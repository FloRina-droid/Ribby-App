// Uses the actual app ranking function, with frozen models and disjoint queries.
const fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const work='accuracy_work/v3';
const manifest=JSON.parse(fs.readFileSync(work+'/training_manifest.json','utf8'));
const baseline=JSON.parse(fs.readFileSync(fs.existsSync('reports/reference_manifest_v2.json')?'reports/reference_manifest_v2.json':'dev/benchmark-manifest.json','utf8'));
const holdout=JSON.parse(fs.readFileSync(work+'/holdout_manifest.json','utf8'));
const previous=JSON.parse(fs.readFileSync('reports/accuracy_test_manifest.json','utf8'));
const oldQueries=JSON.parse(fs.readFileSync(fs.existsSync('reports/accuracy_regression_vectors_v2.json')?'reports/accuracy_regression_vectors_v2.json':'dev/fresh-test-vectors.json','utf8'));
const config=JSON.parse(fs.readFileSync('image_metric.json','utf8'));
const keys={bioclip:'bioclip-v1-fp16-22a18d2-v1',dinov2:'dinov2-small-q8-c2bb04a-cls-v1'};
const html=fs.readFileSync('ribby_app.html','utf8');
let currentModel='bioclip';
const ctx=vm.createContext({document:{addEventListener(){},getElementById(){return {value:currentModel,addEventListener(){}};}},window:{addEventListener(){}},console});
vm.runInContext(html.slice(html.indexOf('// Photo mode:'),html.indexOf('// ── INIT ')),ctx);
const getVector=(ref,model,folder='references')=>JSON.parse(fs.readFileSync(`${work}/${folder}/image_vectors/${keys[model]}/${ref.id}.json`,'utf8')).vector;
const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
const report={metric_sha256:crypto.createHash('sha256').update(fs.readFileSync('image_metric.json')).digest('hex'),
    app_sha256:crypto.createHash('sha256').update(fs.readFileSync('ribby_app.html')).digest('hex'),
    design:'Primary: 112 new photographs, eight per species, distinct photo/observation/photographers from training. Secondary: 28 previous regression photographs.',
    primary:{},regression:{},reference_photos:896,selection:config.default};
function run(queries,model,kind){
 const rows=[];currentModel=model;
 const frozen=manifest.map(sp=>({...sp,references:ctx.selectDiverseImageReferences(sp.references,config.reference_limit).map(r=>({...r,vector:getVector(r,model)}))}));
 const old=baseline.map(sp=>({...sp,references:ctx.selectDiverseImageReferences(sp.references,16).map(r=>({...r,vector:getVector(r,model)}))}));
 for(const query of queries){
  const q=kind==='primary'?getVector(query,model,'holdout'):oldQueries[model+':'+query.id];
  const make=sp=>({species_id:sp.id,scientific_name:sp.sci,queryVector:q,references:sp.references.map(r=>({vector:r.vector,similarity:Math.max(0,dot(q,r.vector)),reference:r}))});
  const oldRanks=ctx.rankImageSpecies(old.map(make),model==='bioclip'?'centroid':'weighted2');
  const dataRanks=ctx.rankImageSpecies(frozen.map(make),model==='bioclip'?'centroid':'weighted2');
  const newRanks=ctx.rankImageSpecies(frozen.map(make),model==='bioclip'?'centroid':'weighted2',config.models[model]);
  const row={id:query.id,expected:query.scientific_name,species_id:query.species_id,
   before:oldRanks.map(r=>({species:r.scientific_name,similarity:r.similarity})),data_only:dataRanks.map(r=>({species:r.scientific_name,similarity:r.similarity})),after:newRanks.map(r=>({species:r.scientific_name,similarity:r.similarity}))};
  for(const side of ['before','data_only','after']){row[side+'_top1']=row[side][0].species===query.scientific_name;row[side+'_top3']=row[side].slice(0,3).some(r=>r.species===query.scientific_name);}
  assert.ok(newRanks.every(r=>Number.isFinite(r.similarity)&&r.similarity>=0&&r.similarity<=1));rows.push(row);
 }
 return {n:rows.length,before_top1:rows.filter(r=>r.before_top1).length,after_top1:rows.filter(r=>r.after_top1).length,
   before_top3:rows.filter(r=>r.before_top3).length,after_top3:rows.filter(r=>r.after_top3).length,
   data_only_top1:rows.filter(r=>r.data_only_top1).length,data_only_top3:rows.filter(r=>r.data_only_top3).length,
   improved:rows.filter(r=>!r.before_top1&&r.after_top1).length,regressed:rows.filter(r=>r.before_top1&&!r.after_top1).length,rows};
}
for(const model of Object.keys(keys)){
 report.primary[model]=run(holdout,model,'primary');report.regression[model]=run(previous,model,'regression');
 console.log(model,JSON.stringify({primary:{...report.primary[model],rows:undefined},regression:{...report.regression[model],rows:undefined}}));
}
fs.writeFileSync('reports/image_accuracy_v3.json',JSON.stringify(report,null,2)+'\n');
