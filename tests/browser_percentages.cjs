// UI correctness uses a frozen real embedding; accuracy is measured separately.
const fs=require('node:fs'),assert=require('node:assert/strict');
const {launch,login,selectPhoto,analyze}=require('./browser_helpers.cjs');
const probe=JSON.parse(fs.readFileSync('reports/accuracy_calibration_probe.json','utf8'))[0];
const vector=JSON.parse(fs.readFileSync('accuracy_work/calibration/probe/image_vectors/bioclip-v1-fp16-22a18d2-v1/'+probe.id+'.json','utf8')).vector;
const buffer=fs.readFileSync('accuracy_work/calibration/probe/image_refs/'+probe.id+'.bin');
const rows=[];
(async()=>{
 const browser=await launch();
 try{
  const page=await browser.newPage();await login(page);
  await page.evaluate(v=>{window.extractImageVector=async()=>v;},vector);
  async function run(name){await selectPhoto(page,{name,mimeType:'image/jpeg',buffer});assert.match(await analyze(page),/abgeschlossen/);}
  await run('percent-confirmation.jpg');
  const matches=await page.evaluate(()=>imageMatches);assert.ok(matches.every(m=>m.score_type==='calibrated_probability'));
  await page.locator('#results-out .mcard').first().getByRole('button',{name:'Bestätigen',exact:true}).click();
  assert.match(await page.locator('#confirm-file-info').innerText(),/Trefferchance/);
  await page.locator('#confirm-other-sp').check();
  assert.equal(await page.evaluate(()=>imageMatches[0].probability),matches[0].probability);
  await page.locator('#confirm-other-sp').uncheck();
  rows.push({case:'manual_toggle_does_not_mutate_analysis_probabilities',pass:true});
  const chosen=matches[1];await page.locator('#confirm-sp-search').fill(chosen.scientific_name);
  const expected=await page.evaluate(id=>imageScorePercent(imageMatches.find(m=>m.species_id===id)),chosen.species_id);
  assert.ok((await page.locator('#confirm-file-info').innerText()).includes(expected));
  assert.equal(await page.evaluate(()=>_confirmMatch.probability),chosen.probability);
  rows.push({case:'manual_selection_uses_selected_species_probability',pass:true});
  const outside=await page.evaluate(()=>allSp.find(sp=>!imageMatches.some(m=>m.species_id===sp.id)));
  await page.locator('#confirm-sp-search').fill(outside.sci);
  assert.doesNotMatch(await page.locator('#confirm-file-info').innerText(),/%/);
  assert.equal(await page.evaluate(()=>_confirmMatch.score_type),'unscored_confirmation');
  await page.locator('#confirm-save-btn').click();await page.locator('#confirm-modal').waitFor({state:'hidden'});
  const saved=await page.evaluate(()=>imageHistory);
  await page.getByRole('button',{name:'Verlauf',exact:true}).click();
  const historyRow=page.locator('#hist-out tbody tr').filter({hasText:'percent-confirmation.jpg'});
  assert.equal(await historyRow.locator('td').nth(2).innerText(),'–');
  rows.push({case:'manual_species_outside_suggestions_has_no_invented_percent',pass:true});
  await page.evaluate(id=>viewHist(id),saved.id);
  assert.match(await page.locator('#results-out').innerText(),/Trefferchance/);
  rows.push({case:'stored_calibration_survives_history_reload',pass:true});
  const legacy=await page.evaluate(async()=>{
   const matches=imageMatches.map(({probability,score_type,calibration_id,score_context,compared_species,...m})=>({...m,confidence:m.similarity}));
   return (await imageApi('/api/history',{method:'POST',body:JSON.stringify({media_type:'image',filename:'legacy-percent.jpg',matches})})).json();
  });
  await page.evaluate(id=>viewHist(id),legacy.id);assert.match(await page.locator('#results-out .mcard').first().innerText(),/Bildähnlichkeit/);
  assert.doesNotMatch(await page.locator('#results-out .mcard').first().innerText(),/Trefferchance/);
  rows.push({case:'legacy_similarity_is_not_relabelled_as_probability',pass:true});
  await page.getByText('Analyse-Einstellungen',{exact:true}).click();
  for(const limit of ['8','16','32']){
   await page.locator('#image-reference-count').selectOption(limit);await run('percent-scope-'+limit+'.jpg');
   assert.ok(await page.evaluate(()=>imageMatches.every(m=>m.score_type==='calibrated_probability')));
  }
  rows.push({case:'all_three_reference_profiles_are_calibrated',pass:true});
  await page.locator('#image-reference-count').selectOption('16');
  await page.route('**/api/images/references?*',async route=>{const response=await route.fetch();const data=await response.json();if(data.references[0]?.scientific_name===probe.scientific_name)data.references.pop();await route.fulfill({json:data});});
  await run('percent-changed-references.jpg');
  assert.ok(await page.evaluate(()=>imageMatches.every(m=>m.score_type==='similarity')));
  assert.match(await page.locator('#results-out .mcard').first().innerText(),/Bildähnlichkeit/);
  rows.push({case:'changed_reference_set_falls_back_to_similarity',pass:true});
  await page.screenshot({path:'dev/percentages-preview.png',fullPage:true});
  fs.writeFileSync('reports/system_percentages_v4.json',JSON.stringify({pass:true,cases:rows,query_embedding:'frozen real BioCLIP vector; no recognition accuracy inferred from these UI cases'},null,2)+'\n');
  console.log('PERCENTAGE UI',rows.length+'/'+rows.length,'passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
