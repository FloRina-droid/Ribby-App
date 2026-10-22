const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html=readFileSync('ribby_app.html','utf8');
const scripts=[...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)].filter(m=>!m[1].includes('text/plain'));
scripts.forEach(m=>new vm.Script(m[2]));
const js=html.slice(html.indexOf('// Photo mode:'),html.indexOf('// ── INIT '));
const context=vm.createContext({document:{addEventListener(){},getElementById(){return {addEventListener(){}};}},window:{addEventListener(){}},console});
vm.runInContext(js,context);
assert.equal(vm.runInContext('imageSimilarity([1,0],[1,0])',context),1);
assert.equal(vm.runInContext('imageSimilarity([1,0],[0,1])',context),0);
assert.equal(vm.runInContext('imageSimilarity([0,0],[1,0])',context),0);
assert.equal(vm.runInContext('imageSimilarity([1],[1,0])',context),0);
const result=vm.runInContext(`rankImageSpecies([
 {species_id:'A',references:[{similarity:.4},{similarity:.9}]},
 {species_id:'B',references:[{similarity:.8},{similarity:.8}]}
])`,context);
assert.equal(result[0].species_id,'B');
assert.equal(result[1].nRefs,2);
assert.equal(vm.runInContext(`rankImageSpecies([{species_id:'one',references:[{similarity:.4}]}])[0].similarity`,context),.4);
const selected=vm.runInContext(`selectDiverseImageReferences([
 {id:'1',canonical_id:'a',creator:'Alice',observation_id:1},
 {id:'2',canonical_id:'b',creator:'Alice',observation_id:1},
 {id:'3',canonical_id:'c',creator:'Alice',observation_id:2},
 {id:'4',canonical_id:'a',creator:'Mirror'},
 {id:'5',canonical_id:'d',creator:'Bob',observation_id:3}
],3)`,context);
assert.deepEqual(Array.from(selected,r=>r.id),['1','5','3']);
const centroid=vm.runInContext(`rankImageSpecies([{species_id:'balanced',queryVector:[1,0],references:[{similarity:1,vector:[1,0]},{similarity:0,vector:[0,1]}]}],'centroid')[0].similarity`,context);
assert.ok(Math.abs(centroid-Math.SQRT1_2)<1e-10);
context.document.getElementById=()=>({naturalWidth:200,naturalHeight:100,getBoundingClientRect(){return {width:400,height:400,left:10,top:20};},value:'bioclip'});
const point=vm.runInContext('imageCropPoint({clientX:110,clientY:170})',context);
assert.equal(point.x,50);assert.equal(point.y,25);
assert.equal(vm.runInContext('imageModelKey()',context),'bioclip-v1-fp16-22a18d2-v1');
const negativeRanking=vm.runInContext(`rankImageSpecies([
 {species_id:'A',scientific_name:'A',queryVector:[1,0],references:[{similarity:0,vector:[-.1,Math.sqrt(.99)]}]},
 {species_id:'B',scientific_name:'B',queryVector:[1,0],references:[{similarity:0,vector:[-.8,.6]}]}
],'centroid',{model_key:imageModelKey(),dimensions:2,species:['a','b'],method:'metric',center:[0,0],weights:[[1,0],[0,1]]})`,context);
assert.equal(negativeRanking[0].species_id,'A');
assert.ok(Math.abs(negativeRanking[0].similarity-.45)<1e-12);
assert.ok(Math.abs(negativeRanking[1].similarity-.1)<1e-12);
const unknownSpecies=vm.runInContext(`rankImageSpecies([{species_id:'new',scientific_name:'Unknown species',queryVector:[1,0],references:[{similarity:1,vector:[1,0]}]}],
 'centroid',{model_key:imageModelKey(),dimensions:2,species:['a','b'],method:'metric',center:[1,0],weights:[[0,1],[1,0]]})[0]`,context);
assert.equal(unknownSpecies.similarity,1);
assert.equal(vm.runInContext('rankImageSpecies([]).length',context),0);
console.log('JavaScript syntax and image ranking checks passed');
