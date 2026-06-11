#!/usr/bin/env python3
"""
Ribby Lokaler Netzwerk-Server
==============================
Startet einen HTTP-Server lokal, im Netzwerk oder hinter HTTPS-Reverse-Proxy.
Alle Daten (Arten, Audios, Nutzer, Verlauf) werden
lokal in ribby_data/ gespeichert.

Start:
  python ribby_server.py

Dann im Browser auf PC und Laptop:
  http://<IP-des-Servers>:7432

Anforderungen: Python 3.10+ (keine zusätzlichen Pakete nötig)
"""

import os, sys, json, hashlib, hmac, secrets, base64, time, mimetypes, shutil
import socket, threading
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# ── Konfiguration ────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        print(f"  WARNUNG: {name}={raw!r} ist keine Zahl. Nutze {default}.")
        return default

HOST        = os.getenv("RIBBY_HOST", "0.0.0.0")
PORT        = env_int("PORT", env_int("RIBBY_PORT", 7432))
DATA_DIR    = Path(os.getenv("RIBBY_DATA_DIR", str(BASE_DIR / "ribby_data"))).expanduser()
SEED_DIR    = Path(os.getenv("RIBBY_SEED_DIR", str(BASE_DIR / "ribby_data_seed"))).expanduser()
PUBLIC_URL  = os.getenv("RIBBY_PUBLIC_URL", "").rstrip("/")
ADMIN_EMAIL = os.getenv("RIBBY_ADMIN_EMAIL", "admin@ribby.app").strip().lower()
ADMIN_PASS  = os.getenv("RIBBY_ADMIN_PASSWORD", "")
CORS_ORIGINS= [o.strip().rstrip("/") for o in os.getenv("RIBBY_CORS_ORIGINS", "").split(",") if o.strip()]
SESSIONS    = {}   # token → user_id
SESSION_TTL = 86400 * 7  # 7 Tage
MAX_UPLOAD_BYTES = env_int("RIBBY_MAX_UPLOAD_MB", 80) * 1024 * 1024

# Datenverzeichnisse anlegen
(DATA_DIR / "species").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "users").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "refaudio").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "history").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "audio_files").mkdir(parents=True, exist_ok=True)

# ── Hilfsfunktionen ──────────────────────────────────────────────────
def uid():
    return secrets.token_hex(8)

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def legacy_hash_pw(pw: str) -> str:
    return hashlib.sha256(f"{pw}ribby_salt".encode()).hexdigest()

def hash_pw(pw: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 260000
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt.encode("ascii"), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"

def verify_pw(stored: str, pw: str) -> bool:
    if not stored:
        return False
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iter_s, salt, digest = stored.split("$", 3)
            test = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt.encode("ascii"), int(iter_s)).hex()
            return hmac.compare_digest(test, digest)
        except Exception:
            return False
    return hmac.compare_digest(stored, legacy_hash_pw(pw))

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return None

def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_all(folder: Path):
    items = []
    for f in folder.glob("*.json"):
        d = load_json(f)
        if d: items.append(d)
    return items

def find_by_id(folder: Path, item_id: str):
    return load_json(folder / f"{item_id}.json")

def save_item(folder: Path, item: dict):
    item_id = item.get("id") or uid()
    item["id"] = item_id
    save_json(folder / f"{item_id}.json", item)
    return item

def delete_item(folder: Path, item_id: str) -> bool:
    p = folder / f"{item_id}.json"
    if p.exists(): p.unlink(); return True
    return False

# ── Seed-Daten einspielen ────────────────────────────────────────────
def ensure_seed_data():
    if os.getenv("RIBBY_DISABLE_SEED", "").strip().lower() in ("1", "true", "yes"):
        print("  Seed-Daten: deaktiviert")
        return
    if not SEED_DIR.exists():
        print("  Seed-Daten: kein ribby_data_seed Ordner gefunden")
        return
    has_species = any((DATA_DIR / "species").glob("*.json"))
    has_refs = any((DATA_DIR / "refaudio").glob("*.json"))
    has_audio = any((DATA_DIR / "audio_files").glob("*.bin"))
    if has_species and has_refs and has_audio:
        print("  Seed-Daten: vorhandene Datenbank wird beibehalten")
        return

    copied = {"species": 0, "refaudio": 0, "history": 0, "audio_files": 0}
    for folder in copied:
        src = SEED_DIR / folder
        dst = DATA_DIR / folder
        if not src.exists():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            if item.is_file():
                target = dst / item.name
                if not target.exists() or target.stat().st_size == 0:
                    shutil.copy2(item, target)
                    copied[folder] += 1
    print(
        "  Seed-Daten eingespielt: "
        f"{copied['species']} Arten, {copied['refaudio']} Referenz-Metadaten, "
        f"{copied['audio_files']} Audiodateien, {copied['history']} Verlaufseinträge"
    )

