const work=process.env.RIBBY_ACCURACY_WORKSPACE||'accuracy_work';
const {chromium}=require('playwright');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.RIBBY_BROWSER_PATH||(process.platform==='win32'?'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe':undefined),headless:true});
 const page=await browser.newPage();
 page.on('console',m=>{if(m.text().startsWith('BENCH'))console.log(m.text());});
 await page.goto('http://127.0.0.1:7434',{waitUntil:'domcontentloaded'});
 const manifest=await page.evaluate(async()=>await (await fetch('/benchmark-manifest')).json());
 fs.writeFileSync(work+'/benchmark-manifest.json',JSON.stringify(manifest,null,2));
 const cachePath=work+'/benchmark-vectors.json',cache=fs.existsSync(cachePath)?JSON.parse(fs.readFileSync(cachePath,'utf8')):{};
 const refs=[...new Map(manifest.flatMap(s=>s.references).map(r=>[r.id,r])).values()];
 await page.evaluate(()=>{
   const url=URL.createObjectURL(new Blob([document.getElementById('image-worker-code').textContent],{type:'text/javascript'}));
   window.benchWorker=new Worker(url,{type:'module'});URL.revokeObjectURL(url);
   let seq=0;const pending=new Map();
   benchWorker.onmessage=({data})=>{if(data.progress)return;const job=pending.get(data.id);if(!job)return;pending.delete(data.id);if(data.error)job.reject(new Error(data.error));else job.resolve({vector:data.vector,mean:data.mean_vector});};
   window.benchExtract=(blob,profile)=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});benchWorker.postMessage({id,blob,profile});});
 });
 for(const profile of ['original','bioclip']){
   let i=0;
   for(const ref of refs){
     const key=profile+':'+ref.id;
     if(!cache[key]){
       try{cache[key]=await page.evaluate(async({id,profile})=>{const response=await fetch('/benchmark-image/'+id);if(!response.ok)throw new Error('HTTP '+response.status);return benchExtract(await response.blob(),profile);},{id:ref.id,profile});}
       catch(e){console.log('BENCH skipped',profile,ref.id,e.message);if(profile==='bioclip')throw e;}
     }
     if(++i%25===0){fs.writeFileSync(cachePath,JSON.stringify(cache));console.log('BENCH',profile,i+'/'+refs.length);}
   }
   fs.writeFileSync(cachePath,JSON.stringify(cache));
 }
 await browser.close();console.log('BENCH complete',refs.length,'images, two preprocessing profiles');
})().catch(e=>{console.error(e);process.exit(1);});
