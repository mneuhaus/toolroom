// Native Onshape example builder. Session bridge only; no API-key fallback.
import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
export const root = new URL('../../', import.meta.url);
const stateFile = new URL('var/joints/state/onshape.json', root);
export const sha = b => crypto.createHash('sha256').update(b).digest('hex');
export async function save(path, data) {
  const url = new URL(path, root); await fs.mkdir(new URL('./', url), {recursive:true});
  await fs.writeFile(url, JSON.stringify(data, null, 2)+'\n');
}
export async function readState(){ return JSON.parse(await fs.readFile(stateFile,'utf8')); }
export const ps = (s,e,kind='partstudios') => `/api/v9/${kind}/d/${s.did}/w/${s.wid}/e/${e}`;
let lastCall = 0;
export async function request(path, label, data, method=data?'POST':'GET') {
  assert(path.startsWith('/api/') || path.startsWith('/_bridge/'));
  const delay = Math.max(0, 450 - (Date.now()-lastCall));
  if(delay) await new Promise(r=>setTimeout(r,delay));
  const pending={path,method,label,body_sha256:data?sha(JSON.stringify(data)):null,started:new Date().toISOString()};
  const mutation=method!=='GET' && !path.endsWith('/featurescript');
  if(mutation){
    const previous=await fs.readFile(new URL('var/joints/state/pending.json',root),'utf8').then(JSON.parse).catch(e=>{if(e.code==='ENOENT')return null;throw e;});
    assert(!previous || ['returned-success','returned-rejection','reconciled'].includes(previous.outcome),'Previous write has an unknown outcome; reconcile its destination before continuing');
    await save('var/joints/state/pending.json',pending);
  }
  lastCall=Date.now();
  const response=await fetch('http://127.0.0.1:8317'+path,{method,redirect:'error',signal:AbortSignal.timeout(180000),headers:{'Content-Type':'application/json'},...(data?{body:JSON.stringify(data)}:{})});
  const raw=await response.text();
  const log={...pending,status:response.status,remaining:response.headers.get('x-rate-limit-remaining'),retry_after:response.headers.get('retry-after'),completed:new Date().toISOString()};
  await fs.mkdir(new URL('var/joints/logs/',root),{recursive:true});
  await fs.appendFile(new URL('var/joints/logs/requests.jsonl',root),JSON.stringify(log)+'\n');
  console.log(label,response.status,'remaining',log.remaining);
  if(!response.ok){if(mutation)await save('var/joints/state/pending.json',{...log,outcome:response.status<500?'returned-rejection':'unknown-server-error'});throw Error(raw.slice(0,2000));}
  const result=raw?JSON.parse(raw):null;
  if(label)await save(`var/joints/cache/${label}.json`,result);
  if(mutation)await save('var/joints/state/pending.json',{...log,outcome:'returned-success',response_cache:`var/joints/cache/${label}.json`});
  return result;
}

