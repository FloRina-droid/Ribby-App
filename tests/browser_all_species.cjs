const fs=require('node:fs'),assert=require('node:assert/strict'),path=require('node:path'),crypto=require('node:crypto');
const {base,photoDir,launch,login,selectPhoto,analyze}=require('./browser_helpers.cjs');
const manifestFile=process.env.RIBBY_TEST_MANIFEST||(fs.existsSync('image_calibration.json')&&fs.existsSync('reports/accuracy_calibration_probe.json')?'reports/accuracy_calibration_probe.json':fs.existsSync('reports/accuracy_holdout_v3.json')?'reports/accuracy_holdout_v3.json':'reports/accuracy_test_manifest.json');
const manifest=JSON.parse(fs.readFileSync(manifestFile,'utf8'));
const queryDir=process.env.RIBBY_TEST_PHOTOS||(manifestFile.includes('calibration_probe')?'accuracy_work/calibration/probe':manifestFile.includes('holdout_v3')?'accuracy_work/v3/holdout':photoDir);
const expectCalibration=process.env.RIBBY_EXPECT_CALIBRATION==='1'||manifestFile.includes('calibration_probe');
const catalog=JSON.parse(fs.readFileSync('image_reference_catalog.json','utf8'));
const report={started_at:new Date().toISOString(),app_sha256:crypto.createHash('sha256').update(fs.readFileSync('ribby_app.html')).digest('hex'),input:manifest.length+' independent photos; normal app upload and real model inference',manifest:manifestFile,technical_cases:[],models:{},external_uploads:[],page_errors:[]};
const output=process.env.RIBBY_SYSTEM_REPORT||(expectCalibration?'reports/system_calibration_species.json':'reports/system_all_species.json');
function save(){fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');}
(async()=>{
 const browser=await launch();
 try{
  report.browser=browser.version();
  const context=await browser.newContext({viewport:{width:1440,height:1050}}),page=await context.newPage();
  page.setDefaultTimeout(25000);
  page.on('pageerror',e=>report.page_errors.push(e.message));
  page.on('request',r=>{if(r.method()!=='GET'&&!r.url().startsWith(base))report.external_uploads.push({url:r.url(),method:r.method()});});
  await login(page);
  assert.equal(await page.locator('#nav-admin').isVisible(),false);
  await page.getByText('Analyse-Einstellungen',{exact:true}).click();
  const referenceLimit=Number(await page.locator('#image-reference-count').inputValue());report.reference_limit=referenceLimit;
  for(const model of ['bioclip','dinov2']){
   await page.locator('#image-model').selectOption(model);
   const rows=[];report.models[model]=rows;
   for(const [index,query] of manifest.entries()){
    const start=Date.now(),row={id:query.id,expected:query.scientific_name,species_id:query.species_id};rows.push(row);
    try{
    const file={name:query.id+'.jpg',mimeType:'image/jpeg',buffer:fs.readFileSync(queryDir+'/image_refs/'+query.id+'.bin')};
     await selectPhoto(page,file);
     const status=await analyze(page);assert.match(status,/abgeschlossen/);
     assert.match(await page.locator('#results-out').innerText(),/14 von 14 Arten/);
     row.matches=await page.evaluate(()=>imageMatches.map(m=>({species:m.scientific_name,score:m.similarity,refs:m.nRefs,confidence:m.confidence,probability:m.probability,score_type:m.score_type,calibration_id:m.calibration_id})));
     assert.equal(row.matches.length,5);assert.ok(row.matches.every(m=>m.refs===referenceLimit&&Number.isFinite(m.score)&&m.score>=0&&m.score<=1));
     if(expectCalibration){
      assert.ok(row.matches.every(m=>m.score_type==='calibrated_probability'&&m.probability===m.confidence&&m.probability>=0&&m.probability<=1&&m.calibration_id));
      const p=row.matches[0].probability,expected=(p>.99?'>99':p<.01?'<1':String(Math.round(100*p)))+'%';
      assert.equal(await page.locator('#results-out .mcard .cnum').first().innerText(),expected);
      assert.match(await page.locator('#results-out .mcard').first().innerText(),/Trefferchance/);
     }
     const history=await page.evaluate(()=>imageHistory);
     assert.equal(history.media_type,'image');assert.ok(history.matches.every(m=>!m.queryVector&&!m.references&&!m.reference?.features&&!m.reference?.image_b64));
     if(expectCalibration)assert.ok(history.matches.every(m=>m.score_type==='calibrated_probability'&&m.calibration_id));
     // Exercise correction to the known test label even when prediction differs.
     await page.locator('#results-out .mcard').first().getByRole('button',{name:'Bestätigen',exact:true}).click();
     await page.locator('#confirm-sp-search').fill(query.scientific_name);
     assert.equal(await page.locator('#confirm-sp-id').inputValue(),query.species_id);
     await page.locator('#confirm-area').fill('Systemtest '+query.scientific_name);
     await page.evaluate(()=>{_currentGPS={lat:52.5,lon:13.4,acc:0};});
     assert.equal(await page.locator('#confirm-save-ref').isChecked(),false);
     await page.locator('#confirm-save-btn').click();
     const species=catalog.find(s=>s.id===query.species_id);
     await page.locator('#image-confirm-feedback').filter({hasText:'Bestätigt: '+species.name_de}).waitFor();
     const confirmed=await page.evaluate(()=>imageHistory);assert.equal(confirmed.confirmed_species_id,query.species_id);assert.equal(confirmed.area,'Systemtest '+query.scientific_name);
     assert.deepEqual(confirmed.gps,{lat:52.5,lon:13.4,acc:0});
     row.history_id=confirmed.id;row.top1=row.matches[0].species===query.scientific_name;row.top3=row.matches.slice(0,3).some(m=>m.species===query.scientific_name);row.technical_pass=true;
    }catch(e){row.technical_pass=false;row.error=e.message;await page.screenshot({path:'dev/all-species-failure.png'});}
    row.elapsed_ms=Date.now()-start;save();
    console.log(model+' '+(index+1)+'/'+manifest.length+' '+query.scientific_name+': '+(row.technical_pass?'flow OK; predicted '+row.matches[0].species:'FAIL '+row.error));
    if(!row.technical_pass)throw new Error('System test failed: '+row.error);
   }
  }
  // Open stored results for every species after normalization and confirmation.
  for(const species of catalog){
   const row=report.models.bioclip.find(r=>r.species_id===species.id);
   await page.evaluate(id=>viewHist(id),row.history_id);
   await page.locator('#results-out').filter({hasText:'Bestätigte Art: '+species.name_de}).waitFor();
   assert.equal(await page.locator('#results-out').getByRole('button',{name:'Bestätigen',exact:true}).count(),0);
   report.technical_cases.push({case:'stored_result',species:species.sci,pass:true});
  }
  assert.deepEqual(report.external_uploads,[]);assert.deepEqual(report.page_errors,[]);
  report.finished_at=new Date().toISOString();report.pass=true;save();
  for(const [model,rows] of Object.entries(report.models))console.log(model+': technical '+rows.filter(r=>r.technical_pass).length+'/'+rows.length+'; top1 '+rows.filter(r=>r.top1).length+'/'+rows.length+'; top3 '+rows.filter(r=>r.top3).length+'/'+rows.length);
 }catch(e){report.pass=false;report.error=e.message;save();throw e;}
 finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
