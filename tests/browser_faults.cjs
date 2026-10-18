const fs=require('node:fs'),assert=require('node:assert/strict');
const {photoDir,launch,login,selectPhoto,analyze,base}=require('./browser_helpers.cjs');
const catalog=JSON.parse(fs.readFileSync('image_reference_catalog.json','utf8'));
const testPhoto={name:'fault-case.jpg',mimeType:'image/jpeg',buffer:fs.readFileSync(photoDir+'/image_refs/92dfb549fc26d536f568305c0c93c6cc.bin')};
const results=[];
async function fixture(page){await login(page,'other@ribby.test');await selectPhoto(page,testPhoto);await page.evaluate(()=>{extractImageVector=async()=>[1,...new Array(511).fill(0)];});}
async function manual(page){await page.evaluate(()=>renderImageResults([],'Manuelle Bestimmung'));await page.getByRole('button',{name:'Sonstiges eintragen',exact:true}).click();}
(async()=>{
 const browser=await launch();
 async function test(name,fn){
  const context=await browser.newContext({viewport:{width:1280,height:1000},permissions:['camera']}),page=await context.newPage(),errors=[];
  page.setDefaultTimeout(12000);page.on('pageerror',e=>errors.push(e.message));
  const row={name};results.push(row);
  try{await fixture(page);await fn(page);assert.deepEqual(errors,[]);row.pass=true;console.log('PASS '+name);}
  catch(e){row.pass=false;row.error=e.message;console.log('FAIL '+name+': '+e.message.split('\n')[0]);await page.screenshot({path:'dev/fault-'+name+'.png'}).catch(()=>{});}
  finally{await context.close();fs.writeFileSync('reports/system_faults.json',JSON.stringify(results,null,2)+'\n');}
 }
 try{
 await test('file_validation',async p=>{
  await p.locator('#image-file').setInputFiles({name:'x.svg',mimeType:'image/svg+xml',buffer:Buffer.from('<svg/>')});assert.match(await p.locator('#image-input-status').innerText(),/JPEG/);
  await p.evaluate(()=>handleImageFile(new File([new Uint8Array(16*1024*1024)],'too-big.jpg',{type:'image/jpeg'})));assert.match(await p.locator('#image-input-status').innerText(),/15 MB/);
  await p.locator('#image-file').setInputFiles({name:'broken.jpg',mimeType:'image/jpeg',buffer:Buffer.from([255,216,255,0])});
  await p.locator('#image-input-status').filter({hasText:'nicht geöffnet'}).waitFor();assert.equal(await p.locator('#image-analyze').isEnabled(),true);
 });
 await test('confirm_empty_species',async p=>{
  await manual(p);await p.locator('#confirm-other-sp').uncheck();await p.locator('#confirm-sp-search').fill('');await p.locator('#confirm-save-btn').click();
  assert.equal(await p.locator('#confirm-modal').evaluate(el=>el.classList.contains('open')),true);
  assert.equal(await p.evaluate(()=>imageHistory),null);assert.match(await p.locator('#confirm-status').innerText(),/Art/);
 });
 await test('confirm_invalid_species',async p=>{
  await p.evaluate(sp=>renderImageResults([{species_id:sp.id,species_name_de:sp.name_de,scientific_name:sp.sci,similarity:.5,nRefs:1}],'test'),catalog[0]);
  await p.locator('#results-out').getByRole('button',{name:'Bestätigen',exact:true}).click();await p.locator('#confirm-sp-search').fill('keine gültige Art xyz');await p.locator('#confirm-save-btn').click();
  assert.equal(await p.locator('#confirm-modal').evaluate(el=>el.classList.contains('open')),true);assert.equal(await p.evaluate(()=>imageHistory),null);
 });
 await test('pending_upload_disables_analysis',async p=>{
  await p.evaluate(()=>{const original=createImageBitmap;window._bitmapOriginal=original;createImageBitmap=async f=>{await new Promise(r=>window._releaseDecode=r);return original(f);};window._pendingUpload=handleImageFile(new File([imageFile],'pending.jpg',{type:'image/jpeg'}));});
  assert.equal(await p.locator('#image-analyze').isDisabled(),true);
  await p.evaluate(()=>_releaseDecode());await p.evaluate(()=>_pendingUpload);assert.equal(await p.evaluate(()=>imageFile.name),'pending.jpg');
 });
 await test('crop_removed_while_decoding',async p=>{
  await p.evaluate(()=>{const original=createImageBitmap;createImageBitmap=async f=>{await new Promise(r=>window._releaseCrop=r);return original(f);};imageCrop={x:0,y:0,width:80,height:80};window._cropError=null;window._cropPending=applyImageCrop().catch(e=>window._cropError=e.message);});
  await p.evaluate(()=>clearImageFile());await p.evaluate(()=>_releaseCrop());await p.evaluate(()=>_cropPending);
  assert.equal(await p.evaluate(()=>_cropError),null);assert.equal(await p.evaluate(()=>imageFile),null);assert.equal(await p.locator('#image-reset-crop').isVisible(),false);
 });
 await test('error_after_logout_ignored',async p=>{
  await p.evaluate(()=>{extractImageVector=()=>new Promise((r,reject)=>window._rejectModel=reject);window._runPending=doImageAnalyze();});
  await p.waitForFunction(()=>typeof _rejectModel==='function');await p.evaluate(()=>doLogout());await p.evaluate(()=>_rejectModel(new Error('late model error')));await p.evaluate(()=>_runPending);
  assert.equal(await p.locator('#results-out').innerText(),'');assert.equal(await p.locator('#confirm-modal').evaluate(e=>e.classList.contains('open')),false);
 });
 await test('private_list_after_logout_ignored',async p=>{
  let release;const gate=new Promise(r=>release=r);let requested=false;
  await p.route('**/api/images/own',async route=>{requested=true;await gate;await route.fulfill({json:[{id:'late-private',filename:'private late photo.jpg',species_id:catalog[0].id}]}).catch(()=>{});});
  await p.evaluate(()=>{window._ownPending=openOwnPhotos();});
  for(let i=0;i<50&&!requested;i++)await p.waitForTimeout(50);assert.equal(requested,true);
  await p.evaluate(()=>doLogout());release();await p.evaluate(()=>_ownPending);
  assert.equal(await p.locator('#image-profile-list').innerText(),'');
 });
 await test('cancel_during_reference_display',async p=>{
  let release;const gate=new Promise(r=>release=r);await p.route('**/api/images/file/**',async route=>{await gate;await route.continue().catch(()=>{});});
  await p.evaluate(()=>{window._runPending=doImageAnalyze();});await p.locator('#results-out .mcard').first().waitFor();
  await p.locator('#image-cancel').click();release();await p.evaluate(()=>_runPending);
  assert.equal(await p.locator('#results-out').innerText(),'');assert.match(await p.locator('#image-progress').innerText(),/abgebrochen/);
 });
 await test('no_references_is_explicit_failure',async p=>{
  await p.route('**/api/images/references?*',route=>route.fulfill({json:{references:[],warnings:['Quellen im Test nicht erreichbar']}}));
  const status=await analyze(p);assert.match(status,/fehlgeschlagen/);assert.equal(await p.evaluate(()=>imageHistory),null);assert.equal(await p.getByRole('button',{name:'Sonstiges eintragen',exact:true}).isVisible(),true);
 });
 await test('history_outage_can_retry',async p=>{
  await p.route('**/api/history',route=>route.request().method()==='POST'?route.fulfill({status:503,json:{error:'Test: Speicher nicht erreichbar'}}):route.continue());
  assert.match(await analyze(p),/fehlgeschlagen/);await p.unroute('**/api/history');
  const confirm=p.locator('#results-out .mcard').first().getByRole('button',{name:'Bestätigen',exact:true});
  if(await confirm.count()){await confirm.click();await p.locator('#confirm-sp-search').fill(catalog[0].sci);}else{await p.getByRole('button',{name:'Sonstiges eintragen',exact:true}).click();await p.locator('#confirm-other-existing').selectOption(catalog[0].id);}
  await p.locator('#confirm-save-btn').click();await p.locator('#image-confirm-feedback').filter({hasText:'Bestätigt:'}).waitFor();
 });
 await test('cache_read_failure_is_optional',async p=>{
  await p.route('**/api/images/references?*',async route=>{const result=await route.fetch(),data=await result.json();if(route.request().url().includes('species_id='+catalog[0].id)){for(const r of data.references)delete r.features;}else data.references=[];await route.fulfill({json:data});});
  await p.evaluate(()=>{const original=dbGet;dbGet=(store,key)=>store==='imagefeatures'?Promise.reject(new Error('test cache unavailable')):original(store,key);});
  assert.match(await analyze(p),/abgeschlossen/);assert.equal(await p.locator('#results-out .mcard').count(),1);
 });
 await test('camera_stops_on_navigation',async p=>{
  await p.locator('#card-image-rec').click();await p.waitForFunction(()=>imageStream?.active);
  await p.evaluate(()=>{window._cameraTracks=imageStream.getTracks();selMode('upload');});
  assert.equal(await p.evaluate(()=>_cameraTracks.every(t=>t.readyState==='ended')&&imageStream===null),true);
 });
 await test('late_camera_error_does_not_stop_new_camera',async p=>{
  await p.evaluate(()=>{window._originalCamera=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);navigator.mediaDevices.getUserMedia=()=>new Promise((r,reject)=>window._rejectOldCamera=reject);window._oldCamera=startImageCamera();});
  await p.evaluate(()=>{navigator.mediaDevices.getUserMedia=window._originalCamera;return startImageCamera();});
  await p.waitForFunction(()=>imageStream?.active);
  await p.evaluate(()=>_rejectOldCamera(new DOMException('late denial','NotAllowedError')));await p.evaluate(()=>_oldCamera);
  assert.equal(await p.evaluate(()=>imageStream?.active),true);
 });
 await test('camera_capture_after_logout_ignored',async p=>{
  await p.locator('#card-image-rec').click();await p.waitForFunction(()=>document.getElementById('image-video').videoWidth>0);
  await p.evaluate(()=>{const original=HTMLCanvasElement.prototype.toBlob;HTMLCanvasElement.prototype.toBlob=function(cb,...args){window._releaseCapture=()=>original.call(this,cb,...args);};window._capturePending=captureImage();});
  await p.evaluate(()=>doLogout());await p.evaluate(()=>_releaseCapture());await p.evaluate(()=>_capturePending);
  assert.equal(await p.evaluate(()=>imageFile),null);assert.equal(await p.locator('#image-preview-wrap').isVisible(),false);
 });
 await test('png_webp_and_large_image_normalization',async p=>{
  for(const type of ['image/png','image/webp']){
   const info=await p.evaluate(async type=>{const canvas=document.createElement('canvas');canvas.width=3000;canvas.height=2400;const blob=await new Promise(r=>canvas.toBlob(r,type));await handleImageFile(new File([blob],'transparent.'+type.split('/')[1],{type}));const bitmap=await createImageBitmap(imageFile);const result={width:bitmap.width,height:bitmap.height,type:imageFile.type};bitmap.close();return result;},type);
   assert.deepEqual(info,{width:1600,height:1280,type:'image/jpeg'});
  }
  assert.match(await analyze(p),/abgeschlossen/);
 });
 await test('repeated_cancel_and_restart',async p=>{
  for(let i=0;i<5;i++){
   await p.evaluate(()=>{extractImageVector=()=>new Promise(r=>window._finishCancelled=r);window._cancelPending=doImageAnalyze();});await p.waitForFunction(()=>typeof _finishCancelled==='function');
   await p.locator('#image-cancel').click();await p.evaluate(()=>_finishCancelled([1,...new Array(511).fill(0)]));await p.evaluate(()=>_cancelPending);
   assert.equal(await p.evaluate(()=>imageRun===null&&imageWorkerJobs.size===0&&imageHistory===null),true);assert.equal(await p.locator('#results-out').innerText(),'');
   await p.evaluate(()=>{delete window._finishCancelled;});
  }
  await p.evaluate(()=>{extractImageVector=async()=>[1,...new Array(511).fill(0)];});assert.match(await analyze(p),/abgeschlossen/);
 });
 await test('expired_authentication_can_recover',async p=>{
  const token=await p.evaluate(()=>authToken);await p.evaluate(()=>{authToken='invalid-session-token';});
  assert.match(await analyze(p),/Nicht authentifiziert/);assert.equal(await p.evaluate(()=>imageHistory),null);
  await p.evaluate(token=>{authToken=token;},token);assert.match(await analyze(p),/abgeschlossen/);
 });
 await test('mobile_confirmation_scrolls',async p=>{
  await p.setViewportSize({width:390,height:700});await manual(p);
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await p.locator('#confirm-other-existing').selectOption(catalog[0].id);await p.locator('#confirm-save-btn').click();await p.locator('#image-confirm-feedback').filter({hasText:'Bestätigt:'}).waitFor();
 });
 }finally{await browser.close();}
 const failed=results.filter(r=>!r.pass);console.log('Fault suite '+(results.length-failed.length)+'/'+results.length+' passed');if(failed.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
