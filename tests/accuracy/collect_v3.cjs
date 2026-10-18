// Real inference with the same worker and query JPEG normalization as Ribby.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require('playwright');
const work=path.resolve(process.env.RIBBY_EMBEDDING_WORKSPACE||'accuracy_work/v3');
const models={bioclip:'bioclip-v1-fp16-22a18d2-v1',dinov2:'dinov2-small-q8-c2bb04a-cls-v1'};
const input=process.env.RIBBY_V3_INPUT||'all';
(async()=>{
 const context=await chromium.launchPersistentContext(path.resolve(process.env.RIBBY_BROWSER_CACHE||path.join(work,'browser_cache')),{executablePath:process.env.RIBBY_BROWSER_PATH||'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true});
 try{
  const page=await context.newPage();await page.goto('http://127.0.0.1:7434',{waitUntil:'domcontentloaded'});
  await page.evaluate(()=>{
   const url=URL.createObjectURL(new Blob([document.getElementById('image-worker-code').textContent],{type:'text/javascript'}));
   window.v3Worker=new Worker(url,{type:'module'});URL.revokeObjectURL(url);
   let sequence=0;const pending=new Map();
   v3Worker.onmessage=({data})=>{if(data.progress)return;const job=pending.get(data.id);if(!job)return;pending.delete(data.id);data.error?job.reject(new Error(data.error)):job.resolve(data.vector);};
   window.v3Extract=(blob,model)=>new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});v3Worker.postMessage({id,blob,model});});
  });
  const jobs=[];
  if(input==='probe')for(const ref of JSON.parse(fs.readFileSync(path.join(work,'probe_manifest.json'),'utf8')))
   jobs.push({ref,kind:'probe',normalize:true});
  if(input!=='holdout'&&input!=='probe')for(const species of JSON.parse(fs.readFileSync(path.join(work,'training_manifest.json'),'utf8')))
   for(const ref of species.references)jobs.push({ref,kind:'references',normalize:false});
  if(input!=='references'&&input!=='probe')for(const ref of JSON.parse(fs.readFileSync(path.join(work,'holdout_manifest.json'),'utf8')))
   jobs.push({ref,kind:'holdout',normalize:true});
  for(const [model,key] of Object.entries(models)){
   let computed=0,skipped=0;
   for(const [index,job] of jobs.entries()){
    const file=path.join(work,job.kind,'image_refs',job.ref.id+'.bin');
    const output=path.join(work,job.kind,'image_vectors',key,job.ref.id+'.json');
    if(fs.existsSync(output)){skipped++;continue;}
    const bytes=fs.readFileSync(file);
    const vector=await page.evaluate(async({base64,model,normalize})=>{
     let blob=new Blob([Uint8Array.from(atob(base64),c=>c.charCodeAt(0))]);
     if(normalize){
      const image=await createImageBitmap(blob),scale=Math.min(1,1600/Math.max(image.width,image.height)),canvas=document.createElement('canvas');
      canvas.width=Math.round(image.width*scale);canvas.height=Math.round(image.height*scale);
      const ctx=canvas.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,0,0,canvas.width,canvas.height);image.close();
      blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.9));
     }
     return v3Extract(blob,model);
    },{base64:bytes.toString('base64'),model,normalize:job.normalize});
    const expected=model==='bioclip'?512:384;
    if(vector.length!==expected||vector.some(x=>!Number.isFinite(x))||Math.abs(Math.sqrt(vector.reduce((sum,x)=>sum+x*x,0))-1)>.001)throw new Error('Invalid embedding '+job.ref.id);
    fs.mkdirSync(path.dirname(output),{recursive:true});
    fs.writeFileSync(output,JSON.stringify({model_key:key,reference_id:job.ref.id,image_sha256:crypto.createHash('sha256').update(bytes).digest('hex'),query_normalized:job.normalize,vector:vector.map(x=>Number(x.toFixed(8)))}));
    if(++computed%20===0)console.log('V3',model,job.kind,index+1+'/'+jobs.length,'computed',computed,'cached',skipped);
   }
   console.log('V3 COMPLETE',model,'computed',computed,'cached',skipped);
  }
 }finally{await context.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
