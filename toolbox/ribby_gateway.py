"""App origin gateway: one-time launch tickets, per-request ACL, no portal cookies upstream."""
import os, re, secrets, time
from urllib.parse import urlsplit
import requests
from http.cookies import SimpleCookie
from flask import Flask, request, abort, redirect, Response, stream_with_context
from sqlalchemy import select
from .models import Session, App, User, Token, permitted
from .security import consume, issue, digest
from .links import app_domain, portal_hosts
from .port_routes import port_app, port_map

class SizedRequestBody:
    """Keep the incoming byte length while streaming to HTTP/1.0 app servers."""
    def __init__(self, stream, length): self.stream, self.length = stream, length
    def __len__(self): return self.length
    def __iter__(self):
        while True:
            chunk = self.stream.read(65536)
            if not chunk: return
            yield chunk

def create_app():
    gateway=Flask(__name__)
    gateway.config['MAX_CONTENT_LENGTH']=int(os.environ.get('APP_UPLOAD_LIMIT','2147483648'))
    cookie_name='__Host-ng_app_session' if os.environ.get('COOKIE_SECURE','1')=='1' else 'ng_app_session'
    @gateway.route('/healthz')
    def health():
        if request.host.split(':')[0] in ('localhost','127.0.0.1') and not port_app(request.host,portal_hosts()): return {'status':'ok'}
        return route('healthz')
    @gateway.route('/',defaults={'path':''},methods=['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'])
    @gateway.route('/<path:path>',methods=['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'])
    def route(path):
        host=request.host.split(':')[0].lower()
        port_aid=port_app(request.host,portal_hosts())
        domains={app_domain()}
        if os.environ.get('APP_DOMAIN','').strip() in ('','localhost'):
            domains.update(portal_hosts())
        match=re.fullmatch(r'app-([0-9a-f]{32})\.('+ '|'.join(re.escape(d) for d in sorted(domains))+')',host)
        if not port_aid and (port_map() or not match): abort(404)
        aid=port_aid or match[1]
        session_cookie=cookie_name+'_'+aid if port_aid else cookie_name
        cookie_prefix='ng_upstream_'+aid+'_'
        with Session.begin() as s:
            a=s.get(App,aid)
            if not a or not a.container: abort(404)
            if path=='__toolbox/entry':
                t=consume(s,request.args.get('ticket',''),'launch',aid)
                u=s.get(User,t.user_id) if t else None
                if not u or u.epoch!=t.epoch or u.role!='admin' or not permitted(u,a): abort(403)
                raw=issue(s,u,'app-session',aid,28800)
                r=redirect('/'); r.set_cookie(session_cookie,raw,secure=os.environ.get('COOKIE_SECURE','1')=='1',httponly=True,samesite='Lax',max_age=28800,path='/')
                r.headers['Cache-Control']='no-store'; r.headers['Referrer-Policy']='no-referrer'; return r
            t=s.get(Token,digest(request.cookies.get(session_cookie,'')))
            u=s.get(User,t.user_id) if t else None
            if not t or t.purpose!='app-session' or t.app_id!=aid or t.expires<time.time() or not u or t.epoch!=u.epoch or u.role!='admin' or not permitted(u,a):
                return Response('Zugriff abgelaufen oder nicht freigegeben. Bitte die App über die Toolbox erneut öffnen.',403,content_type='text/plain; charset=utf-8')
            if request.headers.get('Upgrade'): abort(501,'WebSocket-Anwendungen benötigen einen eigenen Reverse-Proxy-Adapter.')
            if not re.fullmatch(r'ng-[0-9a-f]{32}-[0-9a-f]{12}',a.container): abort(502)
            # Cross-origin writes are denied even between sibling app origins.
            if request.method not in ('GET','HEAD','OPTIONS'):
                origin=request.headers.get('Origin')
                expected=os.environ.get('APP_SCHEME','https')+'://'+request.host
                if origin!=expected: abort(403)
            if path=='__toolbox/logout':
                if request.method!='POST': abort(405)
                s.delete(t)
                response=Response(__import__('json').dumps({'return_url':os.environ.get('PUBLIC_URL','http://localhost:8088/')}),content_type='application/json')
                response.delete_cookie(session_cookie,path='/',secure=os.environ.get('COOKIE_SECURE','1')=='1',httponly=True,samesite='Lax')
                response.headers['Cache-Control']='no-store'
                return response
            upstream='http://'+a.container+':'+str(a.port)
        excluded={'host','cookie','authorization','connection','upgrade','transfer-encoding','x-forwarded-for','x-forwarded-host','x-forwarded-proto','content-length'}
        headers={k:v for k,v in request.headers if k.lower() not in excluded and not k.lower().startswith(('x-toolbox-','x-ribby-'))}
        # Ribby uses its own 64-hex Bearer session after the Toolbox ACL check.
        app_auth=request.headers.get('Authorization','')
        if re.fullmatch(r'Bearer [a-f0-9]{64}',app_auth):
            headers['Authorization']=app_auth
        try:
            from pathlib import Path
            bridge_key=Path(os.environ['RIBBY_TOOLBOX_SECRET_FILE']).read_text().strip()
            if len(bridge_key)<64: raise ValueError('Bridge key missing')
        except (KeyError,OSError,ValueError): abort(503,'Toolbox-Anmeldung nicht verfügbar.')
        headers['X-Ribby-Toolbox-Key']=bridge_key
        headers['Host']=request.host
        headers['X-Forwarded-Proto']=os.environ.get('APP_SCHEME','https')
        # Retain app cookies only. Toolbox authentication is never visible to app code.
        cookies={k:v for k,v in request.cookies.items() if not k.startswith(('ng_','__Host-ng_'))}
        if port_aid:
            cookies={k[len(cookie_prefix):]:v for k,v in request.cookies.items() if k.startswith(cookie_prefix)}
        if cookies: headers['Cookie']='; '.join(k+'='+v for k,v in cookies.items())
        try:
            upstream_response=requests.request(request.method,upstream+'/'+path,params=request.args,headers=headers,data=SizedRequestBody(request.stream,request.content_length) if request.content_length else None,stream=True,allow_redirects=False,timeout=(10,300))
        except requests.RequestException: abort(502,'App ist momentan nicht erreichbar.')
        def body():
            try:
                for chunk in upstream_response.raw.stream(65536,decode_content=False): yield chunk
            finally: upstream_response.close()
        response=Response(stream_with_context(body()),status=upstream_response.status_code)
        excluded_response={'connection','transfer-encoding','set-cookie','content-security-policy','content-length'}
        if port_aid:
            excluded_response.update({'clear-site-data','access-control-allow-origin','access-control-allow-credentials'})
        for k,v in upstream_response.headers.items():
            if k.lower() not in excluded_response: response.headers[k]=v
        for raw_cookie in upstream_response.raw.headers.getlist('Set-Cookie'):
            parsed=SimpleCookie()
            try: parsed.load(raw_cookie)
            except Exception: continue
            for name,m in parsed.items():
                if name.startswith(('ng_','__Host-ng_')): continue
                if port_aid: name=cookie_prefix+name
                response.set_cookie(name,m.value,path='/',secure=os.environ.get('COOKIE_SECURE','1')=='1',httponly=bool(m['httponly']),samesite='Lax',max_age=int(m['max-age']) if m['max-age'].lstrip('-').isdigit() else None)
        response.headers['Content-Security-Policy']="frame-ancestors 'none'; base-uri 'self'; worker-src 'self' blob:"
        response.headers['Origin-Agent-Cluster']='?1'
        response.headers['Cross-Origin-Opener-Policy']='same-origin'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store'; response.headers['Referrer-Policy']='no-referrer'
        return response
    return gateway
