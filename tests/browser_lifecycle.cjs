const fs=require('node:fs'),assert=require('node:assert/strict');
const {launch,login,selectPhoto,analyze,base,photoDir}=require('./browser_helpers.cjs');
const catalog=JSON.parse(fs.readFileSync('image_reference_catalog.json','utf8'));
const bytes=fs.readFileSync(photoDir+'/image_refs/92dfb549fc26d536f568305c0c93c6cc.bin');
const photo=name=>({name,mimeType:'image/jpeg',buffer:bytes});
const results=[];
async function manual(p){await p.evaluate(()=>renderImageResults([],'Manueller Test'));await p.getByRole('button',{name:'Sonstiges eintragen',exact:true}).click();await p.locator('#confirm-other-existing').selectOption(catalog[0].id);}
async function historyEntry(p,name){return p.evaluate(async ({name,sp})=>(await imageApi('/api/history',{method:'POST',body:JSON.stringify({filename:name,media_type:'image',matches:[],confirmed_species_id:sp.id})})).json(),{name,sp:catalog[0]});}
async function until(fn){for(let i=0;i<80;i++){if(fn())return;await new Promise(r=>setTimeout(r,25));}throw new Error('Controlled request did not start');}
(async()=>{
 const browser=await launch();
 async function test(name,fn){
  const context=await browser.newContext({viewport:{width:1280,height:1000}}),page=await context.newPage(),errors=[];
  page.setDefaultTimeout(14000);page.on('pageerror',e=>errors.push(e.message));const row={name};results.push(row);
  try{await login(page,'other@ribby.test');await selectPhoto(page,photo('lifecycle-a.jpg'));await page.evaluate(()=>{extractImageVector=async()=>[1,...new Array(511).fill(0)];});await fn(page);assert.deepEqual(errors,[]);row.pass=true;console.log('PASS '+name);}
  catch(e){row.pass=false;row.error=e.message;console.log('FAIL '+name+': '+e.message.split('\n')[0]);await page.screenshot({path:'dev/lifecycle-'+name+'.png'}).catch(()=>{});}
  finally{await context.close();fs.writeFileSync('reports/system_lifecycle.json',JSON.stringify(results,null,2)+'\n');}
 }
 try{
  await test('reload_preserves_session_without_blocking_overlay',async p=>{
   await p.reload({waitUntil:'domcontentloaded'});await p.waitForFunction(()=>curUser?.email==='other@ribby.test');
   assert.equal(await p.locator('#dsgvo-overlay').isVisible(),false);await p.locator('#media-image').click();assert.equal(await p.locator('#image-panel').isVisible(),true);
  });
  await test('privacy_notice_accept_keeps_current_page',async p=>{
   await p.evaluate(()=>{showPage('history');showDsgvo();});await p.getByRole('button',{name:'Einwilligen & Fortfahren',exact:true}).click();
   assert.equal(await p.locator('#page-history').isVisible(),true);assert.equal(await p.locator('#page-login').isVisible(),false);
  });
  await test('logout_revokes_server_session',async p=>{
   const token=await p.evaluate(()=>authToken);const response=p.waitForResponse(r=>r.url()===base+'/api/auth/logout',{timeout:3000}).catch(()=>null);
   await p.evaluate(()=>doLogout());const logout=await response;assert.ok(logout,'Server logout must be sent');assert.equal(logout.status(),200);
   assert.equal((await p.request.get(base+'/api/images/own',{headers:{Authorization:'Bearer '+token}})).status(),401);
  });
  await test('save_response_does_not_attach_to_next_photo',async p=>{
   await manual(p);let release,requested=false;const gate=new Promise(r=>release=r);
   await p.route('**/api/history',async route=>{if(route.request().method()==='POST'){requested=true;await gate;}await route.continue();});
   await p.evaluate(()=>{window._save=doConfirmSave();});await until(()=>requested);await selectPhoto(p,photo('lifecycle-b.jpg'));release();await p.evaluate(()=>_save);
   assert.equal(await p.evaluate(()=>imageFile.name),'lifecycle-b.jpg');assert.equal(await p.evaluate(()=>imageHistory),null);
  });
  await test('late_save_error_does_not_overwrite_new_dialog',async p=>{
   await manual(p);let release,requested=false;const gate=new Promise(r=>release=r);
   await p.route('**/api/history',async route=>{if(route.request().method()==='POST'){requested=true;await gate;await route.fulfill({status:503,json:{error:'Error from old photo'}});}else await route.continue();});
   await p.evaluate(()=>{window._save=doConfirmSave();});await until(()=>requested);await selectPhoto(p,photo('lifecycle-b.jpg'));await manual(p);release();await p.evaluate(()=>_save);
   assert.equal(await p.locator('#confirm-status').innerText(),'');assert.equal(await p.locator('#confirm-modal').evaluate(e=>e.classList.contains('open')),true);
  });
  await test('private_save_cannot_cross_user_change',async p=>{
   await manual(p);await p.locator('#confirm-filename').fill('lifecycle-private-leak.jpg');await p.locator('#confirm-save-ref').check();let uploads=0;
   p.on('request',r=>{if(r.method()==='POST'&&r.url()===base+'/api/images/own')uploads++;});
   await p.evaluate(()=>{const original=crypto.subtle.digest.bind(crypto.subtle);crypto.subtle.digest=async(...args)=>{await new Promise(r=>window._releaseHash=r);return original(...args);};window._save=doConfirmSave();});
   await p.waitForFunction(()=>typeof _releaseHash==='function');await p.evaluate(()=>doLogout());
   await p.locator('#li-email').fill('field@ribby.test');await p.locator('#li-pw').fill('SystemTestOnly2026!');await p.locator('#dsgvo-check').check();await p.locator('#login-btn').click();await p.waitForFunction(()=>curUser?.email==='field@ribby.test');
   await p.evaluate(()=>_releaseHash());await p.evaluate(()=>_save);
   try{assert.equal(uploads,0);}finally{await p.evaluate(async()=>{for(const r of await ownImageReferences())if(r.filename==='lifecycle-private-leak.jpg')await imageApi('/api/images/own/'+r.id,{method:'DELETE'});});}
  });
  await test('delayed_history_does_not_replace_new_photo',async p=>{
   const old=await historyEntry(p,'lifecycle-old-history.jpg');let release,requested=false;const gate=new Promise(r=>release=r);
   await p.route('**/api/history',async route=>{if(route.request().method()==='GET'){requested=true;await gate;}await route.continue();});
   await p.evaluate(id=>{window._view=viewHist(id);},old.id);await until(()=>requested);await selectPhoto(p,photo('lifecycle-b.jpg'));release();await p.evaluate(()=>_view);
   assert.equal(await p.evaluate(()=>imageFile?.name),'lifecycle-b.jpg');assert.equal(await p.evaluate(()=>imageHistory),null);
  });
  await test('latest_history_selection_wins',async p=>{
   const a=await historyEntry(p,'lifecycle-history-a.jpg'),b=await historyEntry(p,'lifecycle-history-b.jpg');let release,count=0;const gate=new Promise(r=>release=r);
   await p.route('**/api/history',async route=>{if(route.request().method()==='GET'&&++count===1)await gate;await route.continue();});
   await p.evaluate(id=>{window._firstView=viewHist(id);},a.id);await until(()=>count===1);await p.evaluate(id=>viewHist(id),b.id);release();await p.evaluate(()=>_firstView);
   assert.equal(await p.evaluate(()=>imageHistory?.id),b.id);
  });
  await test('reopened_confirmation_waits_for_previous_save',async p=>{
   await manual(p);let release,requested=false;const gate=new Promise(r=>release=r);
   await p.route('**/api/history',async route=>{if(route.request().method()==='POST'){requested=true;await gate;}await route.continue();});
   await p.evaluate(()=>{window._save=doConfirmSave();});await until(()=>requested);await p.evaluate(()=>closeModal('confirm-modal'));await manual(p);await p.locator('#confirm-other-existing').selectOption(catalog[1].id);
   assert.equal(await p.locator('#confirm-save-btn').isDisabled(),true);release();await p.evaluate(()=>_save);
   assert.equal(await p.locator('#confirm-modal').evaluate(e=>e.classList.contains('open')),true);assert.equal(await p.locator('#confirm-save-btn').isEnabled(),true);
   await p.locator('#confirm-save-btn').click();await p.locator('#image-confirm-feedback').filter({hasText:'Bestätigt: '+catalog[1].name_de}).waitFor();
   assert.equal(await p.evaluate(()=>imageHistory.confirmed_species_id),catalog[1].id);
  });
  await test('previous_save_does_not_replace_reanalysis_of_same_photo',async p=>{
   await manual(p);let release,count=0;const gate=new Promise(r=>release=r);
   await p.route('**/api/history',async route=>{if(route.request().method()==='POST'&&++count===1)await gate;await route.continue();});
   await p.evaluate(()=>{window._save=doConfirmSave();});await until(()=>count===1);await p.locator('#confirm-modal').getByRole('button',{name:'Abbrechen',exact:true}).click();assert.match(await analyze(p),/abgeschlossen/);
   const current=await p.evaluate(()=>imageHistory.id);release();await p.evaluate(()=>_save);assert.equal(await p.evaluate(()=>imageHistory.id),current);
  });
  await test('history_response_after_logout_is_ignored',async p=>{
   const old=await historyEntry(p,'old-before-logout.jpg');let release,requested=false;const gate=new Promise(r=>release=r);
   await p.route('**/api/history',async route=>{if(route.request().method()==='GET'){requested=true;await gate;}await route.continue();});
   await p.evaluate(id=>{window._view=viewHist(id);},old.id);await until(()=>requested);await p.evaluate(()=>doLogout());release();await p.evaluate(()=>_view);
   assert.equal(await p.locator('#page-login').isVisible(),true);assert.equal(await p.locator('#results-out').innerText(),'');
  });
  await test('audio_history_is_read_only_with_different_file_selected',async p=>{
   const entry=await p.evaluate(async sp=>(await imageApi('/api/history',{method:'POST',body:JSON.stringify({filename:'historic-audio.wav',media_type:'audio',matches:[{species_id:sp.id,species_name_de:sp.name_de,scientific_name:sp.sci,confidence:.9}]})})).json(),catalog[0]);
   await p.evaluate(()=>{selFile=new File(['different input'],'different-audio.wav',{type:'audio/wav'});});await p.evaluate(id=>viewHist(id),entry.id);
   assert.match(await p.locator('#results-out').innerText(),/Grasfrosch/);assert.equal(await p.locator('#results-out button').count(),0);
  });
  await test('repeat_analysis_releases_temporary_urls',async p=>{
   await p.getByText('Analyse-Einstellungen',{exact:true}).click();
   await p.evaluate(()=>{const make=URL.createObjectURL.bind(URL),drop=URL.revokeObjectURL.bind(URL);window._activeUrls=new Set();URL.createObjectURL=b=>{const id=make(b);_activeUrls.add(id);return id;};URL.revokeObjectURL=id=>{_activeUrls.delete(id);drop(id);};});
   for(let i=0;i<24;i++){
    await p.locator('#image-reference-count').selectOption(['8','16','32'][i%3]);await selectPhoto(p,photo('soak-'+i+'.jpg'));assert.match(await analyze(p),/abgeschlossen/);
    assert.equal(await p.evaluate(()=>imageWorkerJobs.size),0);assert.equal(await p.evaluate(()=>_activeUrls.size<=imageReferenceUrls.size+1),true);
   }
   await p.evaluate(()=>doLogout());assert.equal(await p.evaluate(()=>_activeUrls.size),0);
  });
 }finally{await browser.close();}
 console.log('Lifecycle suite '+results.filter(r=>r.pass).length+'/'+results.length+' passed');if(results.some(r=>!r.pass))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
