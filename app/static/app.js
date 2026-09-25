const $=id=>document.getElementById(id);
const s={interactionId:null,recorder:null,chunks:[],sessionId:crypto.randomUUID?.()||String(Date.now()),validationConsent:false};

const UI={
  english:{meaning:"What this means",rights:"Your rights / protections",steps:"What to do next",route:"Escalation route",sources:"Sources used",draft:"Generate formal complaint",newCase:"Start another complaint",email:"Email",website:"Website",phone:"Phone",
    issues:{billing:"BILLING",metering:"METERING",disconnection:"DISCONNECTION",service_quality:"SERVICE QUALITY",tariff_band:"TARIFF / BAND",token_vending:"TOKEN / VENDING",connection:"CONNECTION",safety:"SAFETY",other:"OTHER"}},
  yoruba:{meaning:"Ohun tí èyí túmọ̀ sí",rights:"Ẹ̀tọ́ rẹ / ààbò rẹ",steps:"Ohun tí o yẹ kí o ṣe",route:"Ọ̀nà tí ẹ̀sùn yóò gbà lọ",sources:"Àwọn orísun tí a lò",draft:"Ṣẹ̀dá lẹ́tà ẹ̀sùn",newCase:"Bẹ̀rẹ̀ ẹ̀sùn míì",email:"Ímeèlì",website:"Ojú-òpó wẹ́ẹ̀bù",phone:"Tẹlifóònù",
    issues:{billing:"BILLING / OWÓ INA",metering:"MÍTA",disconnection:"GÍGÉ INÁ",service_quality:"DÍDÁRA ÌPÈSÈ INÁ",tariff_band:"TARIFF / BAND",token_vending:"TOKEN / VENDING",connection:"ÌSỌ̀PỌ̀ INÁ",safety:"ÀÀBÒ",other:"MÍÌ"}},
  hausa:{meaning:"Abin da wannan ke nufi",rights:"Hakkokinka / kariyarka",steps:"Abin da ya kamata ka yi",route:"Hanyar daukaka korafi",sources:"Majiyoyin da aka yi amfani da su",draft:"Kirkiri takardar korafi",newCase:"Fara wani korafi",email:"Imel",website:"Shafin yanar gizo",phone:"Waya",
    issues:{billing:"BILLING / KUDIN WUTA",metering:"MITA",disconnection:"KATSE WUTA",service_quality:"INGANCIN WUTA",tariff_band:"TARIFF / BAND",token_vending:"TOKEN / VENDING",connection:"HADA WUTA",safety:"TSARO",other:"WANI"}},
  igbo:{meaning:"Ihe nke a pụtara",rights:"Ikike / nchedo gị",steps:"Ihe ị ga-eme ọzọ",route:"Ụzọ ibuli mkpesa",sources:"Isi mmalite e jiri",draft:"Mepụta akwụkwọ mkpesa",newCase:"Malite mkpesa ọzọ",email:"Email",website:"Webụsaịtị",phone:"Ekwentị",
    issues:{billing:"BILLING / EGO ỌKỤ",metering:"MITA",disconnection:"MGBANYỤ ỌKỤ",service_quality:"OGOGO ỌRỤ ỌKỤ",tariff_band:"TARIFF / BAND",token_vending:"TOKEN / VENDING",connection:"NJIKỌ ỌKỤ",safety:"NCHEKWA",other:"ỌZỌ"}}
};

function detectTypedLanguage(text){
  const t=(text||"").toLowerCase();
  const scores={yoruba:0,hausa:0,igbo:0};
  scores.yoruba+=(t.match(/[ẹọṣàáèéìíòóùúń]/g)||[]).length*3;
  scores.igbo+=(t.match(/[ịụṅ]/g)||[]).length*3;
  scores.hausa+=(t.match(/[ƙɗɓ]/g)||[]).length*3;
  for(const p of ["kí ni","ki ni","ṣé wọ́n","se won","mo yẹ","mo ye","fi ẹ̀sùn","fi esun","owó ina","owo ina","wọ́n kò","won ko","báyìí","bayii"])if(t.includes(p))scores.yoruba+=5;
  for(const p of ["me zan","yaya zan","kudin wuta","kamfanin wuta","hakkina"])if(t.includes(p))scores.hausa+=5;
  for(const p of ["gịnị ka","gini ka","ego ọkụ","ego oku","mkpesa","ikike m"])if(t.includes(p))scores.igbo+=5;
  const ranked=Object.entries(scores).sort((a,b)=>b[1]-a[1]);
  return ranked[0][1]>=5&&ranked[0][1]>=ranked[1][1]+2?ranked[0][0]:null;
}

