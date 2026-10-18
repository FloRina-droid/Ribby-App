"""Side-effect-free identities for splitting public research photographs."""
import re

def author_name(ref):
    value=str(ref.get('creator','')).casefold()
    value=re.sub(r'^\s*(?:\(c\)|©)\s*','',value)
    value=re.sub(r',?\s*(?:some rights reserved|no rights reserved).*$','',value)
    return ''.join(c for c in value if c.isalnum())

def author_keys(ref):
    result={'name:'+author_name(ref)}
    if ref.get('creator_id'):
        result.add('inat-user:'+str(ref['creator_id']))
    return result
