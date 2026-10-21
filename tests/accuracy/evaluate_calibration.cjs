// Evaluate frozen confidence estimates using the actual app ranking code.
const fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const html=fs.readFileSync('ribby_app.html','utf8'),metric=JSON.parse(fs.readFileSync('image_metric.json','utf8')),calibration=JSON.parse(fs.readFileSync('image_calibration.json','utf8'));
const manifest=JSON.parse(fs.readFileSync('reports/reference_manifest_v3.json','utf8'));
const probe=JSON.parse(fs.readFileSync('reports/accuracy_calibration_probe.json','utf8'));
const previous=JSON.parse(fs.readFileSync('reports/accuracy_holdout_v3.json','utf8'));
let model='bioclip';
const ctx=vm.createContext({document:{addEventListener(){},getElementById(){return {value:model,addEventListener(){}};}},window:{addEventListener(){}},console});
vm.runInContext(html.slice(html.indexOf('// Photo mode:'),html.indexOf('// ── INIT ')),ctx);
const vector=(folder,key,id)=>JSON.parse(fs.readFileSync(`${folder}/image_vectors/${key}/${id}.json`,'utf8')).vector;
const dot=(a,b)=>a.reduce((sum,x,i)=>sum+x*b[i],0);
function summarize(rows){
 const n=rows.length,correct=rows.reduce((sum,r)=>sum+r.correct,0);
 const error=key=>rows.reduce((sum,r)=>sum+(r[key]-Number(r.correct))**2,0)/n;
 const mean=key=>rows.reduce((sum,r)=>sum+r[key],0)/n;
 const ece=(key,bins)=>Array.from({length:bins},(_,i)=>{const chosen=rows.filter(r=>Math.min(bins-1,Math.floor(r[key]*bins))===i);return chosen.length?chosen.length/n*Math.abs(chosen.reduce((s,r)=>s+r[key],0)/chosen.length-chosen.filter(r=>r.correct).length/chosen.length):0;}).reduce((a,b)=>a+b,0);
 let seed=4721;const random=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/4294967296);
 const deltas=[];
 for(let b=0;b<2000;b++){let sum=0;for(let i=0;i<n;i++){const r=rows[Math.floor(random()*n)];sum+=(r.probability-Number(r.correct))**2-(r.similarity-Number(r.correct))**2;}deltas.push(sum/n);}
 deltas.sort((a,b)=>a-b);
 return {n,correct,accuracy:correct/n,mean_similarity:mean('similarity'),mean_probability:mean('probability'),
  raw_as_chance_brier:error('similarity'),calibrated_brier:error('probability'),raw_ece10:ece('similarity',10),calibrated_ece10:ece('probability',10),
  raw_ece5:ece('similarity',5),calibrated_ece5:ece('probability',5),paired_brier_delta_95:[deltas[49],deltas[1949]],
  selective:[.5,.7,.8,.9].map(threshold=>{const selected=rows.filter(r=>r.probability>=threshold);return {threshold,n:selected.length,correct:selected.filter(r=>r.correct).length};}),rows};
}
const output={calibration_id:calibration.id,calibration_sha256:crypto.createHash('sha256').update(fs.readFileSync('image_calibration.json')).digest('hex'),
 metric_sha256:calibration.metric_sha256,app_sha256:crypto.createHash('sha256').update(fs.readFileSync('ribby_app.html')).digest('hex'),
 primary:{},regression:{},ranking_changes:0,normalization_errors:0};
for(model of ['bioclip','dinov2']){
 const key=metric.models[model].model_key;
 const integrity=JSON.parse(fs.readFileSync('image_reference_integrity.json','utf8'));
 const all=manifest.map(sp=>({...sp,references:sp.references.map(ref=>{
  const saved=JSON.parse(fs.readFileSync(`accuracy_work/v3/references/image_vectors/${key}/${ref.id}.json`,'utf8'));
  assert.equal(saved.image_sha256,integrity.images[ref.id]);
  return {...ref,vector:saved.vector,image_sha256:saved.image_sha256};
 })}));
 output.primary[model]={};output.regression[model]={};
 for(const limit of [8,16,32])for(const [kind,queries,folder] of [['primary',probe,'accuracy_work/calibration/probe'],['regression',previous,'accuracy_work/v3/holdout']]){
  const rows=[];
  for(const ref of queries){
   const q=vector(folder,key,ref.id),input=all.map(sp=>({species_id:sp.id,scientific_name:sp.sci,queryVector:q,references:ctx.selectDiverseImageReferences(sp.references,limit).map(r=>({vector:r.vector,similarity:Math.max(0,dot(q,r.vector)),reference:r}))}));
   const raw=ctx.rankImageSpecies(input,'centroid',metric.models[model],null,true),ranks=ctx.rankImageSpecies(input,'centroid',metric.models[model],calibration,true);
   assert.deepEqual(Array.from(ranks,r=>r.scientific_name),Array.from(raw,r=>r.scientific_name));
   assert.equal(ranks.length,14);assert.ok(ranks.every(r=>r.score_type==='calibrated_probability'&&r.confidence>=0&&r.confidence<=1));
   assert.ok(Math.abs(ranks.reduce((sum,r)=>sum+r.probability,0)-1)<1e-12);
   const top=ranks[0];
   rows.push({id:ref.id,species_id:ref.species_id,expected:ref.scientific_name,predicted:top.scientific_name,correct:top.scientific_name===ref.scientific_name,
    similarity:top.similarity,probability:top.probability,top3:ranks.slice(0,3).some(r=>r.scientific_name===ref.scientific_name),
    matches:ranks.slice(0,5).map(r=>({species:r.scientific_name,similarity:r.similarity,probability:r.probability}))});
  }
  const result=summarize(rows);output[kind][model][String(limit)]=result;
  console.log('CALIBRATION CHECK',kind,model,limit,JSON.stringify({...result,rows:undefined,selective:undefined}));
 }
}
fs.writeFileSync('reports/calibration_evaluation_v4.json',JSON.stringify(output,null,2)+'\n');