function syncTypedLanguage(){
  const detected=detectTypedLanguage($("message").value);
  if(detected&&$("language").value!==detected)$("language").value=detected;
  return detected||$("language").value;
}

function applyLocale(lang){
  const u=UI[lang]||UI.english;
  $("meaningTitle").textContent=u.meaning;
  $("rightsTitle").textContent=u.rights;
  $("stepsTitle").textContent=u.steps;
  $("routeTitle").textContent=u.route;
  $("sourcesTitle").textContent=u.sources;
  $("draftBtn").textContent=u.draft;
  $("newBtn").textContent=u.newCase;
}

const base=()=>({message:$("message").value.trim(),language:syncTypedLanguage(),state:$("state").value||null,disco:$("disco").value||null,session_id:s.sessionId});
const loading=x=>{$("loading").classList.toggle("hidden",!x);$("askBtn").disabled=x;$("recordBtn").disabled=x};
const esc=x=>String(x??"").replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const list=(id,a)=>$(id).innerHTML=(a||[]).map(x=>"<li>"+esc(x)+"</li>").join("");

function contact(label,value,type){
  if(!value)return"";
  let h=type==="email"?"mailto:"+value:type==="website"?value:type==="phone"?"tel:"+value.split(",")[0].replace(/\s/g,""):"";
  return h?'<a href="'+esc(h)+'" target="'+(type==="website"?"_blank":"_self")+'">'+esc(label)+": "+esc(value)+"</a>":"<span>"+esc(label)+": "+esc(value)+"</span>";
}

function render(d){
  s.interactionId=d.interaction_id;
  const lang=d.language||"english";
  $("language").value=lang;
  applyLocale(lang);
  const u=UI[lang]||UI.english;
  $("issueType").textContent=u.issues[d.issue_type]||(d.issue_type||"").replaceAll("_"," ");
  $("summary").textContent=d.summary;
  list("rights",d.rights);
  list("steps",d.next_steps);
  $("regulatorName").textContent=d.escalation.regulator_name;
  $("regulatorNote").textContent=d.escalation.note;
  $("regulatorContacts").innerHTML=
    contact(u.email,d.escalation.email,"email")+
    contact(u.website,d.escalation.website,"website")+
    contact(u.phone,d.escalation.phone,"phone")+
    (d.escalation.address?"<span>"+esc(d.escalation.address)+"</span>":"");
  $("sources").innerHTML=(d.sources||[]).map(x=>
    '<div class="source"><a href="'+esc(x.url)+'" target="_blank" rel="noopener">'+esc(x.title)+
    "</a><p>"+esc(x.authority)+" · "+esc(x.updated||"")+"</p><p>"+esc(x.excerpt)+"</p></div>"
  ).join("");
  $("disclaimer").textContent=d.disclaimer;
  $("result").classList.remove("hidden");
  $("draftPanel").classList.add("hidden");
  $("result").scrollIntoView({behavior:"smooth"});
}

$("message").addEventListener("input",()=>{syncTypedLanguage()});

$("askBtn").onclick=async()=>{
  const p=base();
  if(p.message.length<3)return alert("Please describe what happened.");
  loading(true);
  try{
    const r=await fetch("/api/v1/advice",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)});
    if(!r.ok)throw new Error((await r.json()).detail||"Request failed");
    render(await r.json());
  }catch(e){alert(e.message)}finally{loading(false)}
};

