const fs=require('node:fs'),assert=require('node:assert/strict');
const {launch,login,selectPhoto,base,photoDir}=require('./browser_helpers.cjs');
const catalog=JSON.parse(fs.readFileSync('image_reference_catalog.json','utf8'));
const photo={name:'regression.jpg',mimeType:'image/jpeg',buffer:fs.readFileSync(photoDir+'/image_refs/92dfb549fc26d536f568305c0c93c6cc.bin')};
(async()=>{
 const browser=await launch(),rows=[];
 try{
  const page=await browser.newPage();page.setDefaultTimeout(20000);await login(page,'admin@ribby.test');await selectPhoto(page,photo);
  const original=await page.locator('#image-preview').evaluate(i=>({w:i.naturalWidth,h:i.naturalHeight}));
  await page.evaluate(async()=>{_currentGPS={lat:52.5,lon:13.4,acc:0};imageCrop={x:0,y:0,width:80,height:80};await applyImageCrop();});
  assert.equal(await page.locator('#image-preview').evaluate(i=>i.naturalWidth),80);assert.equal(await page.evaluate(()=>_currentGPS.lat),52.5);
  await page.evaluate(()=>resetImageCrop());await page.waitForFunction(w=>document.getElementById('image-preview').naturalWidth===w,original.w);assert.equal(await page.evaluate(()=>_currentGPS.lon),13.4);
  rows.push({name:'crop and full-photo restore retain explicit GPS',pass:true});
  // Exercise Ribby's unchanged audio engine with one known synthetic PCM fixture.
  const samples=22050*2,wav=Buffer.alloc(44+samples*2);wav.write('RIFF');wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(22050,24);wav.writeUInt32LE(44100,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(samples*2,40);
  for(let i=0;i<samples;i++)wav.writeInt16LE(Math.round(16000*Math.sin(2*Math.PI*630*i/22050)),44+2*i);
  const sp=catalog.find(s=>s.sci==='Bufo bufo');
  const ref=await page.evaluate(async data=>{const file=new File([b64ToBuffer(data.bytes)],'synthetic-audio.wav',{type:'audio/wav'});return serverUploadRefAudio(file,data.id);},{bytes:wav.toString('base64'),id:sp.id});
  try{
   await page.locator('#media-audio').click();await page.locator('#file-input').setInputFiles({name:'synthetic-audio.wav',mimeType:'audio/wav',buffer:wav});
   await page.locator('#analyze-btn').click();await page.locator('#results-out .mcard').first().waitFor();assert.match(await page.locator('#results-out .mcard').first().innerText(),/Erdkröte/);
   await page.locator('#results-out .mcard').first().getByRole('button',{name:/Bestätigen/}).click();assert.match(await page.locator('#confirm-save-label').innerText(),/Referenz-Audio/);await page.evaluate(()=>closeModal('confirm-modal'));
   rows.push({name:'actual audio decoding, feature extraction and confirmation after photo mode (synthetic fixture, no species accuracy claim)',pass:true});
  }finally{await page.evaluate(id=>serverDeleteRefAudio(id),ref.id);}
  await page.locator('#media-image').click();await selectPhoto(page,photo);await page.evaluate(()=>renderImageResults([],'Manuelle Ergänzung'));
  await page.getByRole('button',{name:'Sonstiges eintragen',exact:true}).click();await page.locator('#confirm-other-name').fill('Testspecies diagnosticus');await page.locator('#confirm-save-btn').click();
  try{
   await page.locator('#image-confirm-feedback').filter({hasText:'Testspecies diagnosticus'}).waitFor();
   const added=await page.evaluate(async()=>(await serverLoadSpecies()).find(s=>s.sci==='Testspecies diagnosticus'));assert.ok(added?.id);rows.push({name:'admin can add and confirm an unlisted species',pass:true});
  }finally{await page.evaluate(async()=>{for(const s of await serverLoadSpecies())if(s.sci==='Testspecies diagnosticus')await serverDeleteSpecies(s.id);});}
  await page.evaluate(()=>{lang='en';applyLang();showDsgvo();});
  const notice=await page.locator('#dsgvo-overlay').innerText();assert.match(notice,/Hugging Face/);assert.match(notice,/Technical connection data/);assert.doesNotMatch(notice,/All data is stored exclusively locally/);
  rows.push({name:'English privacy notice accurately describes external model and reference connections',pass:true});
  console.log('REGRESSIONS OK: GPS crop/restore, actual audio engine, new-species confirmation, English disclosure');
 }finally{fs.writeFileSync('reports/system_regressions.json',JSON.stringify(rows,null,2)+'\n');await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