# ── Auth ─────────────────────────────────────────────────────────────
def get_user_by_email(email: str):
    for u in load_all(DATA_DIR / "users"):
        if u.get("email","").lower() == email.lower():
            return u
    return None

def get_user_by_id(uid_: str):
    return find_by_id(DATA_DIR / "users", uid_)

def create_session(user_id: str) -> str:
    token = secrets.token_hex(32)
    SESSIONS[token] = {"user_id": user_id, "created": time.time()}
    return token

def get_session_user(token: str):
    s = SESSIONS.get(token)
    if not s: return None
    if time.time() - s["created"] > SESSION_TTL:
        del SESSIONS[token]; return None
    return get_user_by_id(s["user_id"])

def auth_from_request(handler) -> dict | None:
    """Gibt User aus Authorization-Header zurück oder None."""
    auth = handler.headers.get("Authorization","")
    if auth.startswith("Bearer "):
        return get_session_user(auth[7:])
    # Auch Cookie prüfen
    cookie = handler.headers.get("Cookie","")
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("ribby_token="):
            return get_session_user(part[12:])
    return None

def require_auth(handler):
    u = auth_from_request(handler)
    if not u:
        handler.send_json({"error": "Nicht authentifiziert"}, 401)
    return u

def require_admin(handler):
    u = require_auth(handler)
    if u and u.get("role") != "admin":
        handler.send_json({"error": "Kein Zugriff (Admin erforderlich)"}, 403)
        return None
    return u

# ── Default Admin anlegen ────────────────────────────────────────────
def ensure_default_admin():
    users = load_all(DATA_DIR / "users")
    configured_admin = next((u for u in users if u.get("email","").lower() == ADMIN_EMAIL), None)

    if ADMIN_PASS:
        admin = configured_admin or {
            "id": uid(),
            "name": "Administrator",
            "email": ADMIN_EMAIL,
            "created_at": now_iso()
        }
        admin["password"] = hash_pw(ADMIN_PASS)
        admin["role"] = "admin"
        admin["updated_at"] = now_iso()
        save_item(DATA_DIR / "users", admin)
        print(f"  Admin aus Environment gesetzt: {ADMIN_EMAIL}")
        return

    if not users:
        initial_password = secrets.token_urlsafe(14)
        admin = {
            "id": uid(),
            "name": "Administrator",
            "email": ADMIN_EMAIL,
            "password": hash_pw(initial_password),
            "role": "admin",
            "created_at": now_iso()
        }
        save_item(DATA_DIR / "users", admin)
        print(f"  Admin angelegt: {ADMIN_EMAIL} / {initial_password}")
        print("  Wichtig: Dieses zufällige Erstpasswort jetzt notieren und danach in der App ändern.")

