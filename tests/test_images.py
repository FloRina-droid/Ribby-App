import base64
import importlib
import json
import os
import tempfile
import threading
import unittest
import zipfile
import hashlib
import io
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import ribby_images as images


class ReferenceSeedTests(unittest.TestCase):
    def make_split_seed(self, root):
        seed = root / 'seed.zip'
        content = io.BytesIO()
        with zipfile.ZipFile(content, 'w') as archive:
            archive.writestr('image_refs/' + 'a' * 32 + '.json', '{"license":"CC0"}')
            archive.writestr('BILDNACHWEISE.csv', 'Urheber;Lizenz\n')
        raw = content.getvalue()
        split = len(raw) // 3
        parts = []
        for index, block in enumerate((raw[:split], raw[split:2*split], raw[2*split:]), 1):
            name = f'seed.zip.part{index:03d}'
            (root / name).write_bytes(block)
            parts.append({'name': name, 'bytes': len(block), 'sha256': hashlib.sha256(block).hexdigest()})
        manifest = {'version': 1, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'parts': parts}
        seed.with_name('seed.zip.manifest.json').write_text(json.dumps(manifest))
        return seed, manifest

    def test_split_archive_installs_across_part_boundaries_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); seed, _ = self.make_split_seed(root)
            self.assertEqual(images.install_reference_seed(root/'data', seed), 2)
            self.assertEqual((root/'data/BILDNACHWEISE.csv').read_text(), 'Urheber;Lizenz\n')
            self.assertEqual(images.install_reference_seed(root/'data', seed), 0)

    def test_missing_part_is_rejected_before_any_file_is_installed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); seed, _ = self.make_split_seed(root)
            (root/'seed.zip.part002').unlink()
            with self.assertRaisesRegex(ValueError, 'Teile fehlen'):
                images.install_reference_seed(root/'data', seed)
            self.assertFalse((root/'data').exists())

    def test_corrupted_part_is_rejected_before_any_file_is_installed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); seed, _ = self.make_split_seed(root)
            part = root/'seed.zip.part003'; raw = part.read_bytes()
            part.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
            with self.assertRaisesRegex(ValueError, 'beschädigt'):
                images.install_reference_seed(root/'data', seed)
            self.assertFalse((root/'data').exists())

    def test_seed_parts_require_manifest_and_reject_extra_parts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); seed, _ = self.make_split_seed(root)
            (root/'seed.zip.part004').write_bytes(b'extra')
            with self.assertRaisesRegex(ValueError, 'zusätzliche'):
                images.install_reference_seed(root/'data', seed)
            (root/'seed.zip.manifest.json').unlink()
            with self.assertRaisesRegex(ValueError, 'Prüfliste'):
                images.install_reference_seed(root/'data', seed)
            self.assertFalse((root/'data').exists())

    def test_part_manifest_rejects_traversal_and_invalid_sizes(self):
        for field, value in (('name', '../other'), ('bytes', -1), ('bytes', True), ('sha256', 'wrong')):
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); seed, manifest = self.make_split_seed(root)
                manifest['parts'][0][field] = value
                (root/'seed.zip.manifest.json').write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, 'Ungültige Prüfliste'):
                    images.install_reference_seed(root/'data', seed)
                self.assertFalse((root/'data').exists())

    def test_full_archive_checksum_and_part_length_are_checked(self):
        for change in ('checksum', 'length'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); seed, manifest = self.make_split_seed(root)
                if change == 'checksum':
                    manifest['sha256'] = '0' * 64
                    (root/'seed.zip.manifest.json').write_text(json.dumps(manifest))
                else:
                    part = root/'seed.zip.part001'; part.write_bytes(part.read_bytes() + b'extra')
                with self.assertRaises(ValueError):
                    images.install_reference_seed(root/'data', seed)
                self.assertFalse((root/'data').exists())

    def test_part_stream_seek_read_and_eof(self):
        with images._SeedParts([io.BytesIO(b'abc'), io.BytesIO(b'defg')], [3, 4]) as stream:
            self.assertEqual(stream.read(4), b'abcd')
            self.assertEqual(stream.seek(-2, 1), 2)
            self.assertEqual(stream.read(), b'cdefg')
            self.assertEqual(stream.seek(-3, 2), 4)
            self.assertEqual(stream.read(2), b'ef')
            self.assertEqual(stream.seek(20), 20)
            self.assertEqual(stream.read(), b'')
            with self.assertRaises(ValueError):stream.seek(-1)

    def test_failed_atomic_install_leaves_no_incomplete_target_or_temporary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); seed, _ = self.make_split_seed(root)
            with patch.object(Path, 'replace', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):images.install_reference_seed(root/'data', seed)
            self.assertFalse(any(p.is_file() for p in (root/'data').rglob('*')))
            self.assertEqual(images.install_reference_seed(root/'data', seed), 2)

    def test_regular_start_installs_public_references_and_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); archive=root/'seed.zip'; data=root/'data'
            meta='image_refs/'+'a'*32+'.json'
            vector='image_vectors/bioclip-v1-fp16-22a18d2-v1/'+'a'*32+'.json'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr(meta,'{"license":"CC0"}');z.writestr(vector,'{}')
                z.writestr('BILDNACHWEISE.csv','Urheber;Lizenz\n')
                z.writestr('../escape.json','unsafe');z.writestr('users/admin.json','unsafe')
                z.writestr('refimages/private.json','unsafe')
            self.assertEqual(images.install_reference_seed(data,archive),3)
            self.assertTrue((data/meta).exists());self.assertTrue((data/vector).exists())
            self.assertFalse((data/'users').exists());self.assertFalse((root/'escape.json').exists())
            (data/meta).write_text('existing')
            self.assertEqual(images.install_reference_seed(data,archive),0)
            self.assertEqual((data/meta).read_text(),'existing')

    def test_missing_reference_seed_is_optional(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(images.install_reference_seed(Path(temp)/'data',Path(temp)/'missing.zip'),0)

    def test_seed_upgrades_old_public_index_but_preserves_current_searches(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive=root/'seed.zip';data=root/'data'
            name='image_refs/query_'+'a'*64+'.json';target=data/name
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps({'version':images.CACHE_VERSION-1,'references':[]}))
            payload={'version':images.CACHE_VERSION,'references':[],'fetched_at':123}
            with zipfile.ZipFile(archive,'w') as z:z.writestr(name,json.dumps(payload))
            self.assertEqual(images.install_reference_seed(data,archive),1)
            self.assertEqual(json.loads(target.read_text()),payload)
            payload['fetched_at']=456;target.write_text(json.dumps(payload))
            self.assertEqual(images.install_reference_seed(data,archive),0)
            self.assertEqual(json.loads(target.read_text())['fetched_at'],456)

    def test_seed_does_not_replace_old_index_with_unlicensed_upgrade(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive=root/'seed.zip';data=root/'data'
            name='image_refs/query_'+'b'*64+'.json';target=data/name
            target.parent.mkdir(parents=True)
            previous={'version':images.CACHE_VERSION-1,'references':[]};target.write_text(json.dumps(previous))
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr(name,json.dumps({'version':images.CACHE_VERSION,'references':[{'license_url':'https://creativecommons.org/licenses/by-nc/4.0/','url':'https://static.inaturalist.org/photos/1/medium.jpg'}]}))
            self.assertEqual(images.install_reference_seed(data,archive),0)
            self.assertEqual(json.loads(target.read_text()),previous)


class LicenseTests(unittest.TestCase):
    def test_explicit_commercial_licenses(self):
        for value in ('cc0', 'CC0 1.0', 'cc-by', 'https://creativecommons.org/licenses/by/3.0/', 'http://creativecommons.org/publicdomain/zero/1.0/', 'http://creativecommons.org/publicdomain/zero/1.0/deed.en'):
            self.assertIsNotNone(images.license_info(value), value)

    def test_reject_restricted_unknown_and_lookalike_licenses(self):
        for value in ('cc-by-nc', 'CC BY-SA 4.0', 'CC BY-ND 4.0', '', None, 'public domain',
                      'https://creativecommons.org.evil.test/licenses/by/4.0/',
                      'https://creativecommons.org/licenses/by/4.0/de/', 'CC BY 4.0 or CC BY-NC'):
            self.assertIsNone(images.license_info(value), value)

    def test_urls_fail_closed(self):
        for url in ('http://upload.wikimedia.org/a', 'https://127.0.0.1/a', 'https://upload.wikimedia.org.evil.test/a',
                    'https://user@upload.wikimedia.org/a', 'https://upload.wikimedia.org:444/a', 'file:///etc/passwd'):
            self.assertFalse(images.safe_url(url), url)
        self.assertTrue(images.safe_url('https://upload.wikimedia.org/a.jpg'))

    def test_inaturalist_uses_photo_license_and_exact_taxon(self):
        data = {'results': [{'taxon': {'name': 'Hyla arborea'}, 'license_code': 'cc0', 'photos': [
            {'id': 1, 'license_code': 'cc-by-nc', 'url': 'https://static.inaturalist.org/photos/1/square.jpg', 'attribution': 'A'},
            {'id': 2, 'license_code': 'cc-by', 'url': 'https://static.inaturalist.org/photos/2/square.jpg', 'attribution': 'B'},
        ]}, {'taxon': {'name': 'Hyla orientalis'}, 'photos': [
            {'id': 3, 'license_code': 'cc0', 'url': 'https://static.inaturalist.org/photos/3/square.jpg', 'attribution': 'C'}]}]}
        with patch.object(images, 'fetch_json', side_effect=[{'results': [{'id': 99, 'name': 'Hyla arborea'}]}, data]):
            result = images.inaturalist_photos('Hyla arborea')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['creator'], 'B')
        self.assertEqual(result[0]['license'], 'CC BY 4.0')
        self.assertIn('/medium.jpg', result[0]['url'])

    def test_commons_requires_canonical_license_and_author(self):
        def page(license_url, artist='Author'):
            return {'title': 'File:Tree frog.jpg', 'imageinfo': [{'mime': 'image/jpeg',
                    'url': 'https://upload.wikimedia.org/frog.jpg', 'descriptionurl': 'https://commons.wikimedia.org/wiki/File:Frog.jpg',
                    'extmetadata': {'Artist': {'value': artist}, 'LicenseUrl': {'value': license_url}, 'Categories': {'value':'Hyla arborea'}}}]}
        data = {'query': {'pages': {'1': page('https://creativecommons.org/licenses/by/4.0/', '<b>A &amp; B</b>'),
                                   '2': page('https://creativecommons.org/licenses/by-nc/4.0/'),
                                   '3': page('https://creativecommons.org/licenses/by/4.0/', '')}}}
        with patch.object(images, 'fetch_json', return_value=data):
            result = images.commons_photos('Hyla arborea')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['creator'], 'A & B')

    def test_unavailable_source_does_not_prevent_other_source(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(images, 'commons_photos', side_effect=TimeoutError), patch.object(images, 'inaturalist_photos', return_value=[]):
            result = images.reference_photos(tmp, {'sci': 'Hyla arborea'})
        self.assertIn('Wikimedia Commons', result['warnings'][0])

    def test_cache_preserves_provenance_and_avoids_duplicate_queries(self):
        ref = {'url': 'https://upload.wikimedia.org/frog.jpg', 'license_url': 'https://creativecommons.org/licenses/by/4.0/', 'creator': 'A'}
        with tempfile.TemporaryDirectory() as tmp, patch.object(images, 'commons_photos', return_value=[ref]) as query, patch.object(images, 'inaturalist_photos', return_value=[]):
            first = images.reference_photos(tmp, {'sci': 'Hyla arborea'})
            second = images.reference_photos(tmp, {'sci': 'Hyla arborea'})
            self.assertEqual(query.call_count, 1)
            self.assertEqual(first, second)
            meta = json.loads(next((Path(tmp)/'image_refs').glob('[a-f0-9]'*32+'.json')).read_text())
            self.assertEqual(meta['creator'], 'A')

    def test_image_endpoint_cannot_fetch_unlicensed_or_traverse(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): images.reference_file(tmp, '../secrets')
            root = Path(tmp)/'image_refs'; root.mkdir()
            (root/('a'*32+'.json')).write_text(json.dumps({'license_url': 'https://creativecommons.org/licenses/by-nc/4.0/', 'url': 'https://upload.wikimedia.org/a.jpg'}))
            with self.assertRaises(ValueError): images.reference_file(tmp, 'a'*32)

    def test_hybrid_marker_lookup_does_not_confuse_different_species(self):
        self.assertEqual(images.taxon_key('Pelophylax kl. esculentus'), images.taxon_key('Pelophylax esculentus'))
        self.assertEqual(images.taxon_key('Pelophylax × esculentus'), images.taxon_key('Pelophylax esculentus'))
        self.assertNotEqual(images.taxon_key('Pelophylax lessonae'), images.taxon_key('Pelophylax esculentus'))
        data={'results':[{'id':99,'taxon':{'name':'Pelophylax kl. esculentus'},'photos':[{'id':1,'license_code':'cc0','url':'https://static.inaturalist.org/photos/1/square.jpg','attribution':'A'}]}]}
        with patch.object(images,'fetch_json',side_effect=[{'results':[{'id':5,'name':'Pelophylax kl. esculentus','rank':'hybrid'}]},data]) as fetch:
            self.assertEqual(len(images.inaturalist_photos('Pelophylax esculentus')),1)
            self.assertNotIn('rank=species', fetch.call_args_list[0].args[0])

    def test_reference_diversity_and_cross_source_deduplication(self):
        refs=[{'url':'https://static.inaturalist.org/photos/1/medium.jpg','creator':'A','observation_id':1},
              {'url':'https://static.inaturalist.org/photos/2/medium.jpg','creator':'A','observation_id':1},
              {'url':'https://static.inaturalist.org/photos/3/medium.jpg','creator':'A','observation_id':2},
              {'url':'https://static.inaturalist.org/photos/4/medium.jpg','creator':'B','observation_id':3},
              {'url':'https://upload.wikimedia.org/copy.jpg','creator':'C','canonical_id':'inat:1'}]
        selected=images.diverse_photos(refs,3)
        self.assertEqual([r['creator'] for r in selected],['A','B','A'])
        self.assertEqual(len({images.photo_identity(r) for r in selected}),3)

    def test_version_one_cache_is_refreshed_for_larger_reference_pool(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'image_refs';root.mkdir()
            key=hashlib.sha256(b'hyla arborea').hexdigest()
            (root/f'query_{key}.json').write_text(json.dumps({'fetched_at':9999999999,'references':[]}))
            with patch.object(images,'commons_photos',return_value=[]) as query,patch.object(images,'inaturalist_photos',return_value=[]):
                result=images.reference_photos(tmp,{'sci':'Hyla arborea'})
                self.assertEqual(query.call_count,1)
                self.assertEqual(result['version'],images.CACHE_VERSION)

    def test_expired_reference_pack_survives_source_outage(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'image_refs';root.mkdir()
            ref={'url':'https://upload.wikimedia.org/frog.jpg','original_url':'https://upload.wikimedia.org/frog.jpg','license_url':'https://creativecommons.org/licenses/by/4.0/','provider':'Wikimedia Commons','creator':'A','scientific_name':'Hyla arborea'}
            key=hashlib.sha256(b'hyla arborea').hexdigest()
            (root/f'query_{key}.json').write_text(json.dumps({'version':images.CACHE_VERSION,'fetched_at':0,'references':[ref]}))
            with patch.object(images,'commons_photos',side_effect=OSError),patch.object(images,'inaturalist_photos',side_effect=OSError):
                result=images.reference_photos(tmp,{'sci':'Hyla arborea'})
                self.assertEqual(len(result['references']),1)
                self.assertTrue(any('weiterverwendet' in warning for warning in result['warnings']))

    def test_commons_rejects_name_only_mentions(self):
        page={'title':'File:Other frog.jpg','imageinfo':[{'mime':'image/jpeg','url':'https://upload.wikimedia.org/frog.jpg','descriptionurl':'https://commons.wikimedia.org/wiki/File:Frog.jpg','extmetadata':{'Artist':{'value':'A'},'LicenseUrl':{'value':'https://creativecommons.org/licenses/by/4.0/'},'Categories':{'value':'Hyla orientalis'}}}]}
        with patch.object(images,'fetch_json',return_value={'query':{'pages':{'1':page}}}):
            self.assertEqual(images.commons_photos('Hyla arborea'),[])

    def test_precomputed_reference_vectors_require_matching_model_and_photo_hash(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            key='bioclip-v1-fp16-22a18d2-v1';ref_id='a'*32
            ref_root=Path(tmp)/'image_refs';ref_root.mkdir()
            vector_root=Path(tmp)/'image_vectors'/key;vector_root.mkdir(parents=True)
            photo=b'\xff\xd8\xffpublic-reference';(ref_root/f'{ref_id}.bin').write_bytes(photo)
            payload={'model_key':key,'reference_id':ref_id,'image_sha256':hashlib.sha256(photo).hexdigest(),'vector':[1.0]+[0.0]*511}
            (vector_root/f'{ref_id}.json').write_text(json.dumps(payload))
            result={'references':[{'id':ref_id}]}
            self.assertEqual(len(images.with_precomputed_vectors(tmp,result,key)['references'][0]['features']['vector']),512)
            (ref_root/f'{ref_id}.bin').write_bytes(b'changed')
            self.assertNotIn('features',images.with_precomputed_vectors(tmp,result,key)['references'][0])
            with self.assertRaises(ValueError):images.with_precomputed_vectors(tmp,result,'../../other')


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        os.environ['RIBBY_DATA_DIR'] = cls.temp.name
        import ribby_server
        cls.server_module = importlib.reload(ribby_server)
        cls.server_module.save_item(Path(cls.temp.name)/'species', {'id': 'frog', 'sci': 'Hyla arborea', 'name_de': 'Laubfrosch'})
        for user in ('one', 'two', 'admin'):
            cls.server_module.save_item(Path(cls.temp.name)/'users', {'id': user, 'name': user, 'role': 'admin' if user=='admin' else 'user'})
        cls.tokens = {u: cls.server_module.create_session(u) for u in ('one', 'two', 'admin')}
        cls.http = cls.server_module.ThreadingHTTPServer(('127.0.0.1', 0), cls.server_module.RibbyHandler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True); cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.http.server_address[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close(); cls.temp.cleanup()

    def request(self, path, method='GET', data=None, user='one'):
        headers = {'Content-Type': 'application/json'}
        if user: headers['Authorization'] = 'Bearer '+self.tokens[user]
        req = Request(self.url+path, method=method, headers=headers, data=None if data is None else json.dumps(data).encode())
        try:
            with urlopen(req) as response: return response.status, json.loads(response.read())
        except HTTPError as response:
            with response:
                return response.code, json.loads(response.read())

    def test_image_routes_require_authentication(self):
        for path in ('/api/images/references?species_id=frog', '/api/images/file/'+'a'*32, '/api/images/own'):
            self.assertEqual(self.request(path, user=None)[0], 401)

    def test_reference_query_uses_catalog_and_handles_missing_species(self):
        self.assertEqual(self.request('/api/images/references?species_id=../x')[0], 404)
        with patch.object(images, 'reference_photos', return_value={'references': [], 'warnings': []}) as query:
            self.assertEqual(self.request('/api/images/references?species_id=frog')[0], 200)
            self.assertEqual(query.call_args.args[1]['sci'], 'Hyla arborea')

    def test_history_keeps_image_mode_and_confirmation_without_changing_audio(self):
        code, entry = self.request('/api/history', 'POST', {'media_type': 'image', 'filename': 'frog.jpg', 'matches': []})
        self.assertEqual(code, 201); self.assertEqual(entry['media_type'], 'image')
        self.assertEqual(self.request('/api/history/'+entry['id'], 'PUT', {'confirmed_species_id': 'frog'}, user='two')[0], 403)
        code, changed = self.request('/api/history/'+entry['id'], 'PUT', {'confirmed_species_id': 'frog','area':'Testteich','gps':{'lat':52.5,'lon':13.4}})
        self.assertEqual(code, 200); self.assertEqual(changed['confirmed_species_id'], 'frog')
        self.assertEqual(changed['area'],'Testteich');self.assertEqual(changed['gps']['lat'],52.5)
        _, audio = self.request('/api/history', 'POST', {'filename': 'frog.wav'})
        self.assertEqual(audio['media_type'], 'audio')

    def test_reference_limit_is_applied_before_expensive_vector_validation(self):
        refs=[{'id':f'{i:032x}','canonical_id':f'inat:{i}','creator':f'Author {i//2}','observation_id':i+1} for i in range(64)]
        with patch.object(images,'reference_photos',return_value={'references':refs,'warnings':[]}),patch.object(images,'with_precomputed_vectors',side_effect=lambda data,result,model:result) as enrich:
            code, limited=self.request('/api/images/references?species_id=frog&limit=16')
            self.assertEqual(code,200)
            self.assertEqual(limited['references'],images.diverse_photos(refs,16))
            self.assertEqual(len(enrich.call_args.args[1]['references']),16)
            self.assertEqual(len(self.request('/api/images/references?species_id=frog')[1]['references']),64)

    def test_reference_limit_rejects_invalid_values_without_querying_sources(self):
        with patch.object(images,'reference_photos') as query:
            for value in ('-1','0','100000','nan','16.5'):
                self.assertEqual(self.request('/api/images/references?species_id=frog&limit='+value)[0],400)
            query.assert_not_called()

    def test_private_reference_validation_scope_and_deletion(self):
        content = base64.b64encode(b'\xff\xd8\xffjpeg-fixture').decode()
        code, own = self.request('/api/images/own', 'POST', {'species_id': 'frog', 'image_b64': content, 'filename': '<frog>.jpg'})
        self.assertEqual(code, 201); self.assertEqual(own['license'], 'private')
        self.assertEqual(self.request('/api/images/own', user='two')[1], [])
        self.assertEqual(self.request('/api/images/own/'+own['id'], 'DELETE', user='two')[0], 404)
        self.assertEqual(self.request('/api/images/own/'+own['id'], 'DELETE')[0], 200)
        self.assertEqual(self.request('/api/images/own', 'POST', {'species_id': 'frog', 'image_b64': base64.b64encode(b'<svg/>').decode()})[0], 400)

    def test_camera_policy_and_feature_discovery(self):
        with urlopen(self.url) as response:
            self.assertIn('camera=(self)', response.headers['Permissions-Policy'])
        self.assertTrue(self.request('/api/ping', user=None)[1]['imageRecognition'])

    def test_private_references_survive_backup_and_unsafe_import_is_rejected(self):
        raw=base64.b64encode(b'\xff\xd8\xffbackup-fixture').decode()
        _, ref=self.request('/api/images/own','POST',{'species_id':'frog','image_b64':raw})
        _, backup=self.request('/api/backup/export',user='admin')
        self.assertIn(ref['id'],[r['id'] for r in backup['data']['refimages']])
        self.request('/api/images/own/'+ref['id'],'DELETE')
        code, result=self.request('/api/backup/import','POST',{'data':{'refimages':[ref]}},user='admin')
        self.assertEqual(code,200);self.assertEqual(result['counts']['refimages'],1)
        self.assertIn(ref['id'],[r['id'] for r in self.request('/api/images/own')[1]])
        ref['id']='../escape'
        _, result=self.request('/api/backup/import','POST',{'data':{'refimages':[ref]}},user='admin')
        self.assertEqual(result['counts']['errors'],1)

    def test_own_reference_route_rejects_unknown_species(self):
        self.assertEqual(self.request('/api/images/own','POST',{'species_id':'missing','image_b64':'x'})[0],400)

    def test_repeated_private_photo_does_not_inflate_reference_count(self):
        raw=base64.b64encode(b'\xff\xd8\xffduplicate-test').decode()
        first_code,first=self.request('/api/images/own','POST',{'species_id':'frog','image_b64':raw})
        second_code,second=self.request('/api/images/own','POST',{'species_id':'frog','image_b64':raw})
        self.assertEqual(first_code,201);self.assertEqual(second_code,200)
        self.assertEqual(first['id'],second['id']);self.assertEqual(len(first['content_sha256']),64)
        self.server_module.save_item(Path(self.temp.name)/'species',{'id':'other','sci':'Bufo bufo'})
        self.assertEqual(self.request('/api/images/own','POST',{'species_id':'other','image_b64':raw})[0],409)

    def test_concurrent_private_photo_uploads_cannot_assign_two_species(self):
        import time
        raw=base64.b64encode(b'\xff\xd8\xffconcurrent-private-fixture').decode()
        self.server_module.save_item(Path(self.temp.name)/'species',{'id':'other','sci':'Bufo bufo'})
        original=self.server_module.save_item
        def slow_write(folder,item):
            if Path(folder).name=='refimages':time.sleep(.04)
            return original(folder,item)
        with patch.object(self.server_module,'save_item',side_effect=slow_write):
            with ThreadPoolExecutor(max_workers=8) as pool:
                results=list(pool.map(lambda i:self.request('/api/images/own','POST',{'species_id':'frog' if i%2 else 'other','image_b64':raw}),range(8)))
        accepted={body['species_id'] for code,body in results if code in (200,201)}
        self.assertEqual(len(accepted),1)
        self.assertTrue(any(code==409 for code,body in results))

    def test_legacy_private_photo_without_hash_still_blocks_conflicting_assignment(self):
        raw=base64.b64encode(b'\xff\xd8\xfflegacy-private-fixture').decode()
        self.server_module.save_item(Path(self.temp.name)/'species',{'id':'other','sci':'Bufo bufo'})
        self.server_module.save_item(Path(self.temp.name)/'refimages',{'id':'legacy-test','species_id':'frog','user_id':'one','image_b64':raw,'license':'private'})
        self.assertEqual(self.request('/api/images/own','POST',{'species_id':'other','image_b64':raw})[0],409)

    def test_concurrent_session_renewal_cannot_resurrect_logged_out_token(self):
        import time
        token=self.server_module.create_session('one');started=threading.Event()
        original=self.server_module.save_json
        def slow_session_write(path,data):
            if Path(path).name==token+'.json':started.set();time.sleep(.15)
            return original(path,data)
        with patch.object(self.server_module,'save_json',side_effect=slow_session_write):
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending=pool.submit(self.server_module.get_session_user,token)
                self.assertTrue(started.wait(2))
                request=Request(self.url+'/api/auth/logout',method='POST',headers={'Authorization':'Bearer '+token},data=b'{}')
                with urlopen(request) as response:self.assertEqual(response.status,200)
                pending.result(timeout=2)
        self.assertIsNone(self.server_module.get_session_user(token))

    def test_malformed_bearer_token_is_rejected_without_loading_other_records(self):
        with patch.object(self.server_module,'load_json',wraps=self.server_module.load_json) as load:
            self.assertIsNone(self.server_module.get_session_user('../users/one'))
            load.assert_not_called()


if __name__ == '__main__':
    unittest.main()
