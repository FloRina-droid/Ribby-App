const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('ribby_app.html','utf8'),elements={};let exported;
const ctx=vm.createContext({console,Blob,document:{addEventListener(){},getElementById(id){return elements[id]||(elements[id]={value:'bioclip',addEventListener(){}});},createElement(){return {click(){}};}},window:{addEventListener(){}},URL:{createObjectURL(blob){exported=blob;return 'blob:test';},revokeObjectURL(){}},toast(){},escHtml:s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')});
vm.runInContext(html.slice(html.indexOf('// Photo mode:'),html.indexOf('// ── INIT ')),ctx);
function fixture(n=14){
 const rows=Array.from({length:n},(_,i)=>{const vector=[Math.cos(i*2*Math.PI/n),Math.sin(i*2*Math.PI/n)];return {species_id:'id'+i,scientific_name:'Sp '+i,queryVector:[1,0],references:[{vector,similarity:Math.max(0,vector[0]),reference:{id:'ref'+i,license:'CC0 1.0'}}]};});
 const model_key=vm.runInContext('imageModelKey()',ctx),species=rows.map(r=>r.scientific_name.toLowerCase());
 return {rows,config:{method:'metric',alpha:1,model_key,dimensions:2,species,center:[0,0],weights:[[1,0],[0,1]]},
  calibration:{method:'temperature-scaling',id:'fixture-calibration',species,reference_sets:{'1':Object.fromEntries(species.map((s,i)=>[s,['ref'+i]]))},models:{bioclip:{model_key,profiles:{'1':{temperature:.1,species_count:n,model_key}}}}}};
}
function ranked(f,all=true){ctx.f=f;return vm.runInContext(`rankImageSpecies(f.rows,'centroid',f.config,f.calibration,${all})`,ctx);}
const base=fixture(),result=ranked(base);
assert.equal(result.length,14);assert.equal(result[0].score_type,'calibrated_probability');
assert.ok(Math.abs(result.reduce((s,r)=>s+r.probability,0)-1)<1e-12);
const shown=ranked(base,false);assert.equal(shown.length,5);assert.ok(shown.reduce((s,r)=>s+r.probability,0)<1);
assert.ok(result.every((r,i)=>i===0||r.probability<=result[i-1].probability));
for(const change of [f=>f.rows.pop(),f=>f.rows[0].references[0].reference.id='changed',f=>f.rows[0].references[0].reference.license='private',
 f=>f.rows[0].scientific_name='New species',f=>f.calibration.models.bioclip.profiles['1'].temperature=NaN,
 f=>f.calibration.models.bioclip.profiles['1'].model_key='other-model',f=>f.rows[0].references.push({...f.rows[0].references[0]})]){
 const f=fixture();change(f);assert.ok(ranked(f).every(r=>r.score_type==='similarity'));
}
ctx.fixtureResult=result;
assert.equal(vm.runInContext("imageScorePercent({score_type:'calibrated_probability',calibration_id:'x',probability:.999999})",ctx),'>99%');
assert.equal(vm.runInContext("imageScorePercent({score_type:'calibrated_probability',calibration_id:'x',probability:.00001})",ctx),'<1%');
assert.equal(vm.runInContext("imageScorePercent({similarity:1})",ctx),'100%');
assert.equal(vm.runInContext("imageScorePercent({score_type:'unscored_confirmation'})",ctx),'–');
ctx._confirmMedia='image';ctx._confirmMatch={confidence:.99,probability:.99,score_type:'calibrated_probability',calibration_id:'old'};
vm.runInContext("imageMatches=[{species_id:'known',similarity:.8,confidence:.3,probability:.3,score_type:'calibrated_probability',calibration_id:'current'}]; updateImageConfirmationScore({id:'known'})",ctx);
assert.match(elements['confirm-file-info'].innerHTML,/30%/);assert.equal(ctx._confirmMatch.confidence,.3);
vm.runInContext("updateImageConfirmationScore({id:'outside-results'})",ctx);
assert.doesNotMatch(elements['confirm-file-info'].innerHTML,/%/);assert.equal(ctx._confirmMatch.score_type,'unscored_confirmation');
assert.equal(ctx._confirmMatch.calibration_id,undefined);
vm.runInContext("_confirmMatch=imageMatches[0]; updateImageConfirmationScore(null)",ctx);
assert.equal(vm.runInContext('imageMatches[0].probability',ctx),.3);
ctx.allSp=[];ctx.entry={media_type:'image',confirmed_species_id:'deleted',matches:[{species_id:'other',confidence:.99,similarity:.99}]};
assert.equal(vm.runInContext("imageScorePercent(historyTopMatch(entry))",ctx),'–');

const parse=csv=>csv.replace(/^\uFEFF/,'').trim().split(/\r?\n/).map(line=>Array.from(line.matchAll(/"((?:[^"]|"")*)"(?:;|$)/g),m=>m[1].replace(/""/g,'"')));
(async()=>{
 ctx.serverMode=true;ctx.serverLoadSpecies=async()=>[{id:'a',name_de:'Art A',sci:'Sp a'},{id:'b',name_de:'Art B',sci:'Sp b'}];
 ctx.serverLoadHistory=async()=>[
  {id:'1',media_type:'image',filename:'photo;one.jpg',confirmed_species_id:'a',created_at:'2026-01-01',matches:[{species_id:'a',similarity:.9,confidence:.62,probability:.62,score_type:'calibrated_probability',calibration_id:'calib-v1'}]},
  {id:'2',media_type:'image',filename:'manual.jpg',confirmed_species_id:'b',created_at:'2026-01-01',matches:[]},
  {id:'3',filename:'audio.wav',created_at:'2026-01-01',matches:[{species_name_de:'Art A',confidence:.57}]}
 ];
 let start=html.indexOf('async function exportHistCSV()'),end=html.indexOf('// ── KARTE',start);
 vm.runInContext(html.slice(start,end),ctx);await vm.runInContext('exportHistCSV()',ctx);
 const history=parse(await exported.text());assert.equal(history[0].length,11);assert.ok(history.every(r=>r.length===11));
 assert.equal(history[1][4],'62');assert.equal(history[1][9],'calibrated_probability');assert.equal(history[1][10],'calib-v1');
 assert.equal(history[2][4],'');assert.equal(history[2][9],'unscored_confirmation');assert.equal(history[3][4],'57');
 start=html.indexOf('function exportBatchCSV(');end=html.indexOf('\n',start);
 vm.runInContext(html.slice(start,end),ctx);vm.runInContext("exportBatchCSV([{file:'audio.wav',matches:[{species_name_de:'Art A',confidence:.57}]}])",ctx);
 const batch=parse(await exported.text());assert.equal(batch[0].length,batch[1].length);assert.equal(batch[1][1],'Audio');assert.equal(batch[1][4],'57');
 console.log('Calibration math, scope fallbacks, formatting, manual correction and CSV checks passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