# ── HTTP Handler ─────────────────────────────────────────────────────
class RibbyHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Kompakteres Logging
        print(f"  [{self.address_string()}] {fmt % args}")

    def send_common_headers(self):
        origin = self.headers.get("Origin", "").rstrip("/")
        if "*" in CORS_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", "*")
        elif origin and origin in CORS_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), geolocation=(self), microphone=(self)")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_common_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, content_type=None):
        data = path.read_bytes()
        ct = content_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", len(data))
        self.send_common_headers()
        self.end_headers()
        self.wfile.write(data)

    def send_html(self, html: str):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_common_headers()
        self.end_headers()
        self.wfile.write(body)

    def read_body(self) -> bytes:
        n = int(self.headers.get("Content-Length", 0))
        if n > MAX_UPLOAD_BYTES:
            raise ValueError(f"Upload zu groß. Maximum: {MAX_UPLOAD_BYTES // 1024 // 1024} MB")
        return self.rfile.read(n) if n else b""

    def read_json(self):
        return json.loads(self.read_body())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_common_headers()
        self.end_headers()

    def do_HEAD(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_common_headers()
            self.end_headers()
        elif path in ("/api/ping", "/healthz"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_common_headers()
            self.end_headers()
        else:
            self.send_response(404)
            self.send_common_headers()
            self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/") or "/"
        qs     = parse_qs(parsed.query)

        # ── Frontend ──────────────────────────────────────────────
        if path == "/" or path == "/index.html":
            html_file = Path(__file__).parent / "ribby_app.html"
            if html_file.exists():
                self.send_html(html_file.read_text(encoding="utf-8"))
            else:
                self.send_json({"error": "ribby_app.html nicht gefunden"}, 404)
            return

        # ── API Routes ────────────────────────────────────────────
        if path == "/api/ping":
            self.send_json({"status": "ok", "version": 4, "time": now_iso(), "publicUrl": PUBLIC_URL})

        elif path == "/healthz":
            self.send_json({"status": "ok", "time": now_iso()})

        elif path == "/api/me":
            u = require_auth(self)
            if u: self.send_json({k:v for k,v in u.items() if k!="password"})

        elif path == "/api/species":
            species = load_all(DATA_DIR / "species")
            species.sort(key=lambda x: x.get("name_de",""))
            self.send_json(species)

        elif path.startswith("/api/species/"):
            sp_id = path.split("/")[-1]
            sp = find_by_id(DATA_DIR / "species", sp_id)
            if sp: self.send_json(sp)
            else: self.send_json({"error": "Nicht gefunden"}, 404)

        elif path == "/api/refaudio":
            sp_filter = qs.get("species_id",[""])[0]
            audios = load_all(DATA_DIR / "refaudio")
            if sp_filter:
                audios = [a for a in audios if a.get("species_id")==sp_filter]
            # Keine audio_data im Listing zurückgeben
            audios = [{k:v for k,v in a.items() if k!="audio_b64"} for a in audios]
            self.send_json(audios)

        elif path.startswith("/api/refaudio/file/"):
            if not require_auth(self): return
            audio_id = path.split("/")[-1]
            audio_file = DATA_DIR / "audio_files" / f"{audio_id}.bin"
            meta = find_by_id(DATA_DIR / "refaudio", audio_id)
            if audio_file.exists() and meta:
                self.send_file(audio_file, meta.get("mime_type","audio/wav"))
            else:
                self.send_json({"error": "Audio nicht gefunden"}, 404)

        elif path == "/api/history":
            u = require_auth(self)
            if not u: return
            hist = load_all(DATA_DIR / "history")
            if u.get("role") != "admin":
                hist = [h for h in hist if h.get("user_id")==u["id"]]
            hist.sort(key=lambda x: x.get("created_at",""), reverse=True)
            self.send_json(hist)

        elif path == "/api/users":
            if not require_admin(self): return
            users = load_all(DATA_DIR / "users")
            self.send_json([{k:v for k,v in u.items() if k!="password"} for u in users])

        elif path == "/api/stats":
            if not require_auth(self): return
            self.send_json({
                "species": len(load_all(DATA_DIR / "species")),
                "refaudio": len(load_all(DATA_DIR / "refaudio")),
                "history": len(load_all(DATA_DIR / "history")),
                "users": len(load_all(DATA_DIR / "users")),
            })

        elif path == "/api/backup/export":
            if not require_admin(self): return
            refaudio = load_all(DATA_DIR / "refaudio")
            export_refs = []
            for meta in refaudio:
                item = dict(meta)
                audio_file = DATA_DIR / "audio_files" / f"{meta.get('id')}.bin"
                if audio_file.exists():
                    item["audioB64"] = base64.b64encode(audio_file.read_bytes()).decode("ascii")
                export_refs.append(item)
            data = {
                "species": load_all(DATA_DIR / "species"),
                "refaudio": export_refs,
                "users": load_all(DATA_DIR / "users"),
                "history": load_all(DATA_DIR / "history"),
            }
            self.send_json({
                "version": 4,
                "mode": "server",
                "exportedAt": now_iso(),
                "includesAudio": True,
                "counts": {k: len(v) for k, v in data.items()},
                "data": data,
            })

        else:
            self.send_json({"error": "Route nicht gefunden"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")

        # ── Login ─────────────────────────────────────────────────
        if path == "/api/auth/login":
            try:
                body = self.read_json()
                email = body.get("email","").strip().lower()
                pw    = body.get("password","")
                user  = get_user_by_email(email)
                if user and verify_pw(user.get("password",""), pw):
                    if not user.get("password","").startswith("pbkdf2_sha256$"):
                        user["password"] = hash_pw(pw)
                        user["updated_at"] = now_iso()
                        save_item(DATA_DIR / "users", user)
                    token = create_session(user["id"])
                    self.send_json({
                        "token": token,
                        "user": {k:v for k,v in user.items() if k!="password"}
                    })
                else:
                    self.send_json({"error": "Falsche E-Mail oder Passwort"}, 401)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)

        elif path == "/api/auth/logout":
            auth = self.headers.get("Authorization","")
            if auth.startswith("Bearer "):
                SESSIONS.pop(auth[7:], None)
            self.send_json({"status": "ok"})

        # ── Benutzer anlegen (Admin) ──────────────────────────────
        elif path == "/api/users":
            if not require_admin(self): return
            try:
                body = self.read_json()
                email = body.get("email","").strip().lower()
                if get_user_by_email(email):
                    self.send_json({"error": "E-Mail bereits vorhanden"}, 409); return
                user = {
                    "id": uid(),
                    "name": body.get("name",""),
                    "email": email,
                    "password": hash_pw(body.get("password","")),
                    "role": body.get("role","user"),
                    "created_at": now_iso()
                }
                save_item(DATA_DIR / "users", user)
                self.send_json({k:v for k,v in user.items() if k!="password"}, 201)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)

        # ── Art anlegen ───────────────────────────────────────────
        elif path == "/api/species":
            if not require_admin(self): return
            try:
                body = self.read_json()
                sp = {
                    "id": uid(),
                    "name_de": body.get("name_de","").strip(),
                    "sci": body.get("sci","").strip(),
                    "category": body.get("category","amphibians"),
                    "img_url": body.get("img_url") or None,
                    "description": body.get("description","").strip(),
                    "created_at": now_iso(),
                    "created_by": auth_from_request(self)["id"] if auth_from_request(self) else None
                }
                save_item(DATA_DIR / "species", sp)
                self.send_json(sp, 201)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)

        # ── Referenz-Audio hochladen ──────────────────────────────
        elif path == "/api/refaudio":
            u = require_auth(self)
            if not u: return
            try:
                # Multipart-Parsing (einfach – liest raw body)
                content_type = self.headers.get("Content-Type","")
                body_bytes = self.read_body()

                if "multipart/form-data" in content_type:
                    boundary = content_type.split("boundary=")[-1].strip().encode()
                    parts = parse_multipart(body_bytes, boundary)
                    species_id = parts.get("species_id", [b""])[0].decode()
                    audio_data = parts.get("file", [None])[0]
                    filename   = parts.get("filename", [b"audio.wav"])[0].decode()
                    mime_type  = parts.get("mime_type", [b"audio/wav"])[0].decode()
                else:
                    # JSON mit base64
                    data = json.loads(body_bytes)
                    species_id = data.get("species_id","")
                    filename   = data.get("filename","audio.wav")
                    mime_type  = data.get("mime_type","audio/wav")
                    audio_b64  = data.get("audio_b64","")
                    audio_data = base64.b64decode(audio_b64) if audio_b64 else None

                if not audio_data:
                    self.send_json({"error": "Keine Audiodaten"}, 400); return

                audio_id = uid()
                # Audiodatei speichern
                audio_file = DATA_DIR / "audio_files" / f"{audio_id}.bin"
                audio_file.write_bytes(audio_data)

                meta = {
                    "id": audio_id,
                    "species_id": species_id,
                    "filename": filename,
                    "mime_type": mime_type,
                    "size": len(audio_data),
                    "created_at": now_iso(),
                    "uploaded_by": u["id"]
                }
                save_item(DATA_DIR / "refaudio", meta)
                self.send_json(meta, 201)
            except Exception as e:
                import traceback; traceback.print_exc()
                self.send_json({"error": str(e)}, 400)

        # ── Analyse-Verlauf speichern ─────────────────────────────
        elif path == "/api/history":
            u = require_auth(self)
            if not u: return
            try:
                body = self.read_json()
                entry = {
                    "id": uid(),
                    "filename": body.get("filename",""),
                    "matches": body.get("matches",[]),
                    "duration": body.get("duration"),
                    "created_at": now_iso(),
                    "user_id": u["id"],
                    "user_name": u.get("name","")
                }
                save_item(DATA_DIR / "history", entry)
                self.send_json(entry, 201)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)

        elif path == "/api/backup/import":
            if not require_admin(self): return
            try:
                backup = self.read_json()
                data = backup.get("data", backup)
                counts = {"species": 0, "refaudio": 0, "users": 0, "history": 0, "errors": 0}
                for sp in data.get("species", []):
                    try:
                        if sp.get("id"):
                            save_item(DATA_DIR / "species", sp)
                            counts["species"] += 1
                    except Exception:
                        counts["errors"] += 1
                for u in data.get("users", []):
                    try:
                        if u.get("id") and u.get("email") and u.get("password"):
                            save_item(DATA_DIR / "users", u)
                            counts["users"] += 1
                    except Exception:
                        counts["errors"] += 1
                for h in data.get("history", []):
                    try:
                        if h.get("id"):
                            save_item(DATA_DIR / "history", h)
                            counts["history"] += 1
                    except Exception:
                        counts["errors"] += 1
                for r in data.get("refaudio", []):
                    try:
                        audio_b64 = r.get("audioB64") or r.get("audio_b64")
                        if not r.get("id") or not audio_b64:
                            continue
                        audio_bytes = base64.b64decode(audio_b64)
                        (DATA_DIR / "audio_files" / f"{r['id']}.bin").write_bytes(audio_bytes)
                        meta = {k: v for k, v in r.items() if k not in ("audioB64", "audio_b64", "audioData")}
                        meta.setdefault("size", len(audio_bytes))
                        meta.setdefault("mime_type", meta.get("mimeType", "audio/wav"))
                        save_item(DATA_DIR / "refaudio", meta)
                        counts["refaudio"] += 1
                    except Exception:
                        counts["errors"] += 1
                self.send_json({"status": "ok", "counts": counts})
            except Exception as e:
                self.send_json({"error": str(e)}, 400)

        else:
            self.send_json({"error": "Route nicht gefunden"}, 404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")

        # ── Art bearbeiten ────────────────────────────────────────
        if path.startswith("/api/species/"):
            if not require_admin(self): return
            sp_id = path.split("/")[-1]
            existing = find_by_id(DATA_DIR / "species", sp_id)
            if not existing:
                self.send_json({"error": "Nicht gefunden"}, 404); return
            try:
                body = self.read_json()
                existing.update({
                    "name_de":     body.get("name_de", existing.get("name_de","")),
                    "sci":         body.get("sci", existing.get("sci","")),
                    "category":    body.get("category", existing.get("category","amphibians")),
                    "img_url":     body.get("img_url", existing.get("img_url")),
                    "description": body.get("description", existing.get("description","")),
                    "updated_at":  now_iso()
                })
                save_item(DATA_DIR / "species", existing)
                self.send_json(existing)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)

        # ── Referenz-Audio-Metadaten bearbeiten ───────────────────
        elif path.startswith("/api/refaudio/"):
            if not require_auth(self): return
            audio_id = path.split("/")[-1]
            existing = find_by_id(DATA_DIR / "refaudio", audio_id)
            if not existing:
                self.send_json({"error": "Nicht gefunden"}, 404); return
            try:
                body = self.read_json()
                for key in ("filename", "gps", "area", "featV3", "confirmed", "species_id"):
                    if key in body:
                        existing[key] = body[key]
                existing["updated_at"] = now_iso()
                save_item(DATA_DIR / "refaudio", existing)
                self.send_json(existing)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)

        # ── Benutzer-Rolle ändern ─────────────────────────────────
        elif path.startswith("/api/users/"):
            if not require_admin(self): return
            user_id = path.split("/")[-1]
            existing = find_by_id(DATA_DIR / "users", user_id)
            if not existing:
                self.send_json({"error": "Nicht gefunden"}, 404); return
            try:
                body = self.read_json()
                if "role" in body: existing["role"] = body["role"]
                if "name" in body: existing["name"] = body["name"]
                if "password" in body and body["password"]:
                    if "_verify" in body:
                        if not verify_pw(existing.get("password",""), body["_verify"]):
                            self.send_json({"error": "Aktuelles Passwort falsch"}, 403); return
                    existing["password"] = hash_pw(body["password"])
                existing["updated_at"] = now_iso()
                save_item(DATA_DIR / "users", existing)
                self.send_json({k:v for k,v in existing.items() if k!="password"})
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
        else:
            self.send_json({"error": "Route nicht gefunden"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")

        if path.startswith("/api/species/"):
            if not require_admin(self): return
            sp_id = path.split("/")[-1]
            # Auch zugehörige Referenz-Audios löschen
            audios = [a for a in load_all(DATA_DIR/"refaudio") if a.get("species_id")==sp_id]
            for a in audios:
                delete_item(DATA_DIR/"refaudio", a["id"])
                af = DATA_DIR/"audio_files"/f"{a['id']}.bin"
                if af.exists(): af.unlink()
            deleted = delete_item(DATA_DIR/"species", sp_id)
            self.send_json({"deleted": deleted, "audios_deleted": len(audios)})

        elif path.startswith("/api/refaudio/"):
            if not require_auth(self): return
            audio_id = path.split("/")[-1]
            af = DATA_DIR/"audio_files"/f"{audio_id}.bin"
            if af.exists(): af.unlink()
            deleted = delete_item(DATA_DIR/"refaudio", audio_id)
            self.send_json({"deleted": deleted})

        elif path.startswith("/api/users/"):
            if not require_admin(self): return
            user_id = path.split("/")[-1]
            u = auth_from_request(self)
            if u and u["id"] == user_id:
                self.send_json({"error": "Eigenen Account nicht löschbar"}, 400); return
            deleted = delete_item(DATA_DIR/"users", user_id)
            self.send_json({"deleted": deleted})

        elif path.startswith("/api/history/"):
            if not require_auth(self): return
            hist_id = path.split("/")[-1]
            deleted = delete_item(DATA_DIR/"history", hist_id)
            self.send_json({"deleted": deleted})

        else:
            self.send_json({"error": "Route nicht gefunden"}, 404)


# ── Multipart-Parser (ohne externe Bibliotheken) ─────────────────────
def parse_multipart(body: bytes, boundary: bytes) -> dict:
    """Einfacher Multipart-Parser. Gibt dict name→[value] zurück."""
    parts = {}
    delimiter = b"--" + boundary
    segments = body.split(delimiter)
    for seg in segments[1:]:
        if seg.startswith(b"--") or not seg.strip(): continue
        # Header und Body trennen
        if b"\r\n\r\n" in seg:
            header_raw, content = seg.split(b"\r\n\r\n", 1)
        elif b"\n\n" in seg:
            header_raw, content = seg.split(b"\n\n", 1)
        else:
            continue
        # Content-Disposition parsen
        name, filename = None, None
        for line in header_raw.decode("utf-8","ignore").splitlines():
            if "Content-Disposition" in line:
                for token in line.split(";"):
                    token = token.strip()
                    if token.startswith("name="):
                        name = token.split("=",1)[1].strip('"')
                    if token.startswith("filename="):
                        filename = token.split("=",1)[1].strip('"')
        if name is None: continue
        # Trailing CRLF entfernen
        value = content.rstrip(b"\r\n")
        parts.setdefault(name, []).append(value)
        if filename:
            parts.setdefault("filename", []).append(filename.encode())
    return parts


# ── IP-Adresse ermitteln ─────────────────────────────────────────────
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


# ── Main ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        ensure_seed_data()
        ensure_default_admin()
        ip = get_local_ip()

        print()
        print("=" * 55)
        print("  Ribby Soundanalyse – Lokaler Netzwerk-Server")
        print("=" * 55)
        print(f"  Host          : {HOST}")
        print(f"  Port          : {PORT}")
        print(f"  Daten-Ordner  : {DATA_DIR.resolve()}")
        print(f"  Seed-Ordner   : {SEED_DIR.resolve()}")
        print()
        print(f"  Lokal         : http://localhost:{PORT}")
        print(f"  Netzwerk      : http://{ip}:{PORT}")
        if PUBLIC_URL:
            print(f"  Öffentlich    : {PUBLIC_URL}")
        print()
        print(f"  Login-E-Mail  : {ADMIN_EMAIL}")
        print(f"  Admin-Passwort: {'aus Environment gesetzt' if ADMIN_PASS else 'nicht gesetzt'}")
        print()
        print("  Strg+C zum Beenden")
        print("=" * 55)
        print()

        server = ThreadingHTTPServer((HOST, PORT), RibbyHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server gestoppt.")
    except Exception:
        import traceback
        print("\nFATAL: Ribby Server konnte nicht starten.", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
