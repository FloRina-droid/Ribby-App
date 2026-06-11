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

import os, sys, json, hashlib, hmac, secrets, base64, time, mimetypes
import socket, threading
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# ── Konfiguration ────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
HOST        = os.getenv("RIBBY_HOST", "0.0.0.0")
PORT        = int(os.getenv("RIBBY_PORT", os.getenv("PORT", "7432")))
DATA_DIR    = Path(os.getenv("RIBBY_DATA_DIR", str(BASE_DIR / "ribby_data"))).expanduser()
PUBLIC_URL  = os.getenv("RIBBY_PUBLIC_URL", "").rstrip("/")
ADMIN_EMAIL = os.getenv("RIBBY_ADMIN_EMAIL", "admin@ribby.app").strip().lower()
ADMIN_PASS  = os.getenv("RIBBY_ADMIN_PASSWORD", "")
CORS_ORIGINS= [o.strip().rstrip("/") for o in os.getenv("RIBBY_CORS_ORIGINS", "").split(",") if o.strip()]
SESSIONS    = {}   # token → user_id
SESSION_TTL = 86400 * 7  # 7 Tage
MAX_UPLOAD_BYTES = int(os.getenv("RIBBY_MAX_UPLOAD_MB", "80")) * 1024 * 1024

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