$("recordBtn").onclick=async()=>{
  if(s.recorder?.state==="recording"){s.recorder.stop();return}
  if(!navigator.mediaDevices?.getUserMedia)return alert("Voice recording is not supported in this browser.");
  try{
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});
    s.chunks=[];
    s.recorder=new MediaRecorder(stream);
    s.recorder.ondataavailable=e=>s.chunks.push(e.data);
    s.recorder.onstop=async()=>{
      stream.getTracks().forEach(t=>t.stop());
      $("recordBtn").classList.remove("recording");
      $("recordText").textContent="Record voice";
      $("recordIcon").textContent="●";
      await sendVoice(new Blob(s.chunks,{type:s.recorder.mimeType||"audio/webm"}));
    };
    s.recorder.start();
    $("recordBtn").classList.add("recording");
    $("recordText").textContent="Stop & analyse";
    $("recordIcon").textContent="■";
  }catch(e){alert("Microphone permission is needed.")}
};

async function sendVoice(blob){
  loading(true);
  try{
    const f=new FormData();
    s.validationConsent=$("validationConsent").checked;
    f.append("audio",blob,"complaint.webm");
    f.append("language",$("language").value);
    if($("state").value)f.append("state",$("state").value);
    if($("disco").value)f.append("disco",$("disco").value);
    f.append("session_id",s.sessionId);
    f.append("validation_consent",String(s.validationConsent));
    const r=await fetch("/api/v1/voice/advice",{method:"POST",body:f});
    if(!r.ok)throw new Error((await r.json()).detail||"Voice request failed");
    const d=await r.json();
    const p=d.summary.split("\n\n");
    if(p[0].startsWith("Transcript:")){$("message").value=p[0].replace("Transcript:","").trim();d.summary=p.slice(1).join("\n\n")}
    render(d);
  }catch(e){alert(e.message)}finally{loading(false)}
}

$("draftBtn").onclick=async()=>{
  const p={...base(),complainant_name:null,phone:null,email:null,address:null,desired_resolution:null};
  const r=await fetch("/api/v1/complaint",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)});
  if(!r.ok)return alert("Could not generate draft");
  const d=await r.json();
  $("draftSubject").textContent=d.subject;
  $("draftBody").textContent=d.body;
  list("draftChecklist",d.checklist);
  $("draftPanel").classList.remove("hidden");
};

$("copyDraft").onclick=async()=>{
  await navigator.clipboard.writeText($("draftSubject").textContent+"\n\n"+$("draftBody").textContent);
  $("copyDraft").textContent="Copied";
  setTimeout(()=>$("copyDraft").textContent="Copy",1200);
};

$("newBtn").onclick=()=>{
  $("result").classList.add("hidden");
  $("message").value="";
  window.scrollTo({top:0,behavior:"smooth"});
};

document.querySelectorAll("[data-helpful]").forEach(b=>b.onclick=async()=>{
  if(!s.interactionId)return;
  const r=await fetch("/api/v1/feedback",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    interaction_id:s.interactionId,
    helpful:b.dataset.helpful==="true",
    understood_language:true,
    resolved_or_actionable:b.dataset.helpful==="true",
    consent_to_validation:s.validationConsent
  })});
  $("feedbackStatus").textContent=r.ok?"Thank you — validation response recorded.":"Could not record feedback.";
});

async function refreshReadiness(){
  try{
    const r=await fetch("/api/v1/challenge/readiness");
    if(!r.ok)throw new Error("readiness unavailable");
    const d=await r.json();
    const el=$("modelStatus");
    if(d.ready){
      el.textContent="N-ATLaS live";
      el.title="Official N-ATLaS LLM and ASR are connected.";
    }else{
      el.textContent="N-ATLaS activation pending";
      el.title="The public application is live, but official N-ATLaS inference is not fully connected yet.";
    }
  }catch(_){$("modelStatus").textContent="Model status unavailable"}
}
refreshReadiness();

if("serviceWorker" in navigator){window.addEventListener("load",()=>navigator.serviceWorker.register("/static/service-worker.js").catch(()=>{}));}
