const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('ribby_app.html','utf8');
const ctx=vm.createContext({console,DOMException,serverMode:true,curUser:{id:'admin',role:'admin'}});
vm.runInContext(html.slice(html.indexOf('const publicImageFeatureJobs='),html.indexOf('function extractImageVector(')),ctx);
const pause=()=>new Promise(r=>setImmediate(r));
(async()=>{
 let active=0,max=0,calls=[];
 ctx.imageApi=async url=>{active++;max=Math.max(max,active);await pause();active--;const id=new URL(url,'http://app').searchParams.get('species_id');return {json:async()=>({references:[id]})};};
 const candidates=Array.from({length:20},(_,i)=>({id:String(i)}));
 const out=await ctx.loadImageReferenceSets(candidates,'model',16);assert.equal(max,4);assert.deepEqual(Array.from(out,x=>x.references[0]),candidates.map(x=>x.id));
 ctx.imageApi=async()=>{throw new Error('offline');};const fallback=await ctx.loadImageReferenceSets([{id:'1'}],'model',16);assert.equal(fallback[0].references.length,0);assert.equal(fallback[0].warnings[0],'offline');
 const abort=new AbortController();abort.abort();await assert.rejects(ctx.loadImageReferenceSets(candidates,'model',16,abort.signal),{name:'AbortError'});
 const pending=[];active=0;max=0;
 ctx.imageApi=async(url,opts)=>{calls.push(JSON.parse(opts.body));active++;max=Math.max(max,active);await new Promise(r=>pending.push(r));active--;};
 for(let i=0;i<10;i++)ctx.queuePublicImageFeatures({id:i.toString(16).padStart(32,'0'),license:'CC0'},'model','a'.repeat(64),[1]);
 ctx.queuePublicImageFeatures({id:'0'.repeat(32),license:'CC0'},'model','a'.repeat(64),[1]);assert.equal(calls.length,4);
 ctx.queuePublicImageFeatures({id:'f'.repeat(32),license:'private'},'model','a'.repeat(64),[1]);
 while(pending.length){pending.splice(0).forEach(r=>r());await pause();}assert.equal(calls.length,10);assert.equal(max,4);assert.ok(calls.every(x=>!('image_b64' in x)));
 // Logout discards queued writes, rather than publishing under another identity.
 for(let i=10;i<20;i++)ctx.queuePublicImageFeatures({id:i.toString(16).padStart(32,'0'),license:'CC0'},'model','a'.repeat(64),[1]);ctx.curUser={id:'other',role:'user'};
 while(pending.length){pending.splice(0).forEach(r=>r());await pause();}assert.equal(calls.length,14);
 // A failed optional upload can be retried on a later analysis.
 ctx.curUser={id:'admin',role:'admin'};ctx.imageApi=async()=>{throw new Error('offline');};const ref={id:'e'.repeat(32),license:'CC0'};
 ctx.queuePublicImageFeatures(ref,'model','a'.repeat(64),[1]);await pause();let retried=0;ctx.imageApi=async()=>{retried++;};ctx.queuePublicImageFeatures(ref,'model','a'.repeat(64),[1]);await pause();assert.equal(retried,1);
 console.log('Parallel reference loading, cancellation, bounded public cache, logout and retry checks passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
