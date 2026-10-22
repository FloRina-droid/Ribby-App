import hashlib,json,tempfile,unittest
from pathlib import Path
import ribby_images as images
class PublicFeatureCacheTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'image_refs').mkdir();self.rid='a'*32;self.key='bioclip-v1-fp16-22a18d2-v1';self.vector=[1.0]+[0.0]*511;self.photo=b'\xff\xd8\xffpublic-photo';self.hash=hashlib.sha256(self.photo).hexdigest();self.meta=self.root/'image_refs'/f'{self.rid}.json';self.meta.write_text(json.dumps({'id':self.rid,'license_url':'https://creativecommons.org/licenses/by/4.0/','url':'https://static.inaturalist.org/photos/example.jpg'}));(self.root/'image_refs'/f'{self.rid}.bin').write_bytes(self.photo)
 def tearDown(self):self.tmp.cleanup()
 def save(self,**kw):return images.cache_public_features(self.root,kw.get('rid',self.rid),kw.get('key',self.key),kw.get('hash',self.hash),kw.get('vector',self.vector))
 def test_verified_public_vector_is_reused_by_normal_reader(self):
  self.assertTrue(self.save());d=images.with_precomputed_vectors(self.root,{'references':[{'id':self.rid}]},self.key);self.assertEqual(d['references'][0]['features']['vector'],self.vector)
 def test_existing_valid_pack_is_not_overwritten(self):
  self.save();self.assertFalse(self.save(vector=[0.,1.]+[0.]*510));d=images.with_precomputed_vectors(self.root,{'references':[{'id':self.rid}]},self.key);self.assertEqual(d['references'][0]['features']['vector'],self.vector)
 def test_changed_photo_hash_is_rejected(self):
  with self.assertRaises(ValueError):self.save(hash='b'*64)
 def test_invalid_models_vectors_and_path_ids_are_rejected(self):
  for kwargs in [{'rid':'../bad'},{'key':'other'},{'vector':[0.]*512},{'vector':[True]+[0.]*511},{'vector':[float('nan')]+[0.]*511},{'vector':[1.]}]:
   with self.assertRaises(ValueError):self.save(**kwargs)
 def test_private_unlicensed_and_unsafe_sources_are_rejected(self):
  for m in [{'license_url':'private','url':'https://static.inaturalist.org/p.jpg'},{'license_url':'https://creativecommons.org/licenses/by/4.0/','url':'https://bad.example/p.jpg'}]:
   self.meta.write_text(json.dumps(m))
   with self.assertRaises(ValueError):self.save()
 def test_replacing_photo_invalidates_saved_features(self):
  self.save();(self.root/'image_refs'/f'{self.rid}.bin').write_bytes(b'\xff\xd8\xffchanged');d=images.with_precomputed_vectors(self.root,{'references':[{'id':self.rid}]},self.key);self.assertNotIn('features',d['references'][0])
 def test_atomic_cache_write_leaves_no_temporary_files(self):
  self.save();self.assertFalse(list((self.root/'image_vectors'/self.key).glob('*.tmp')))
if __name__=='__main__':unittest.main()
