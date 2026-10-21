"""Commercially reusable species reference photos. No uploaded photos leave Ribby.

Only explicit CC0 / CC BY licenses are accepted, at photo level. This module
deliberately does not treat an observation's license as a photo license.
"""
import hashlib
import html
import json
import re
import threading
import time
import math
import zipfile
import io
import tempfile
from bisect import bisect_right
from contextlib import ExitStack, contextmanager
from pathlib import Path
from collections import defaultdict, deque
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

USER_AGENT = "Ribby-App/1.0 (https://github.com/FloRina-droid/Ribby-App)"
ALLOWED_HOSTS = frozenset({
    "commons.wikimedia.org", "upload.wikimedia.org", "thumb.wikimedia.org", "api.inaturalist.org",
    "static.inaturalist.org", "inaturalist-open-data.s3.amazonaws.com",
})
IMAGE_HOSTS = ALLOWED_HOSTS - {"commons.wikimedia.org", "api.inaturalist.org"}
TTL = 7 * 86400
CACHE_VERSION = 3
MAX_REFERENCES = 64
VECTOR_MODELS = {'dinov2-small-q8-c2bb04a-cls-v1':384, 'bioclip-v1-fp16-22a18d2-v1':512}


class _SeedParts(io.RawIOBase):
    """Seek across verified seed parts without copying the whole archive to RAM/disk."""
    def __init__(self, files, sizes):
        super().__init__()
        self.files = files
        self.offsets = [0]
        for size in sizes:
            self.offsets.append(self.offsets[-1] + size)
        self.position = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        if whence not in (0, 1, 2):
            raise ValueError('Ungültiger Suchmodus')
        position = offset + (self.position if whence == 1 else self.offsets[-1] if whence == 2 else 0)
        if position < 0:
            raise ValueError('Negative Archivposition')
        self.position = position
        return position

    def read(self, size=-1):
        remaining = max(0, self.offsets[-1] - self.position)
        if size is not None and size >= 0:
            remaining = min(remaining, size)
        chunks = []
        while remaining:
            index = bisect_right(self.offsets, self.position) - 1
            source = self.files[index]
            source.seek(self.position - self.offsets[index])
            count = min(remaining, self.offsets[index + 1] - self.position)
            block = source.read(count)
            if len(block) != count:
                raise ValueError('Bildreferenz-Teil wurde während des Imports verändert')
            chunks.append(block)
            self.position += count
            remaining -= count
        return b''.join(chunks)


@contextmanager
def reference_seed_archive(seed_path):
    """Read a legacy ZIP or a complete hash-verified set of Git-sized parts."""
    seed_path = Path(seed_path)
    if seed_path.is_file():
        with zipfile.ZipFile(seed_path) as archive:
            yield archive
        return
    manifest_path = seed_path.with_name(seed_path.name + '.manifest.json')
    found = {p.name for p in seed_path.parent.glob(seed_path.name + '.part*') if p.is_file()}
    if not manifest_path.is_file():
        if found:
            raise ValueError('Prüfliste für Bildreferenz-Teile fehlt')
        yield None
        return
    try:
        if manifest_path.stat().st_size > 16384:
            raise ValueError()
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        parts = manifest['parts']
        if type(manifest['version']) is not int or manifest['version'] != 1 or not isinstance(parts, list) or not 1 <= len(parts) <= 32:
            raise ValueError()
        for index, part in enumerate(parts, 1):
            if (part['name'] != f'{seed_path.name}.part{index:03d}' or
                    type(part['bytes']) is not int or not 0 < part['bytes'] <= 64 * 1024 * 1024 or
                    not re.fullmatch('[a-f0-9]{64}', part['sha256'])):
                raise ValueError()
        total = sum(part['bytes'] for part in parts)
        if (total > 256 * 1024 * 1024 or type(manifest['bytes']) is not int or
                manifest['bytes'] != total or not re.fullmatch('[a-f0-9]{64}', manifest['sha256'])):
            raise ValueError()
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ValueError('Ungültige Prüfliste für Bildreferenz-Teile') from None
    if found != {part['name'] for part in parts}:
        raise ValueError('Bildreferenz-Teile fehlen oder enthalten zusätzliche Dateien')
    with ExitStack() as stack:
        files = []
        digest = hashlib.sha256()
        for part in parts:
            source = stack.enter_context((seed_path.parent / part['name']).open('rb'))
            files.append(source)
            part_digest = hashlib.sha256()
            length = 0
            while block := source.read(1024 * 1024):
                length += len(block)
                if length > part['bytes']:
                    raise ValueError('Bildreferenz-Teil hat eine falsche Länge')
                part_digest.update(block)
                digest.update(block)
            if length != part['bytes'] or part_digest.hexdigest() != part['sha256']:
                raise ValueError('Bildreferenz-Teil ist beschädigt oder unvollständig')
        if digest.hexdigest() != manifest['sha256']:
            raise ValueError('Prüfsumme des Bildreferenz-Archivs stimmt nicht')
        stream = stack.enter_context(_SeedParts(files, [part['bytes'] for part in parts]))
        with zipfile.ZipFile(stream) as archive:
            yield archive


