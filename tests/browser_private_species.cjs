const fs=require('node:fs'),assert=require('node:assert/strict');
const {request}=require('playwright');
const {base,photoDir,launch,login,selectPhoto,analyze}=require('./browser_helpers.cjs');
const catalog=JSON.parse(fs.readFileSync('image_reference_catalog.json','utf8')),manifest=JSON.parse(fs.readFileSync('reports/accuracy_test_manifest.json','utf8'));
(async()=>{
 const api=await request.newContext(),admin=await (await api.post(base+'/api/auth/login',{data:{email:'admin@ribby.test',password:'SystemTestOnly2026!'}})).json();
 const headers={Authorization:'Bearer '+admin.token},email='roundtrip-'+Date.now()+'@ribby.test';
 const created=await api.post(base+'/api/users',{headers,data:{name:'Private round-trip test',email,password:'SystemTestOnly2026!',role:'user'}});assert.equal(created.status(),201);
 const browser=await launch(),report={species:[],checks:[]};
 try{
  const page=await browser.newPage();page.setDefaultTimeout(20000);await login(page,email);
  for(const sp of catalog){
   const photo=manifest.find(p=>p.species_id===sp.id);assert.ok(photo);
   await selectPhoto(page,{name:photo.id+'.jpg',mimeType:'image/jpeg',buffer:fs.readFileSync(photoDir+'/image_refs/'+photo.id+'.bin')});
   // Manual reference confirmation is exercised separately from real-model accuracy.
   await page.evaluate(()=>renderImageResults([],'Test der privaten Referenzverwaltung; kein Erkennungstest'));
   await page.getByRole('button',{name:'Sonstiges eintragen',exact:true}).click();await page.locator('#confirm-other-existing').selectOption(sp.id);
   await page.locator('#confirm-filename').fill('private-case-'+sp.id+'.jpg');await page.locator('#confirm-save-ref').check();await page.locator('#confirm-save-btn').click();
   await page.locator('#image-confirm-feedback').filter({hasText:'Bestätigt: '+sp.name_de}).waitFor();
   const hist=await page.evaluate(()=>imageHistory);assert.equal(hist.confirmed_species_id,sp.id);report.species.push({species:sp.sci,save:true});
  }
  const refs=await page.evaluate(()=>ownImageReferences());assert.equal(refs.length,14);assert.equal(new Set(refs.map(r=>r.species_id)).size,14);
  const token=await page.evaluate(()=>authToken),first=refs[0];
  assert.equal((await api.post(base+'/api/images/own',{headers:{Authorization:'Bearer '+token},data:first})).status(),200);
  assert.equal((await api.post(base+'/api/images/own',{headers:{Authorization:'Bearer '+token},data:{...first,species_id:catalog.find(s=>s.id!==first.species_id).id}})).status(),409);
  report.checks.push({name:'same-photo deduplication and conflicting species rejection',pass:true});
  const other=await (await api.post(base+'/api/auth/login',{data:{email:'field@ribby.test',password:'SystemTestOnly2026!'}})).json();
  const otherRefs=await (await api.get(base+'/api/images/own',{headers:{Authorization:'Bearer '+other.token}})).json();assert.equal(otherRefs.length,0);
  assert.equal((await api.delete(base+'/api/images/own/'+first.id,{headers:{Authorization:'Bearer '+other.token}})).status(),404);
  report.checks.push({name:'private references inaccessible to other user',pass:true});
  const backup=await (await api.get(base+'/api/backup/export',{headers})).json();for(const ref of refs)assert.ok(backup.data.refimages.some(r=>r.id===ref.id));
  assert.equal((await api.get(base+'/api/backup/export',{headers:{Authorization:'Bearer '+token}})).status(),403);
  report.checks.push({name:'admin backup includes all 14 private references, regular user denied',pass:true});
  await page.getByText('Analyse-Einstellungen',{exact:true}).click();await page.locator('#image-online').uncheck();
  await page.evaluate(()=>{extractImageVector=async()=>[1,...new Array(511).fill(0)];});
  assert.match(await analyze(page),/abgeschlossen/);assert.match(await page.locator('#results-out').innerText(),/14 von 14 Arten/);
  report.checks.push({name:'all private species references usable with online sources disabled (deterministic inference)',pass:true});
  await page.getByRole('button',{name:'Profil',exact:true}).click();await page.getByRole('button',{name:'Meine Referenzfotos',exact:true}).click();
  for(const [index,sp] of catalog.entries()){
   const row=page.locator('#image-profile-list .image-own-row').filter({hasText:'private-case-'+sp.id+'.jpg'});await row.waitFor();await row.getByRole('button',{name:'Löschen',exact:true}).click();await row.waitFor({state:'detached'});report.species[index].delete=true;
  }
  assert.equal((await page.evaluate(()=>ownImageReferences())).length,0);assert.equal(await page.evaluate(async()=>(await dbAll('imagefeatures')).filter(r=>r.id.includes('bioclip')).length),0);
  report.pass=true;console.log('PRIVATE REFERENCES OK: 14/14 species save/use/delete; ownership, deduplication and backup checked');
 }catch(e){report.pass=false;report.error=e.message;throw e;}
 finally{fs.writeFileSync('reports/system_private_species.json',JSON.stringify(report,null,2)+'\n');await browser.close();await api.dispose();}
})().catch(e=>{console.error(e);process.exitCode=1;});
