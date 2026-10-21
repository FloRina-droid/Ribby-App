// Exercise the actual app resolver with changed bytes under the same photo ID.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto,createHash}=require('node:crypto');
const html=fs.readFileSync('ribby_app.html','utf8');
const ctx=vm.createContext({console,Blob,crypto:webcrypto,DOMException,document:{addEventListener(){},getElementById(){return {value:'bioclip',addEventListener(){}};}},window:{addEventListener(){}}});
ctx.serverMode=false;
vm.runInContext(html.slice(html.indexOf('// Photo mode:'),html.indexOf('// ── INIT ')),ctx);
const key=vm.runInContext('imageModelKey()',ctx),old=[1,...new Array(511).fill(0)],fresh=[0,1,...new Array(510).fill(0)];
const photo=new Blob(['new reference bytes']),hash=createHash('sha256').update('new reference bytes').digest('hex'),before='a'.repeat(64);
const ref=()=>({id:'same-id',license:'CC0 1.0',image_sha256:hash});
let cache,reads,extracts,writes,last;
function setup(value){cache=value;reads=extracts=writes=0;last=null;ctx.referenceBlob=async()=>{reads++;return photo;};ctx.extractImageVector=async()=>{extracts++;return fresh;};ctx.dbGet=async()=>cache;ctx.dbPut=async(store,value)=>{writes++;last=value;};}
const rows=[];
async function test(name,fn){await fn();rows.push({case:name,pass:true});}
(async()=>{
 await test('legacy_unbound_cache_recomputed',async()=>{setup({vector:old});const result=await ctx.imageReferenceVector(ref());assert.deepEqual(Array.from(result.vector),fresh);assert.equal(extracts,1);assert.equal(last.image_sha256,hash);assert.equal(last.model_key,key);});
 await test('matching_bound_cache_reused_without_inference',async()=>{setup({vector:old,model_key:key,image_sha256:hash});const result=await ctx.imageReferenceVector(ref());assert.deepEqual(Array.from(result.vector),old);assert.equal(reads+extracts+writes,0);});
 await test('same_id_changed_photo_recomputed',async()=>{setup({vector:old,model_key:key,image_sha256:before});await ctx.imageReferenceVector(ref());assert.equal(extracts,1);assert.equal(last.image_sha256,hash);});
 await test('unknown_hash_verified_before_cache_lookup',async()=>{setup({vector:old,model_key:key,image_sha256:hash});const input=ref();delete input.image_sha256;const result=await ctx.imageReferenceVector(input);assert.equal(result.image_sha256,hash);assert.equal(reads,1);assert.equal(extracts,0);});
 await test('matching_precomputed_features_need_no_download',async()=>{setup(null);const input=ref();input.features={model_key:key,image_sha256:hash,vector:old};await ctx.imageReferenceVector(input);assert.equal(reads+extracts+writes,0);});
 await test('mismatching_precomputed_features_are_rejected',async()=>{setup(null);const input=ref();input.features={model_key:key,image_sha256:before,vector:old};await ctx.imageReferenceVector(input);assert.equal(extracts,1);});
 await test('changed_download_is_never_cached_or_used',async()=>{setup(null);const input=ref();input.image_sha256=before;await assert.rejects(ctx.imageReferenceVector(input),/während der Analyse geändert/);assert.equal(extracts+writes,0);});
 await test('private_photo_change_invalidates_same_id',async()=>{setup({vector:old,model_key:key,image_sha256:before});const input={...ref(),license:'private',content_sha256:hash};await ctx.imageReferenceVector(input);assert.equal(extracts,1);assert.equal(last.image_sha256,hash);});
 await test('invalid_cached_vectors_and_wrong_model_recomputed',async()=>{for(const value of [{vector:old,model_key:'wrong',image_sha256:hash},{vector:[NaN,...old.slice(1)],model_key:key,image_sha256:hash},{vector:new Array(512).fill(0),model_key:key,image_sha256:hash}]){setup(value);await ctx.imageReferenceVector(ref());assert.equal(extracts,1);}});
 await test('cache_failures_remain_optional',async()=>{setup(null);ctx.dbGet=async()=>{throw new Error('offline cache');};ctx.dbPut=async()=>{throw new Error('quota');};const result=await ctx.imageReferenceVector(ref());assert.equal(result.image_sha256,hash);assert.equal(extracts,1);});
 await test('invalid_inference_is_not_saved',async()=>{setup(null);ctx.extractImageVector=async()=>new Array(512).fill(0);await assert.rejects(ctx.imageReferenceVector(ref()),/Ungültige Referenzmerkmale/);assert.equal(writes,0);});
 await test('cancelled_cache_read_cannot_start_inference',async()=>{setup(null);const controller=new AbortController();ctx.dbGet=async()=>{controller.abort();return null;};await assert.rejects(ctx.imageReferenceVector(ref(),controller.signal),{name:'AbortError'});assert.equal(reads+extracts+writes,0);});
 await test('user_change_cannot_save_late_inference',async()=>{setup(null);let active=true;ctx.extractImageVector=async()=>{active=false;return fresh;};await assert.rejects(ctx.imageReferenceVector(ref(),null,()=>{if(!active)throw new DOMException('Changed user','AbortError');}),{name:'AbortError'});assert.equal(writes,0);});
 fs.writeFileSync('reports/image_cache_unit_v6.json',JSON.stringify({pass:true,cases:rows,app_sha256:createHash('sha256').update(fs.readFileSync('ribby_app.html')).digest('hex')},null,2)+'\n');
 console.log('Reference cache tests',rows.length+'/'+rows.length,'passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
