const work=process.env.RIBBY_ACCURACY_WORKSPACE||'accuracy_work';
const {chromium}=require('playwright'),fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.RIBBY_BROWSER_PATH||(process.platform==='win32'?'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe':undefined),headless:true});
 const page=await browser.newPage();await page.goto('http://127.0.0.1:7434',{waitUntil:'domcontentloaded'});
 await page.evaluate(()=>{
  const url=URL.createObjectURL(new Blob([document.getElementById('image-worker-code').textContent],{type:'text/javascript'}));window.freshWorker=new Worker(url,{type:'module'});URL.revokeObjectURL(url);
  let seq=0;const pending=new Map();freshWorker.onmessage=({data})=>{if(data.progress)return;const j=pending.get(data.id);pending.delete(data.id);if(data.error)j.reject(new Error(data.error));else j.resolve(data.vector);};
  window.freshExtract=(blob,model)=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});freshWorker.postMessage({id,blob,model});});
 });
 const manifest=JSON.parse(fs.readFileSync(work+'/test_data/manifest.json','utf8')),result={};
 for(const model of ['dinov2','bioclip'])for(const [i,ref] of manifest.entries()){
  const base64=fs.readFileSync(work+'/test_data/image_refs/'+ref.id+'.bin').toString('base64');
  result[model+':'+ref.id]=await page.evaluate(async({base64,model})=>{
   const bytes=Uint8Array.from(atob(base64),c=>c.charCodeAt(0)),image=await createImageBitmap(new Blob([bytes]));
   const scale=Math.min(1,1600/Math.max(image.width,image.height)),canvas=document.createElement('canvas');canvas.width=Math.round(image.width*scale);canvas.height=Math.round(image.height*scale);
   const ctx=canvas.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,0,0,canvas.width,canvas.height);image.close();
   const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.9));return freshExtract(blob,model);
  },{base64,model});
  if((i+1)%7===0)console.log('FRESH',model,i+1,'/28');
 }
 fs.writeFileSync(work+'/fresh-test-vectors.json',JSON.stringify(result));await browser.close();console.log('FRESH inference complete');
})().catch(e=>{console.error(e);process.exit(1);});
