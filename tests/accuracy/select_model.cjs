const work=process.env.RIBBY_ACCURACY_WORKSPACE||'accuracy_work';
const fs=require('node:fs'),crypto=require('node:crypto'),vm=require('node:vm');
const catalog=JSON.parse(fs.readFileSync(work+'/benchmark-manifest.json','utf8')),vectors=JSON.parse(fs.readFileSync(work+'/benchmark-vectors.json','utf8'));
const html=fs.readFileSync('ribby_app.html','utf8'),ctx=vm.createContext({document:{addEventListener(){},getElementById(){return {addEventListener(){}};}},window:{addEventListener(){}},console});
vm.runInContext(html.slice(html.indexOf('// Photo mode:'),html.indexOf('// ── INIT ')),ctx);
const creator=r=>String(r.creator||'').toLowerCase().replace(/^\s*(?:\(c\)|©)\s*/,'').replace(/,?\s*(?:some rights reserved|no rights reserved).*$/,'').replace(/[^\p{L}\p{N}]+/gu,'');
const fold=r=>parseInt(crypto.createHash('sha256').update('ribby-grouped-cv-v2:'+creator(r)).digest('hex').slice(0,8),16)%5;
const all=catalog.flatMap(s=>s.references.map(r=>({...r,species_id:s.id,fold:fold(r)})));
const dot=(a,b)=>{let sum=0;for(let i=0;i<a.length;i++)sum+=a[i]*b[i];return sum;};
function scoreValues(sims,method){sims.sort((a,b)=>b-a);if(method==='nearest')return sims[0]||0;if(method==='top3')return sims.slice(0,3).reduce((s,x)=>s+x,0)/Math.min(3,sims.length);return sims.length>1?.6*sims[0]+.4*sims[1]:sims[0]||0;}
const results=[];
for(const model of ['original','bioclip'])for(const method of ['nearest','weighted2','top3','centroid']){
 let correct=0,top3=0,total=0;
 for(let f=0;f<5;f++){
  const training=catalog.map(s=>({id:s.id,refs:ctx.selectDiverseImageReferences(all.filter(r=>r.species_id===s.id&&r.fold!==f),16)}));
  for(const s of training){
   const items=s.refs.map(r=>vectors[model+':'+r.id].vector),avg=items[0].map((_,i)=>items.reduce((sum,v)=>sum+v[i],0)/items.length),norm=Math.sqrt(dot(avg,avg));s.centroid=avg.map(x=>x/norm);
  }
  for(const query of all.filter(r=>r.fold===f)){
   const q=vectors[model+':'+query.id].vector;
   const scores=training.map(s=>({id:s.id,score:method==='centroid'?dot(q,s.centroid):scoreValues(s.refs.map(r=>Math.max(0,dot(q,vectors[model+':'+r.id].vector))),method)})).sort((a,b)=>b.score-a.score);
   correct+=scores[0].id===query.species_id;top3+=scores.slice(0,3).some(s=>s.id===query.species_id);total++;
  }
 }
 results.push({model,method,reference_limit:16,n:total,correct,top1:correct/total,top3:top3/total});
}
results.sort((a,b)=>b.top1-a.top1||b.top3-a.top3);
const selection={design:'5-fold validation grouped by normalized photographer name; all reference images, no fresh test image used',selected:results[0],candidates:results};
fs.writeFileSync(work+'/model-selection.json',JSON.stringify(selection,null,2));console.log(JSON.stringify(selection,null,2));
