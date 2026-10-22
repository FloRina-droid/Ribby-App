const {chromium}=require('playwright');
const base=process.env.RIBBY_TEST_URL||'http://127.0.0.1:7436';
const browserPath=process.env.RIBBY_BROWSER_PATH||'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const photoDir=process.env.RIBBY_TEST_PHOTOS||(require('node:fs').existsSync('accuracy_test_data/image_refs')?'accuracy_test_data':'accuracy_work/test_data');
async function launch(){return chromium.launch({executablePath:browserPath,headless:true,args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});}
async function login(page,email='field@ribby.test'){
 await page.goto(base,{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>serverMode===true);
 await page.getByRole('button',{name:'Einwilligen & Fortfahren',exact:true}).click();
 await page.locator('#li-email').fill(email);await page.locator('#li-pw').fill('SystemTestOnly2026!');
 await page.locator('#dsgvo-check').check();
 await page.locator('#login-btn').click();
 await page.locator('#page-home').waitFor({state:'visible'});
 await page.locator('#media-image').click();
 await page.locator('#image-scope').filter({hasText:'14 Arten'}).waitFor();
}
async function selectPhoto(page,file){
 const expected=(typeof file==='string'?require('node:path').basename(file):file.name).replace(/\.[^.]+$/,'')+'.jpg';
 await page.locator('#image-file').setInputFiles(file);
 await page.waitForFunction(name=>imageFile?.name===name&&!document.getElementById('image-analyze').disabled,expected);
}
async function analyze(page){
 await page.locator('#image-analyze').click();
 await page.waitForFunction(()=>imageRun===null&&document.getElementById('image-progress').textContent.length>0,null,{timeout:300000});
 return page.locator('#image-progress').innerText();
}
module.exports={base,photoDir,launch,login,selectPhoto,analyze};