def install_reference_seed(data_dir, seed_path):
    """Install bundled public photo references into Ribby's normal data directory.

    Existing files are retained. User photos, accounts and audio are never part
    of this seed; the normal reference reader still validates licenses/vectors.
    """
    seed_path, data_dir = Path(seed_path), Path(data_dir).resolve()
    copied = 0
    with reference_seed_archive(seed_path) as archive:
        if archive is None:
            return 0
        entries = archive.infolist()
        if len(entries) > 5000 or sum(e.file_size for e in entries) > 256 * 1024 * 1024:
            raise ValueError('Bildreferenz-Seed ist zu groß')
        for entry in entries:
            name = entry.filename
            allowed = bool(re.fullmatch(r'image_refs/(?:[a-f0-9]{32}\.(?:bin|json)|query_[a-f0-9]{64}\.json)', name))
            allowed = allowed or any(re.fullmatch(r'image_vectors/' + re.escape(key) + r'/[a-f0-9]{32}\.json', name) for key in VECTOR_MODELS)
            allowed = allowed or name in ('BILDNACHWEISE.csv', 'image_reference_report.json')
            if not allowed or entry.is_dir() or entry.file_size > 4 * 1024 * 1024:
                continue
            target = (data_dir / name).resolve()
            if not target.is_relative_to(data_dir):
                raise ValueError('Ungültiger Bildreferenz-Pfad')
            if target.exists() and target.stat().st_size:
                # Upgrade old public query indexes as well as adding image files.
                # Otherwise an existing installation never sees the larger seed
                # until its previous cache expires. Current caches stay intact.
                if not re.fullmatch(r'image_refs/query_[a-f0-9]{64}\.json', name):
                    continue
                try:
                    previous = json.loads(target.read_text(encoding='utf-8'))
                    incoming = json.loads(archive.read(entry).decode('utf-8'))
                    old_version = previous.get('version', 0)
                    if type(old_version) is not int or old_version >= CACHE_VERSION or incoming.get('version') != CACHE_VERSION:
                        continue
                    refs = incoming.get('references')
                    if not isinstance(refs, list) or len(refs) > MAX_REFERENCES or any(
                        not license_info(r.get('license_url')) or not safe_url(r.get('url'), IMAGE_HOSTS) for r in refs
                    ):
                        continue
                except (ValueError, TypeError, AttributeError):
                    continue
            target.parent.mkdir(parents=True, exist_ok=True)
            content = archive.read(entry)  # CRC is checked before writing.
            # A cancelled first start must not leave a partial file that future
            # starts mistake for a complete, existing public reference.
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.seed-', suffix='.tmp', delete=False) as output:
                    temporary = Path(output.name)
                    output.write(content)
                temporary.replace(target)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            copied += 1
    return copied


