const work=process.env.RIBBY_ACCURACY_WORKSPACE||'accuracy_work';
const fs=require('node:fs'),vm=require('node:vm');
const refs=JSON.parse(fs.readFileSync(work+'/benchmark-manifest.json','utf8')),vectors=JSON.parse(fs.readFileSync(work+'/benchmark-vectors.json','utf8')),queries=JSON.parse(fs.readFileSync(work+'/test_data/manifest.json','utf8')),queryVectors=JSON.parse(fs.readFileSync(work+'/fresh-test-vectors.json','utf8')),selection=JSON.parse(fs.readFileSync(work+'/model-selection.json','utf8'));
if(selection.selected.model!=='bioclip'||selection.selected.method!=='centroid')throw new Error('Freeze the validation choice before testing');
const html=fs.readFileSync('ribby_app.html','utf8'),ctx=vm.createContext({document:{addEventListener(){},getElementById(){return {addEventListener(){}};}},window:{addEventListener(){}},console});vm.runInContext(html.slice(html.indexOf('// Photo mode:'),html.indexOf('// ── INIT ')),ctx);
const dot=(a,b)=>a.reduce((sum,x,i)=>sum+x*b[i],0),normalize=v=>{const norm=Math.sqrt(dot(v,v));return v.map(x=>x/norm);};
const rows=[];
for(const query of queries){
 const row={id:query.id,expected:query.scientific_name,source_url:query.source_url};
 for(const model of ['dinov2','bioclip']){
  const q=queryVectors[model+':'+query.id],prefix=model==='dinov2'?'original':'bioclip';
  const matches=refs.map(sp=>{
   const selected=model==='dinov2'?sp.references.filter(r=>r.provider==='Wikimedia Commons').slice(0,2).concat(sp.references.filter(r=>r.provider==='iNaturalist').slice(0,2)):ctx.selectDiverseImageReferences(sp.references,16);
   const features=selected.map(r=>vectors[prefix+':'+r.id].vector),sims=features.map(v=>Math.max(0,dot(q,v))).sort((a,b)=>b-a);
   const score=model==='dinov2'?.6*sims[0]+.4*sims[1]:dot(q,normalize(features[0].map((_,j)=>features.reduce((sum,v)=>sum+v[j],0)/features.length)));
   return {species:sp.sci,score};
  }).sort((a,b)=>b.score-a.score);
  row[model]={top1:matches[0].species===query.scientific_name,top3:matches.slice(0,3).some(m=>m.species===query.scientific_name),matches:matches.slice(0,3)};
 }
 rows.push(row);
}
const metrics={};for(const model of ['dinov2','bioclip'])metrics[model]={correct:rows.filter(r=>r[model].top1).length,n:rows.length,top1:rows.filter(r=>r[model].top1).length/rows.length,top3_correct:rows.filter(r=>r[model].top3).length,top3:rows.filter(r=>r[model].top3).length/rows.length};
const report={reference_images:447,species:14,design:'28 fresh iNaturalist research-grade photos (2 per species). Canonical photo IDs, observations and normalized creator names excluded from all 447 references. Input follows app JPEG normalization. Configuration selected by 5-fold grouped validation before this test.',baseline:'DINOv2, 4 references per species, weighted top two',optimized:'BioCLIP, 16 diverse references per species, normalized class centroid',metrics,model_selection:selection,rows,limitations:['Small collection; no field validation or expert relabeling.','Possible pretraining overlap of foundation models is unknown.','Similar amphibian species may require additional observations.']};
fs.mkdirSync('reports',{recursive:true});fs.writeFileSync('reports/image_accuracy_v2.json',JSON.stringify(report,null,2));console.log(JSON.stringify({metrics,design:report.design},null,2));
