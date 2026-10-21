// Cache/transport UI tests use deterministic inference; accuracy is tested separately.
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {base,launch,login,selectPhoto,analyze}=require('./browser_helpers.cjs');
const catalog=JSON.parse(fs.readFileSync('image_reference_catalog.json','utf8'));
const probe=JSON.parse(fs.readFileSync('reports/accuracy_calibration_probe.json','utf8'))[0];
const bytes=fs.readFileSync('accuracy_work/calibration/probe/image_refs/'+probe.id+'.bin');
const vector=JSON.parse(fs.readFileSync('accuracy_work/calibration/probe/image_vectors/bioclip-v1-fp16-22a18d2-v1/'+probe.id+'.json','utf8')).vector;
const rows=[];
(async()=>{
 const browser=await launch();
 try{
  async function test(name,fn){
   const context=await browser.newContext(),page=await context.newPage();page.setDefaultTimeout(25000);
   try{
    await login(page);await selectPhoto(page,{name:name+'.jpg',mimeType:'image/jpeg',buffer:bytes});
    await page.evaluate(v=>{window._referenceExtractions=0;extractImageVector=async blob=>{if(blob!==imageFile)window._referenceExtractions++;return v;};},vector);
    await fn(page);rows.push({case:name,pass:true});console.log('CACHE UI PASS',name);
   }finally{await context.close();}
  }
  async function onlyFirst(page){
   const ref=await page.evaluate(async id=>(await (await imageApi('/api/images/references?species_id='+id+'&model='+imageModelKey()+'&limit=8')).json()).references[0],catalog[0].id);
   assert.match(ref.image_sha256,/^[a-f0-9]{64}$/);delete ref.features;
   await page.route('**/api/images/references?*',route=>route.fulfill({json:{references:new URL(route.request().url()).searchParams.get('species_id')===catalog[0].id?[ref]:[],warnings:[]}}));
   return ref;
  }
  async function cached(page,ref,bound){await page.evaluate(async({ref,vector,bound})=>dbPut('imagefeatures',{id:imageModelKey()+':'+ref.id,vector,...(bound?{model_key:imageModelKey(),image_sha256:ref.image_sha256}:{})}),{ref,vector,bound});}
  await test('legacy_cache_migrates_after_fresh_inference',async page=>{
   const ref=await onlyFirst(page);await cached(page,ref,false);assert.match(await analyze(page),/abgeschlossen/);
   assert.equal(await page.evaluate(()=>_referenceExtractions),1);
   const stored=await page.evaluate(id=>dbGet('imagefeatures',imageModelKey()+':'+id),ref.id);assert.equal(stored.image_sha256,ref.image_sha256);assert.ok(stored.model_key);
  });
  await test('matching_cache_avoids_reference_inference',async page=>{
   const ref=await onlyFirst(page);await cached(page,ref,true);assert.match(await analyze(page),/abgeschlossen/);assert.equal(await page.evaluate(()=>_referenceExtractions),0);
  });
  await test('same_id_old_checksum_recomputes_reference',async page=>{
   const ref=await onlyFirst(page);await cached(page,{...ref,image_sha256:'0'.repeat(64)},true);assert.match(await analyze(page),/abgeschlossen/);assert.equal(await page.evaluate(()=>_referenceExtractions),1);
  });
  await test('photo_changed_during_download_is_rejected',async page=>{
   const ref=await onlyFirst(page);ref.image_sha256='0'.repeat(64);assert.match(await analyze(page),/fehlgeschlagen/);
   assert.equal(await page.evaluate(()=>_referenceExtractions),0);assert.equal(await page.evaluate(()=>imageHistory),null);
  });
  await test('private_photo_same_id_new_bytes_recomputes',async page=>{
   const hash=crypto.createHash('sha256').update(bytes).digest('hex');
   const ref={id:'cache-private',species_id:catalog[0].id,license:'private',filename:'cache-private.jpg',image_b64:bytes.toString('base64'),content_sha256:hash,mime_type:'image/jpeg',user_id:'field'};
   await page.route('**/api/images/own',route=>route.fulfill({json:[ref]}));await page.getByText('Analyse-Einstellungen',{exact:true}).click();await page.locator('#image-online').uncheck();
   await cached(page,{...ref,image_sha256:'0'.repeat(64)},true);assert.match(await analyze(page),/abgeschlossen/);assert.equal(await page.evaluate(()=>_referenceExtractions),1);
   assert.equal(await page.evaluate(()=>imageMatches[0].reference.image_sha256),hash);assert.equal(await page.evaluate(()=>imageMatches[0].score_type),'similarity');
  });
  await test('unchanged_public_pack_remains_calibrated',async page=>{
   assert.match(await analyze(page),/abgeschlossen/);assert.equal(await page.evaluate(()=>_referenceExtractions),0);assert.equal(await page.evaluate(()=>imageMatches[0].score_type),'calibrated_probability');
  });
  await test('same_public_ids_changed_hash_disable_calibration',async page=>{
   await page.route('**/api/images/references?*',async route=>{const response=await route.fetch(),data=await response.json();if(data.references[0]?.scientific_name===catalog[0].sci){data.references[0].image_sha256='f'.repeat(64);data.references[0].features.image_sha256='f'.repeat(64);}await route.fulfill({json:data});});
   assert.match(await analyze(page),/abgeschlossen/);assert.ok(await page.evaluate(()=>imageMatches.every(m=>m.score_type==='similarity')));
   assert.match(await page.locator('#results-out .mcard').first().innerText(),/Bildähnlichkeit/);
  });
  await test('invalid_query_vector_cannot_show_results',async page=>{
   await page.evaluate(()=>{extractImageVector=async()=>new Array(512).fill(0);});assert.match(await analyze(page),/ungültige Merkmale/);assert.equal(await page.evaluate(()=>imageHistory),null);assert.equal(await page.locator('#results-out .mcard').count(),0);
  });
  fs.writeFileSync('reports/image_cache_browser_v6.json',JSON.stringify({pass:true,cases:rows,app_sha256:crypto.createHash('sha256').update(fs.readFileSync('ribby_app.html')).digest('hex'),inference:'deterministic vectors; no recognition accuracy measured'},null,2)+'\n');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