_locks_guard = threading.Lock()
_query_locks = {}
_api_lock = threading.Lock()
_last_inat_request = 0.0


def safe_url(url, hosts=ALLOWED_HOSTS):
    try:
        p = urlparse(url)
        return p.scheme == "https" and p.hostname in hosts and not p.username and not p.password and p.port in (None, 443)
    except (TypeError, ValueError):
        return False


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_url(newurl):
            raise ValueError("Bildquelle hat eine unzulässige Weiterleitung geliefert")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_bytes(url, limit=4 * 1024 * 1024):
    if not safe_url(url):
        raise ValueError("Unzulässige Bildquelle")
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, image/*"})
    with build_opener(SafeRedirect()).open(req, timeout=15) as response:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Antwort der Bildquelle ist zu groß")
        return data


def fetch_json(url):
    global _last_inat_request
    if urlparse(url).hostname == 'api.inaturalist.org':
        # Keep this server below the provider's recommended 60 requests/minute.
        with _api_lock:
            delay = 1.05 - (time.monotonic() - _last_inat_request)
            if delay > 0:
                time.sleep(delay)
            _last_inat_request = time.monotonic()
    # Observation JSON contains identifications and annotations; image downloads
    # retain their separate 4 MB bound.
    return json.loads(fetch_bytes(url, limit=16 * 1024 * 1024).decode("utf-8"))


def plain(value):
    return html.unescape(re.sub(r"<[^>]*>", " ", str(value or ""))).strip()[:1000]


def license_info(value):
    """Fail closed: never infer a license from a source, filename or substring."""
    s = str(value or "").strip().lower().replace("http://", "https://")
    # Commons sometimes returns a human-readable deed URL instead of its root.
    s = re.sub(r"/deed\.[a-z-]+$", "/", s)
    if s.rstrip('/') in ("cc0", "cc0 1.0", "https://creativecommons.org/publicdomain/zero/1.0"):
        return {"license": "CC0 1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"}
    if s == "cc-by":  # iNaturalist's photo license code
        s = "cc by 4.0"
    match = re.fullmatch(r"(?:cc by |https://creativecommons\.org/licenses/by/)(1\.0|2\.0|2\.5|3\.0|4\.0)/?", s)
    if match:
        version = match.group(1)
        return {"license": f"CC BY {version}", "license_url": f"https://creativecommons.org/licenses/by/{version}/"}
    return None


def taxon_key(scientific):
    """Normalize explicit hybrid markers, never different species epithets."""
    words = str(scientific or '').casefold().replace('×', ' ').split()
    return ' '.join(w for w in words if w not in ('x', 'kl.', 'kl'))


def photo_identity(ref):
    """Recognize iNaturalist photos mirrored to Commons as the same source."""
    if ref.get('canonical_id'):
        return ref['canonical_id']
    for value in (ref.get('source_url', ''), ref.get('url', ''), ref.get('credit', '')):
        match = re.search(r'(?:inaturalist\.org|inaturalist-open-data\.s3\.amazonaws\.com)/photos/(\d+)', value)
        if match:
            return 'inat:' + match.group(1)
    return ref.get('original_url') or ref.get('url') or ref.get('id', '')


def diverse_photos(refs, limit=MAX_REFERENCES):
    """One photo per observation, round-robin across creators, stable ordering."""
    unique, seen, observations = [], set(), set()
    for ref in refs:
        identity = photo_identity(ref)
        observation = ref.get('observation_id')
        if identity in seen or (observation and observation in observations):
            continue
        seen.add(identity)
        if observation:
            observations.add(observation)
        unique.append(ref)
    buckets = defaultdict(deque)
    for ref in unique:
        # Numeric observer IDs are more reliable than formatted copyright text.
        creator = str(ref.get('creator_id') or ref.get('creator') or photo_identity(ref)).casefold()
        buckets[creator].append(ref)
    result = []
    while buckets and len(result) < limit:
        for creator in list(buckets):
            result.append(buckets[creator].popleft())
            if not buckets[creator]:
                del buckets[creator]
            if len(result) == limit:
                break
    return result


def commons_photos(scientific):
    params = {"action": "query", "format": "json", "generator": "search",
              "gsrsearch": f'"{scientific}" filetype:bitmap', "gsrnamespace": 6,
              "gsrlimit": 50, "prop": "imageinfo", "iiprop": "url|extmetadata|mime", "iiurlwidth": 640}
    data = fetch_json("https://commons.wikimedia.org/w/api.php?" + urlencode(params))
    result = []
    for page in data.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        categories = str(meta.get('Categories', {}).get('value', '')).split('|')
        # A name merely mentioned in a description is insufficient evidence.
        if not any(taxon_key(c) == taxon_key(scientific) or
                   taxon_key(c).startswith(taxon_key(scientific) + ' in ') for c in categories):
            continue
        if any(re.search(r'(?i)\b(drawings|illustrations|maps|skeletons)\b', c) for c in categories):
            continue
        # Use the canonical license URL; short names may omit a jurisdiction.
        lic = license_info(meta.get("LicenseUrl", {}).get("value"))
        if not lic:
            continue
        artist = plain(meta.get("Artist", {}).get("value"))
        url = info.get("thumburl") or info.get("url", "")
        source = info.get("descriptionurl", "")
        if not artist or not safe_url(url, IMAGE_HOSTS) or not safe_url(source, {"commons.wikimedia.org"}):
            continue
        if info.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
            continue
        credit = meta.get('Credit', {}).get('value', '')
        canonical = re.search(r'inaturalist\.org/photos/(\d+)', str(credit))
        result.append({**lic, "provider": "Wikimedia Commons", "creator": artist,
                       "credit": plain(credit), "canonical_id": 'inat:'+canonical.group(1) if canonical else '',
                       "taxon_verified": "commons-category", "categories": categories,
                       "title": plain(page.get("title", "").removeprefix("File:")),
                       "source_url": source, "url": url, "original_url": info.get("url", url)})
    return diverse_photos(result, 12)


def inaturalist_photos(scientific):
    taxa = fetch_json("https://api.inaturalist.org/v1/taxa?" + urlencode({"q": scientific, "per_page": 10}))
    taxon = next((t for t in taxa.get("results", []) if taxon_key(t.get("name")) == taxon_key(scientific) and t.get('is_active', True)), None)
    if not taxon:
        return []
    params = {"taxon_id": taxon["id"], "quality_grade": "research", "photos": "true",
              "photo_license": "cc0,cc-by", "per_page": 100, "order_by": "created_at", "order": "desc"}
    data = fetch_json("https://api.inaturalist.org/v1/observations?" + urlencode(params))
    result, seen = [], set()
    for observation in data.get("results", []):
        if taxon_key(observation.get("taxon", {}).get("name")) != taxon_key(scientific):
            continue
        for photo in observation.get("photos", []):
            lic = license_info(photo.get("license_code"))  # NOT observation.license_code
            url = photo.get("url", "").replace("/square.", "/medium.")
            creator = plain(photo.get("attribution"))
            photo_id = photo.get("id")
            if not lic or not creator or not str(photo_id).isdigit() or photo_id in seen or not safe_url(url, IMAGE_HOSTS):
                continue
            seen.add(photo_id)
            result.append({**lic, "provider": "iNaturalist", "creator": creator,
                           "creator_id": observation.get('user', {}).get('id'),
                           "observation_id": observation.get('id'), "canonical_id": f'inat:{photo_id}',
                           "taxon_verified": "research-grade-exact-taxon", "taxon_id": taxon['id'],
                           "title": scientific, "source_url": f"https://www.inaturalist.org/photos/{photo_id}",
                           "url": url, "original_url": url.replace("/medium.", "/original.")})
            break  # Adjacent shots of one animal do not add independent evidence.
    return diverse_photos(result, MAX_REFERENCES)


def reference_photos(data_dir, species, force=False):
    """Cache search results and provenance, never fall back to an unlicensed URL."""
    scientific = str(species.get("sci", "")).strip()
    if not scientific or len(scientific) > 160:
        return {"references": [], "warnings": ["Wissenschaftlicher Artname fehlt."]}
    root = Path(data_dir) / "image_refs"
    root.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(scientific.casefold().encode()).hexdigest()
    cache = root / f"query_{key}.json"
    with _locks_guard:
        lock = _query_locks.setdefault(key, threading.Lock())
    with lock:
        stale = None
        if cache.exists():
            try:
                data = json.loads(cache.read_text(encoding="utf-8"))
                if data.get('version') == CACHE_VERSION:
                    stale = data
                if not force and data.get('version') == CACHE_VERSION and time.time() - data["fetched_at"] < (600 if data.get("warnings") or not data.get('references') else TTL):
                    return data
            except (ValueError, KeyError, TypeError, AttributeError):
                pass
        refs, warnings = [], []
        for provider, query in (("Wikimedia Commons", commons_photos), ("iNaturalist", inaturalist_photos)):
            try:
                refs.extend(query(scientific))
            except Exception:
                warnings.append(f"{provider} ist momentan nicht erreichbar.")
                if stale:
                    previous = [{**r, 'cached_source':True} for r in stale.get('references', []) if r.get('provider') == provider and
                                taxon_key(r.get('scientific_name')) == taxon_key(scientific) and
                                license_info(r.get('license_url')) and safe_url(r.get('url'), IMAGE_HOSTS)]
                    if previous:
                        refs.extend(previous)
                        warnings.append(f'Gespeicherte Referenzen von {provider} werden weiterverwendet.')
        refs = diverse_photos(refs)
        for ref in refs:
            ref['canonical_id'] = photo_identity(ref)
            ref["id"] = hashlib.sha256(ref['canonical_id'].encode()).hexdigest()[:32]
            ref["scientific_name"] = scientific
            ref["retrieved_at"] = ref.get('retrieved_at',time.time()) if ref.get('cached_source') else time.time()
            (root / f"{ref['id']}.json").write_text(json.dumps(ref, ensure_ascii=False), encoding="utf-8")
        result = {"references": refs, "warnings": warnings, "fetched_at": time.time(), 'version': CACHE_VERSION,
                  'creators': len({str(r.get('creator_id') or r.get('creator')) for r in refs})}
        cache.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return result


def image_mime(data):
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError("Nur JPEG, PNG und WebP sind als Referenzbild erlaubt")


def with_precomputed_vectors(data_dir, result, model_key):
    """Optional public-reference pack: saves expensive per-device inference."""
    if not model_key:
        return result
    if model_key not in VECTOR_MODELS:
        raise ValueError('Unbekanntes Bildmodell')
    enriched = []
    for original in result.get('references', []):
        ref = dict(original)
        # Cached/search metadata must never smuggle unvalidated feature data.
        ref.pop('features', None)
        ref.pop('image_sha256', None)
        if not re.fullmatch('[a-f0-9]{32}', str(ref.get('id', ''))):
            continue
        path = Path(data_dir)/'image_vectors'/model_key/f"{ref['id']}.json"
        image_path = Path(data_dir)/'image_refs'/f"{ref['id']}.bin"
        image_hash = None
        try:
            if image_path.stat().st_size > 4 * 1024 * 1024:
                raise ValueError('Referenzbild zu groß')
            photo = image_path.read_bytes()
            image_mime(photo)
            image_hash = hashlib.sha256(photo).hexdigest()
            ref['image_sha256'] = image_hash
        except (OSError, ValueError):
            pass
        try:
            if path.stat().st_size > 65536:
                raise ValueError('Feature-Datei zu groß')
            saved = json.loads(path.read_text(encoding='utf-8'))
            vector = saved['vector']
            if saved.get('model_key') != model_key or saved.get('reference_id') != ref['id'] or len(vector) != VECTOR_MODELS[model_key]:
                raise ValueError('Feature-Datei passt nicht zum Modell')
            if not all(type(x) in (float,int) and math.isfinite(x) for x in vector) or abs(sum(x*x for x in vector)-1) > .01:
                raise ValueError('Ungültige Bildmerkmale')
            if image_hash is None or image_hash != saved.get('image_sha256'):
                raise ValueError('Referenzbild wurde geändert')
            ref['features'] = {'model_key':model_key, 'image_sha256':image_hash, 'vector':vector}
        except (OSError,ValueError,KeyError,TypeError):
            pass  # A missing/invalid precomputed vector falls back to local inference.
        enriched.append(ref)
    return {**result, 'references':enriched}


def reference_file(data_dir, ref_id):
    if not re.fullmatch(r"[a-f0-9]{32}", ref_id):
        raise ValueError("Ungültige Bild-ID")
    root = Path(data_dir) / "image_refs"
    meta_file = root / f"{ref_id}.json"
    if not meta_file.exists():
        raise FileNotFoundError("Referenzbild nicht gefunden")
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    if not license_info(meta.get("license_url")) or not safe_url(meta.get("url"), IMAGE_HOSTS):
        raise ValueError("Lizenz oder Bildquelle nicht freigegeben")
    target = root / f"{ref_id}.bin"
    if not target.exists():
        content = fetch_bytes(meta["url"])
        image_mime(content)
        temporary = root / f"{ref_id}.{threading.get_ident()}.tmp"
        temporary.write_bytes(content)
        temporary.replace(target)
    return target, image_mime(target.read_bytes())


def cache_public_features(data_dir, reference_id, model_key, image_hash, vector):
    """Cache admin-prepared public features only for the exact current photo bytes."""
    if not re.fullmatch(r'[a-f0-9]{32}', str(reference_id)) or model_key not in VECTOR_MODELS:
        raise ValueError('Ungültige Referenz oder unbekanntes Modell')
    if not re.fullmatch(r'[a-f0-9]{64}', str(image_hash)):
        raise ValueError('Bildprüfsumme fehlt')
    if not isinstance(vector, list) or len(vector) != VECTOR_MODELS[model_key] or not all(type(x) in (int,float) and math.isfinite(x) for x in vector) or abs(sum(x*x for x in vector)-1) > .01:
        raise ValueError('Ungültige Bildmerkmale')
    root = Path(data_dir)
    metadata_path = root/'image_refs'/f'{reference_id}.json'
    image_path = root/'image_refs'/f'{reference_id}.bin'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    if not isinstance(metadata, dict) or not license_info(metadata.get('license_url')) or not safe_url(metadata.get('url'), IMAGE_HOSTS):
        raise ValueError('Nur freigegebene öffentliche Referenzbilder dürfen zwischengespeichert werden')
    if image_path.stat().st_size > 4*1024*1024:
        raise ValueError('Referenzbild zu groß')
    photo = image_path.read_bytes()
    image_mime(photo)
    if hashlib.sha256(photo).hexdigest() != image_hash:
        raise ValueError('Referenzbild wurde geändert')
    directory = root/'image_vectors'/model_key
    directory.mkdir(parents=True,exist_ok=True)
    destination = directory/f'{reference_id}.json'
    # Existing valid packs are never overwritten by a browser cache entry.
    existing = with_precomputed_vectors(root, {'references':[{'id':reference_id}]}, model_key)
    if existing['references'][0].get('features'):
        return False
    record = {'reference_id':reference_id,'model_key':model_key,'image_sha256':image_hash,'vector':vector}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=directory,prefix=reference_id+'.',suffix='.tmp',delete=False) as file:
            temporary=Path(file.name)
            json.dump(record,file,separators=(',',':'))
        temporary.replace(destination)
    finally:
        if temporary: temporary.unlink(missing_ok=True)
    return True