const titles=['Straight dovetail','Tapered dovetail','Scarfed dovetail','Curved tapered dovetail','Conical curved dovetail','Echo-Lock','Drop-Lock','Keyed scarf'];
async function main() {
  const [command, selected] = process.argv.slice(2);
  if(!['create','source','build','inspect','render','export'].includes(command)) {
    console.log('node examples/printed-joints/onshape.mjs create|source|build|inspect|render|export [joint-number]');return;
  }
  await fs.mkdir(new URL('var/joints/state/',root),{recursive:true});
  const lockFile=new URL('var/joints/state/writer.lock',root);
  const lock=await fs.open(lockFile,'wx');await lock.writeFile(String(process.pid));
  try {
    if(command==='create'){
      try {await fs.access(stateFile);throw Error('Document state already exists; do not create a duplicate');}
      catch(e){if(e.code!=='ENOENT')throw e;}
      const doc=await request('/api/documents','create-document',{name:'CAD Skills — Printed Joints Lab 01',isPublic:true,description:'Independent native teaching specimens after three NeedItMakeIt videos. Fits uncalibrated; no physical strength claim.'});
      const s={did:doc.id,wid:doc.defaultWorkspace.id,isPublic:doc.isPublic,studios:{}};
      await save('var/joints/state/onshape.json',s);
      const elems=await request(`/api/documents/d/${s.did}/w/${s.wid}/elements`,'initial-elements');
      s.initialElements=elems.map(e=>({id:e.id,type:e.elementType,name:e.name}));
      await save('var/joints/state/onshape.json',s);return;
    }
    const s=await readState();
    if(command==='source'){
      if(!s.fs){const e=await request(`/api/v9/featurestudios/d/${s.did}/w/${s.wid}`,'create-feature-studio',{name:'Joints — native parameters and construction'});s.fs=e.id;await save('var/joints/state/onshape.json',s);}
      const source=await fs.readFile(new URL('examples/printed-joints/joints.fs',root),'utf8');
      await request(ps(s,s.fs,'featurestudios'),'upload-source',{contents:source});
      const specs=await request(ps(s,s.fs,'featurestudios')+'/featurespecs','source-specs');
      const spec=specs.featureSpecs?.find(f=>f.featureType==='printedJoint');assert(spec,'Source compilation failed; inspect source-specs');
      s.sourceMicroversion=spec.sourceMicroversionId;s.sourceSha256=sha(source);
      await save('var/joints/state/onshape.json',s);return;
    }
    const kinds=selected?[Number(selected)]:[1,2,3,4,5,6,7,8];assert(kinds.every(k=>k>=1&&k<=8));
    for(const k of kinds){
      for(const separate of [false,true]){
        const key=`J0${k}-${separate?'separate':'assembled'}`;
        if(command==='build'){
          assert(s.fs&&s.sourceMicroversion,'Upload source first');
          s.studios[key]??={kind:k,separate};const tab=s.studios[key];
          if(!tab.id){const e=await request(`/api/partstudios/d/${s.did}/w/${s.wid}`,`${key}-create`,{name:`J0${k} ${titles[k-1]} — ${separate?'Separate parts':'Assembled'}`});tab.id=e.id;await save('var/joints/state/onshape.json',s);}
          const feature={btType:'BTMFeature-134',featureType:'printedJoint',name:`J0${k} ${titles[k-1]}`,namespace:`e${s.fs}::m${s.sourceMicroversion}`,parameters:[
            {btType:'BTMParameterQuantity-147',parameterId:'kind',expression:String(k),isInteger:true},
            {btType:'BTMParameterQuantity-147',parameterId:'gap',expression:'0.10 mm'},
            {btType:'BTMParameterBoolean-144',parameterId:'separate',value:separate}],...(tab.feature?{featureId:tab.feature}:{})};
          const result=await request(ps(s,tab.id)+'/features'+(tab.feature?'/featureid/'+encodeURIComponent(tab.feature):''),`${key}-build`,{btType:'BTFeatureDefinitionCall-1406',feature});
          tab.feature=result.feature?.featureId||tab.feature;tab.status=result.featureState;tab.buildMicroversion=result.sourceMicroversion;tab.sourceMicroversion=s.sourceMicroversion;tab.sourceSha256=s.sourceSha256;
          await save('var/joints/state/onshape.json',s);assert.equal(result.featureState?.featureStatus,'OK',JSON.stringify(result.featureState));
        }else{
          const tab=s.studios[key];assert(tab?.id,`Build ${key} first`);
          if(command==='inspect'){
            const parts=await request(ps(s,tab.id,'parts'),`${key}-parts`);
            assert.equal(parts.length,k===8?4:2);tab.parts=parts.map(p=>({partId:p.partId,name:p.name,microversionId:p.microversionId}));
            const mass=await request(ps(s,tab.id)+'/massproperties?massAsGroup=false',`${key}-mass`);tab.massResponseSha256=sha(JSON.stringify(mass));
            await save('var/joints/state/onshape.json',s);
          }
          if(command==='render'){
            const image=await request(ps(s,tab.id)+'/shadedviews?viewMatrix=isometric&outputWidth=1100&outputHeight=650&pixelSize=0&edges=true',`${key}-render`);
            const path=new URL(`site/assets/joints-${key}.png`,root);await fs.writeFile(path,Buffer.from(image.images[0],'base64'));
          }
          if(command==='export'&&!separate){
            const job=await request(ps(s,tab.id)+'/translations',`${key}-step-job`,{formatName:'STEP',storeInDocument:false});let status=job;const deadline=Date.now()+180000;
            while(!['DONE','FAILED'].includes(status.requestState)){assert(Date.now()<deadline,'Export still pending; reconcile saved translation ID before retrying');await new Promise(r=>setTimeout(r,2000));status=await request('/api/translations/'+job.id,`${key}-step-status`);}
            assert.equal(status.requestState,'DONE');
            const response=await fetch('http://127.0.0.1:8317/api/documents/d/'+s.did+'/externaldata/'+status.resultExternalDataIds[0],{redirect:'error',signal:AbortSignal.timeout(180000)});assert(response.ok);
            const bytes=Buffer.from(await response.arrayBuffer());assert(bytes.subarray(0,100).toString().includes('ISO-10303-21'));
            await fs.mkdir(new URL('examples/printed-joints/exports/',root),{recursive:true});
            await fs.writeFile(new URL(`examples/printed-joints/exports/${key}.step`,root),bytes);tab.stepSha256=sha(bytes);
            await save('var/joints/state/onshape.json',s);
          }
        }
      }
    }
  }finally{await lock.close();await fs.unlink(lockFile);}
}
if(process.argv[1]&&new URL(process.argv[1],'file:').href===import.meta.url)await main();
