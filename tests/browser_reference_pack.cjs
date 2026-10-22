const fs=require('node:fs'),assert=require('node:assert/strict');
const {launch,login}=require('./browser_helpers.cjs');
(async()=>{
 const browser=await launch();
 try{
  const page=await browser.newPage();await login(page);
  const report=await page.evaluate(async()=>{
   const rows=[],photos=new Set(),errors=[],models=['bioclip-v1-fp16-22a18d2-v1','dinov2-small-q8-c2bb04a-cls-v1'];let vectors=0;
   for(const sp of imageLibrary){
    let count=0;
    for(const model of models){
     const data=await (await imageApi('/api/images/references?species_id='+encodeURIComponent(sp.id)+'&model='+encodeURIComponent(model))).json();
     count=data.references.length;
     for(const ref of data.references){
      if(ref.scientific_name!==sp.sci||!ref.creator||!['CC0 1.0','CC BY 1.0','CC BY 2.0','CC BY 2.5','CC BY 3.0','CC BY 4.0'].includes(ref.license)||!ref.license_url||!ref.source_url)errors.push('provenance '+ref.id);
      const features=ref.features?.vector,expected=model.startsWith('bioclip')?512:384;
      if(features?.length!==expected||features.some(v=>!Number.isFinite(v))||Math.abs(Math.sqrt(features.reduce((s,v)=>s+v*v,0))-1)>.01)errors.push('vector '+model+' '+ref.id);else vectors++;
      if(photos.has(ref.id))continue;photos.add(ref.id);
      try{const bitmap=await createImageBitmap(await referenceBlob(ref));if(!bitmap.width||!bitmap.height)throw new Error('empty');bitmap.close();}catch(e){errors.push('image '+ref.id+' '+e.message);}
     }
    }
    rows.push({species:sp.sci,photos:count,pass:count===64});
   }
   return {species:rows,photo_count:photos.size,vector_count:vectors,errors};
  });
  fs.writeFileSync('reports/system_reference_pack.json',JSON.stringify(report,null,2)+'\n');
  assert.equal(report.species.length,14);assert.equal(report.photo_count,896);assert.equal(report.vector_count,1792);assert.ok(report.species.every(r=>r.pass));assert.deepEqual(report.errors,[]);
  console.log('ALL PUBLIC REFERENCES OK: 14 species / 896 browser-decodable photos / 1792 valid model vectors');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
