const $=(id)=>document.getElementById(id);
let history=[];
let lastAssistantText="";

const quickstartSamples={
  python:`import os\nfrom ednai import EDNAi

ai = EDNAi(
    base_url="https://ednai-6znf.onrender.com",
    api_key=os.environ["EDNAI_API_KEY"]
)

result = ai.generate(
    "Ka bayyana API da Hausa.",
    temperature=0.2
)

print(result.text)`,
  typescript:`import { EDNAi } from "@ednai/sdk";

const ai = new EDNAi({
  baseUrl: "https://ednai-6znf.onrender.com",
  apiKey: process.env.EDNAI_API_KEY
});

const result = await ai.generate(
  "Ka bayyana API da Hausa.",
  { temperature: 0.2 }
);

console.log(result.text);`,
  curl:`curl -X POST \
  https://ednai-6znf.onrender.com/v1/chat/completions \
  -H "Authorization: Bearer $EDNAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "NCAIR1/N-ATLaS",
    "messages": [
      {
        "role": "user",
        "content": "Ka bayyana API da Hausa."
      }
    ],
    "temperature": 0.2
  }'`
};

const promptTemplates={
  english:{
    system:"You are a helpful Nigerian AI assistant. Explain clearly, use practical local context when useful, and avoid unnecessary jargon.",
    prompt:"Explain how prepaid electricity meters work to a first-time Nigerian electricity customer.",
    json:false,maxTokens:300
  },
  yoruba:{
    system:"Dáhùn ní Yorùbá tó rọrùn. Jẹ́ kó ṣe kedere, kúkúrú, kí o sì lo àpẹẹrẹ tó wúlò.",
    prompt:"Ṣàlàyé ohun tí API jẹ́ fún developer tuntun.",
    json:false,maxTokens:300
  },
  hausa:{
    system:"Ka amsa da Hausa mai sauƙi kuma a taƙaice. Ka yi amfani da misali idan ya taimaka.",
    prompt:"Ka bayyana yadda API yake aiki ga sabon developer.",
    json:false,maxTokens:300
  },
  extract:{
    system:"Return valid JSON only. Do not add markdown or explanatory text.",
    prompt:"Extract intent, language and urgency from this message: 'My prepaid meter stopped working yesterday and I need help quickly.'",
    json:true,maxTokens:220
  }
};

let toastTimer=null;
function showToast(message,type){
  const toast=$("toast");
  if(!toast)return;
  if(type==="error" && (
    message==="Developer session is invalid or expired." ||
    message==="Developer login required."
  )){
    message="Your developer session expired. Opening sign in…";
    setTimeout(()=>clearExpiredSessionAndOpenLogin(""),500);
  }
  toast.textContent=message;
  toast.className="toast show "+(type||"");
  clearTimeout(toastTimer);
  const duration=type==="error"?6500:2800;
  toastTimer=setTimeout(()=>{toast.className="toast";},duration);
}

function formatQuotaResetTime(value){
  if(!value)return "";
  const date=new Date(value);
  if(Number.isNaN(date.getTime()))return "";
  try{
    return new Intl.DateTimeFormat(undefined,{
      weekday:"short",
      month:"short",
      day:"numeric",
      hour:"numeric",
      minute:"2-digit",
      timeZoneName:"short"
    }).format(date);
  }catch(_){
    return date.toLocaleString();
  }
}

async function copyText(text){
  try{
    await navigator.clipboard.writeText(text);
  }catch(_){
    const area=document.createElement("textarea");
    area.value=text;
    area.style.position="fixed";
    area.style.opacity="0";
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
}

function setButtonLoading(button,loading){
  if(!button)return;
  if(loading){
    if(!button.dataset.loadingLabel)button.dataset.loadingLabel=button.textContent;
    button.classList.add("button-loading");
    button.disabled=true;
  }else{
    button.classList.remove("button-loading");
    button.disabled=false;
    if(button.dataset.loadingLabel){
      button.textContent=button.dataset.loadingLabel;
      delete button.dataset.loadingLabel;
    }
  }
}

function addPendingMessage(){
  removePendingMessage();
  const div=document.createElement("div");
  div.id="pendingMessage";
  div.className="message assistant pending";
  div.innerHTML='<span>N-ATLaS</span><p>Generating response…</p><div class="typing-dots"><i></i><i></i><i></i></div>';
  $("messages").appendChild(div);
  $("messages").scrollTop=$("messages").scrollHeight;
}
function removePendingMessage(){
  const pending=$("pendingMessage");
  if(pending)pending.remove();
}

let onboarding={stack:false,run:false,ship:false};
try{
  onboarding=Object.assign(onboarding,JSON.parse(localStorage.getItem("ednai-onboarding")||"{}"));
}catch(_){}
function renderOnboarding(){
  const map={stack:"stepStack",run:"stepRun",ship:"stepShip"};
  Object.entries(map).forEach(([key,id])=>{
    const node=$(id);
    if(node)node.classList.toggle("done",Boolean(onboarding[key]));
  });
  const complete=Object.values(onboarding).filter(Boolean).length;
  if($("onboardingProgress")){
    $("onboardingProgress").textContent=complete+" / 3 complete";
    $("onboardingProgress").classList.toggle("complete",complete===3);
  }
}
function completeOnboarding(step){
  onboarding[step]=true;
  try{localStorage.setItem("ednai-onboarding",JSON.stringify(onboarding));}catch(_){}
  if($("asrLanguage")){
  $("asrLanguage").addEventListener("change",updateSelectedAsrModel);
  updateSelectedAsrModel();
}

if($("copyAsrPythonBtn"))$("copyAsrPythonBtn").addEventListener("click",async()=>{
  await copyText($("asrPythonCode").textContent);
  showToast("Python ASR example copied.","success");
});

if($("copyAsrCurlBtn"))$("copyAsrCurlBtn").addEventListener("click",async()=>{
  await copyText($("asrCurlCode").textContent);
  showToast("cURL ASR example copied.","success");
});

renderOnboarding();
}

async function readApiResponse(response){
  const text=await response.text();
  let body=null;
  if(text){
    try{body=JSON.parse(text);}
    catch(_){body=null;}
  }
  if(!response.ok){
    const detail=body&&body.detail;
    const quotaResetsAt=response.headers.get("x-zerogpu-resets-at")||(detail&&detail.resets_at)||null;
    let message=
      (typeof detail==="string"&&detail)||
      (detail&&typeof detail==="object"&&detail.message)||
      (body&&body.error)||
      text.trim()||
      ("Request failed ("+response.status+")");

    if(response.status===429 && quotaResetsAt){
      const resetLabel=formatQuotaResetTime(quotaResetsAt);
      if(resetLabel && !message.includes("Next reset:")){
        const generic="Please try again after the free quota resets.";
        if(message.endsWith(generic))message=message.slice(0,-generic.length).trim();
        message+=" Next reset: "+resetLabel+".";
      }
    }

    const error=new Error(message);
    error.status=response.status;
    error.retryAfter=response.headers.get("retry-after")||(detail&&detail.retry_after_seconds?String(detail.retry_after_seconds):null);
    error.quotaResetsAt=quotaResetsAt;
    error.code=detail&&typeof detail==="object"?detail.error:null;
    throw error;
  }
  if(body!==null)return body;
  throw new Error("Server returned an unreadable response.");
}

function addMessage(role,text){
  const div=document.createElement("div");
  div.className="message "+role;
  const who=document.createElement("span");
  who.textContent=role==="user"?"You":"N-ATLaS";
  const p=document.createElement("p");
  p.textContent=text;
  div.append(who,p);
  $("messages").appendChild(div);
  if(role==="assistant" && !String(text).startsWith("Runtime error:")){
    lastAssistantText=String(text);
  }
  $("messages").scrollTop=$("messages").scrollHeight;
}
async function clearExpiredSessionAndOpenLogin(prompt){
  try{
    if(prompt)sessionStorage.setItem("ednai-pending-prompt",prompt);
    sessionStorage.setItem("ednai-return-after-login","/#playground");
  }catch(_){}
  try{
    await fetch("/api/developer/logout",{method:"POST",credentials:"same-origin"});
  }catch(_){}
  if(typeof renderHeaderProfile==="function")renderHeaderProfile(null);
  window.location.href="/developer?return="+encodeURIComponent("/#playground");
}

async function health(){
  const heroStatus=$("heroRuntimeStatus");
  try{
    const r=await fetch("/health",{cache:"no-store"});
    const h=await r.json();
    const connected=Boolean(h.direct_natlas_integration);
    $("runtimeStatus").textContent=connected?"N-ATLaS connected":"Runtime not connected";
    $("runtimeStatus").className="status "+(connected?"good":"warn");
    if(heroStatus){
      heroStatus.className="runtime-inline nav-runtime "+(connected?"good":"warn");
      heroStatus.querySelector("span").textContent=connected?"N-ATLaS runtime connected":"Runtime not connected";
    }
  }catch{
    $("runtimeStatus").textContent="Offline";
    $("runtimeStatus").className="status warn";
    if(heroStatus){
      heroStatus.className="runtime-inline nav-runtime warn";
      heroStatus.querySelector("span").textContent="Gateway offline";
    }
  }
}
async function runPrompt(){
  const prompt=$("prompt").value.trim();
  if(!prompt){
    showToast("Add a prompt first.","error");
    $("prompt").focus();
    return;
  }
  addMessage("user",prompt);
  history.push({role:"user",content:prompt});
  $("prompt").value="";
  $("meta").textContent="Allocating N-ATLaS runtime…";
  setButtonLoading($("sendBtn"),true);
  setButtonLoading($("runBtn"),true);
  addPendingMessage();

  const messages=[];
  const system=$("system").value.trim();
  if(system)messages.push({role:"system",content:system});
  messages.push(...history);

  try{
    const started=performance.now();
    const r=await fetch("/v1/generate",{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({
        model:"NCAIR1/N-ATLaS",
        messages,
        temperature:Number($("temperature").value),
        max_tokens:Number($("maxTokens").value),
        json_mode:$("jsonMode").checked
      })
    });
    const body=await readApiResponse(r);
    removePendingMessage();
    addMessage("assistant",body.text);
    history.push({role:"assistant",content:body.text});
    const latency=body.latency_ms??Math.round(performance.now()-started);
    $("meta").textContent=`${body.provider||"EDNAi"} · ${latency} ms · ${body.model}`;
    completeOnboarding("run");
    showToast("N-ATLaS response completed.","success");
  }catch(e){
    removePendingMessage();

    if(e.status===401){
      $("meta").textContent="Sign in required";
      showToast("Your developer session expired. Opening sign in…","error");
      setTimeout(()=>clearExpiredSessionAndOpenLogin(prompt),500);
      return;
    }

    const resetLabel=e.status===429?formatQuotaResetTime(e.quotaResetsAt):"";
    addMessage("assistant",`Runtime error: ${e.message}`);
    $("meta").textContent=resetLabel
      ? `ZeroGPU quota exhausted · resets ${resetLabel}`
      : (e.status===429?"Free ZeroGPU quota temporarily exhausted":"Request failed");
    showToast(e.message,"error");
  }finally{
    setButtonLoading($("sendBtn"),false);
    setButtonLoading($("runBtn"),false);
  }
}
$("sendBtn").addEventListener("click",runPrompt);
$("runBtn").addEventListener("click",runPrompt);
$("prompt").addEventListener("keydown",(e)=>{if((e.ctrlKey||e.metaKey)&&e.key==="Enter")runPrompt();});
$("clearBtn").addEventListener("click",()=>{
  history=[];
  $("messages").innerHTML='<div class="message assistant"><span>EDNAi</span><p>Conversation cleared.</p></div>';
  $("meta").textContent="Ready";
});
health();


/* ---------- EDNAi Developer Console workspaces ---------- */
const smokeSuite=[
  {id:"en-capital",prompt:"What is the capital of Nigeria? Answer in one short sentence.",language:"english",must_include:["Abuja"]},
  {id:"en-json",prompt:"Return a JSON object with keys country and capital for Nigeria.",language:"english",json_mode:true,must_include:["Nigeria","Abuja"]},
  {id:"yo-api",prompt:"Ṣàlàyé ohun tí API túmọ̀ sí fún developer tuntun.",language:"yoruba"},
  {id:"ha-api",prompt:"Ka bayyana API ga sabon developer da Hausa.",language:"hausa"},
  {id:"ig-api",prompt:"Kọwaa API nye onye developer ọhụrụ n'Igbo.",language:"igbo"}
];

const datasetExample=[
  {messages:[{role:"user",content:"What is an API?"},{role:"assistant",content:"An API is an interface that lets software systems communicate."}]},
  {instruction:"Ṣàlàyé machine learning ní ọ̀rọ̀ díẹ̀.",input:"",output:"Machine learning jẹ́ ọ̀nà tí kọ̀ǹpútà fi ń kọ́ láti inú data."},
  {messages:[{role:"system",content:"Ka amsa a Hausa mai sauƙi."},{role:"user",content:"Menene API?"},{role:"assistant",content:"API hanya ce da software biyu ke amfani da ita wajen sadarwa da juna."}]}
];

let normalizedDataset="";

function consolePanel(name){
  const isOverview=name==="overview";
  const home=$("homeOverview");
  if(home)home.classList.toggle("hidden",!isOverview);
  const tabs=document.querySelector(".console-tabs");
  if(tabs)tabs.classList.toggle("workspace-nav-visible",!isOverview);
  document.querySelectorAll(".console-panel").forEach(function(panel){
    panel.classList.toggle("active",!isOverview && panel.id==="panel-"+name);
  });
  document.querySelectorAll(".console-tab").forEach(function(tab){
    tab.classList.toggle("active",tab.dataset.panel===name);
  });
  document.querySelectorAll("[data-console-target]").forEach(function(control){
    control.classList.toggle("active",control.dataset.consoleTarget===name);
  });
  window.history.replaceState(null,"","#"+name);
  if(name==="runtime")refreshRuntimeWorkspace();
  if(name==="profile")refreshProfileWorkspace();
  if(isOverview)window.scrollTo({top:0,behavior:"smooth"});
}

document.querySelectorAll(".console-tab").forEach(function(tab){
  tab.addEventListener("click",function(){consolePanel(tab.dataset.panel);});
});

document.querySelectorAll("[data-console-target]").forEach(function(control){
  control.addEventListener("click",function(event){
    if(control.tagName==="A")return;
    event.preventDefault();
    const target=control.dataset.consoleTarget;
    consolePanel(target);
    if(target!=="overview"){
      const panel=$("panel-"+target);
      if(panel)panel.scrollIntoView({behavior:"smooth",block:"start"});
    }
  });
});

function downloadText(filename,content,type){
  const blob=new Blob([content],{type:type||"text/plain"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;a.download=filename;a.click();
  setTimeout(function(){URL.revokeObjectURL(url);},400);
}

function parseJSONL(text){
  return text.split(/\r?\n/).filter(function(line){return line.trim();}).map(function(line,index){
    try{return JSON.parse(line);}
    catch(error){throw new Error("Line "+(index+1)+": "+error.message);}
  });
}

function workspaceSave(){
  try{
    localStorage.setItem("ednai-console-workspace",JSON.stringify({
      benchmark:$("benchmarkEditor")?$("benchmarkEditor").value:"",
      dataset:$("datasetEditor")?$("datasetEditor").value:""
    }));
  }catch(_){}
}

function workspaceRestore(){
  let saved={};
  try{saved=JSON.parse(localStorage.getItem("ednai-console-workspace")||"{}");}catch(_){}
  if($("benchmarkEditor"))$("benchmarkEditor").value=saved.benchmark||smokeSuite.map(function(x){return JSON.stringify(x);}).join("\n");
  if($("datasetEditor"))$("datasetEditor").value=saved.dataset||datasetExample.map(function(x){return JSON.stringify(x);}).join("\n");
}

if($("benchmarkEditor"))$("benchmarkEditor").addEventListener("input",workspaceSave);
if($("datasetEditor"))$("datasetEditor").addEventListener("input",workspaceSave);

if($("loadSmokeBtn"))$("loadSmokeBtn").addEventListener("click",function(){
  $("benchmarkEditor").value=smokeSuite.map(function(x){return JSON.stringify(x);}).join("\n");
  workspaceSave();
});

if($("downloadBenchmarkBtn"))$("downloadBenchmarkBtn").addEventListener("click",function(){
  downloadText("ednai-benchmark.jsonl",$("benchmarkEditor").value+"\n","application/x-ndjson");
});

if($("runEvalBtn"))$("runEvalBtn").addEventListener("click",async function(){
  let cases;
  try{cases=parseJSONL($("benchmarkEditor").value);}
  catch(error){showToast(error.message,"error");return;}
  $("runEvalBtn").disabled=true;
  $("evalStatus").textContent="Running";
  try{
    const response=await fetch("/api/studio/evaluate",{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({cases:cases,temperature:0,max_tokens:512})
    });
    const report=await readApiResponse(response);
    if(!response.ok)throw new Error(report.detail||"Evaluation failed");
    $("evalStatus").textContent="Complete";
    $("evalPassRate").textContent=Math.round(report.pass_rate*100)+"%";
    $("evalPassed").textContent=report.passed+"/"+report.total;
    $("evalLatency").textContent=report.median_latency_ms==null?"—":report.median_latency_ms+" ms";
    $("evalTotal").textContent=report.total;
    $("evalRows").innerHTML=report.results.map(function(row){
      const checks=Object.entries(row.checks||{}).map(function(pair){
        return '<span class="check-pill '+(pair[1]?"ok":"bad")+'">'+pair[0]+'</span>';
      }).join(" ");
      return "<tr><td><strong>"+row.id+"</strong>"+(row.error?'<small class="error-text">'+row.error+"</small>":"")+
        '</td><td><span class="result-pill '+(row.passed?"ok":"bad")+'">'+(row.passed?"PASS":"FAIL")+
        "</span></td><td>"+(checks||"—")+"</td><td>"+(row.latency_ms==null?"—":row.latency_ms+" ms")+"</td></tr>";
    }).join("");
    $("evalRaw").textContent=JSON.stringify(report,null,2);
  }catch(error){
    $("evalStatus").textContent="Failed";
    showToast(error.message,"error");
  }finally{
    $("runEvalBtn").disabled=false;
  }
});

if($("loadDatasetExampleBtn"))$("loadDatasetExampleBtn").addEventListener("click",function(){
  $("datasetEditor").value=datasetExample.map(function(x){return JSON.stringify(x);}).join("\n");
  workspaceSave();
});

if($("uploadDatasetBtn"))$("uploadDatasetBtn").addEventListener("click",function(){$("datasetFile").click();});
if($("datasetFile"))$("datasetFile").addEventListener("change",async function(){
  const file=$("datasetFile").files[0];
  if(!file)return;
  $("datasetEditor").value=await file.text();
  workspaceSave();
});

if($("inspectDatasetBtn"))$("inspectDatasetBtn").addEventListener("click",async function(){
  $("inspectDatasetBtn").disabled=true;
  $("datasetStatus").textContent="Inspecting";
  try{
    const response=await fetch("/api/studio/dataset/inspect",{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({jsonl:$("datasetEditor").value,preview_rows:3})
    });
    const report=await readApiResponse(response);
    if(!response.ok)throw new Error(report.detail||"Dataset inspection failed");
    $("datasetStatus").textContent=report.valid?"Valid":"Needs work";
    $("datasetValid").textContent=report.valid_examples;
    $("datasetInvalid").textContent=report.invalid_examples;
    $("datasetMessages").textContent=report.stats.message_count;
    $("datasetTokens").textContent=Number(report.stats.rough_token_estimate).toLocaleString();
    $("datasetPreview").textContent=JSON.stringify(report.preview,null,2);
    normalizedDataset=report.normalized_jsonl||"";
    $("downloadNormalizedBtn").disabled=!normalizedDataset;
    if(report.errors&&report.errors.length){
      $("datasetErrors").classList.remove("hidden");
      $("datasetErrors").innerHTML="<strong>Validation issues</strong>"+report.errors.map(function(item){
        return "<div>Line "+item.line+": "+item.error+"</div>";
      }).join("");
    }else{
      $("datasetErrors").classList.add("hidden");
      $("datasetErrors").innerHTML="";
    }
  }catch(error){
    $("datasetStatus").textContent="Failed";
    showToast(error.message,"error");
  }finally{
    $("inspectDatasetBtn").disabled=false;
  }
});

if($("downloadNormalizedBtn"))$("downloadNormalizedBtn").addEventListener("click",function(){
  if(normalizedDataset)downloadText("prepared.jsonl",normalizedDataset,"application/x-ndjson");
});

function fineTuneRequest(){
  return {
    examples:Number($("ftExamples").value),
    epochs:Number($("ftEpochs").value),
    learning_rate:Number($("ftLearningRate").value),
    batch_size:Number($("ftBatch").value),
    gradient_accumulation:Number($("ftGradAccum").value),
    max_length:Number($("ftMaxLength").value),
    lora_r:Number($("ftLoraR").value),
    lora_alpha:Number($("ftLoraAlpha").value),
    output_dir:$("ftOutput").value
  };
}

if($("planFineTuneBtn"))$("planFineTuneBtn").addEventListener("click",async function(){
  $("planFineTuneBtn").disabled=true;
  try{
    const response=await fetch("/api/studio/fine-tune/plan",{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify(fineTuneRequest())
    });
    const plan=await readApiResponse(response);
    if(!response.ok)throw new Error(plan.detail||"Could not generate plan");
    $("ftMethod").textContent=plan.method;
    $("ftEffectiveBatch").textContent=plan.effective_batch_size;
    $("ftSteps").textContent=plan.estimated_optimizer_steps;
    $("ftCommand").textContent=plan.command;
    $("ftWarnings").innerHTML=plan.warnings.map(function(warning){
      return "<div><strong>!</strong><span>"+warning+"</span></div>";
    }).join("");
  }catch(error){showToast(error.message,"error");}
  finally{$("planFineTuneBtn").disabled=false;}
});

if($("copyTrainCommandBtn"))$("copyTrainCommandBtn").addEventListener("click",async function(){
  await navigator.clipboard.writeText($("ftCommand").textContent);
  $("copyTrainCommandBtn").textContent="Copied";
  setTimeout(function(){$("copyTrainCommandBtn").textContent="Copy";},1000);
});

async function refreshRuntimeWorkspace(){
  if(!$("runtimeProvider"))return;
  try{
    const responses=await Promise.all([
      fetch("/health",{cache:"no-store"}),
      fetch("/v1/capabilities",{cache:"no-store"})
    ]);
    const h=await responses[0].json();
    const cap=await responses[1].json();
    $("runtimeModel").textContent=h.model||"NCAIR1/N-ATLaS";
    $("runtimeProvider").textContent=h.provider||"disabled";
    $("runtimeDirect").textContent=h.direct_natlas_integration?"Configured":"Pending";
    $("healthRaw").textContent=JSON.stringify(h,null,2);
    const groups=[
      ["Interfaces",cap.interfaces||[]],
      ["Runtime modes",cap.runtime_modes||[]],
      ["Evaluation",cap.evaluation||[]],
      ["Adaptation",cap.adaptation||[]],
      ["Documentation",cap.documentation_languages||[]],
      ["Speech models",Object.entries(cap.asr_models||{}).map(function(pair){return pair[0]+": "+pair[1];})]
    ];
    $("capabilities").innerHTML=groups.map(function(group){
      return "<section><strong>"+group[0]+"</strong><div>"+group[1].map(function(item){
        return "<span>"+item+"</span>";
      }).join("")+"</div></section>";
    }).join("");
  }catch(error){
    $("runtimeProvider").textContent="Unavailable";
  }
}

if($("refreshRuntimeBtn"))$("refreshRuntimeBtn").addEventListener("click",refreshRuntimeWorkspace);
if($("probeRuntimeBtn"))$("probeRuntimeBtn").addEventListener("click",async function(){
  $("runtimeProbe").textContent="Running…";
  try{
    const response=await fetch("/api/runtime/probe",{method:"POST"});
    const result=await readApiResponse(response);
    $("runtimeProbe").textContent=result.provenance_verified?"Verified":"Unverified";
  }catch(error){
    $("runtimeProbe").textContent="Unavailable";
    showToast(error.message,"error");
  }
});


/* ---------- Profile / Settings ---------- */
let profileState=null;
let profileNewestKey="";

async function profileApi(path,options={}){
  const response=await fetch(path,{
    credentials:"same-origin",
    ...options,
    headers:{
      ...(options.body?{"content-type":"application/json"}:{}),
      ...(options.headers||{})
    }
  });
  return readApiResponse(response);
}

function profileInitials(account){
  if(!account)return "P";
  const source=(account.display_name||account.email||"Profile").trim();
  if(source.includes(" ")){
    return source.split(/\s+/).slice(0,2).map(function(part){return part[0]||"";}).join("").toUpperCase();
  }
  return source.slice(0,2).toUpperCase();
}

function renderHeaderProfile(account){
  if(!$("profileAvatar"))return;
  const initials=profileInitials(account);
  $("profileAvatar").textContent=initials;
  if($("profileHeroAvatar"))$("profileHeroAvatar").textContent=initials;
  $("profileMenuName").textContent=account?(account.display_name||"Developer account"):"Developer account";
  $("profileMenuEmail").textContent=account?account.email:"Sign in to manage your account";
  if($("profileButtonName"))$("profileButtonName").textContent=account?(account.display_name||"Profile"):"Profile";
  $("profileSignInLink").classList.toggle("hidden",Boolean(account));
  $("profileMenuLogoutBtn").classList.toggle("hidden",!account);
}

function closeProfileMenu(){
  if(!$("profileMenu")||!$("profileMenuBtn"))return;
  $("profileMenu").classList.add("hidden");
  $("profileMenuBtn").setAttribute("aria-expanded","false");
}

function toggleProfileMenu(){
  if(!$("profileMenu")||!$("profileMenuBtn"))return;
  const opening=$("profileMenu").classList.contains("hidden");
  $("profileMenu").classList.toggle("hidden",!opening);
  $("profileMenuBtn").setAttribute("aria-expanded",String(opening));
}

function openProfileDestination(destination){
  closeProfileMenu();
  consolePanel("profile");
  const ids={
    account:"profileAccountSection",
    keys:"profileApiKeysSection",
    usage:"profileRecentUsageSection"
  };
  setTimeout(function(){
    const target=$(ids[destination]||"panel-profile");
    if(target)target.scrollIntoView({behavior:"smooth",block:"start"});
  },80);
}

async function refreshHeaderProfile(){
  try{
    const data=await profileApi("/api/developer/me");
    renderHeaderProfile(data.account);
  }catch(error){
    if(error.status===401){
      renderHeaderProfile(null);
      return;
    }
  }
}

async function logoutProfileSession(){
  try{await profileApi("/api/developer/logout",{method:"POST"});}catch(_){}
  profileState=null;
  profileNewestKey="";
  if($("profileNewKeyReveal"))$("profileNewKeyReveal").classList.add("hidden");
  if($("profileWorkspace"))$("profileWorkspace").classList.add("hidden");
  if($("profileSignedOut"))$("profileSignedOut").classList.remove("hidden");
  renderHeaderProfile(null);
  closeProfileMenu();
  showToast("Logged out.","success");
}

if($("profileMenuBtn"))$("profileMenuBtn").addEventListener("click",function(event){
  event.stopPropagation();
  toggleProfileMenu();
});

if($("profileMenu"))$("profileMenu").addEventListener("click",function(event){
  event.stopPropagation();
});

document.querySelectorAll("[data-profile-destination]").forEach(function(button){
  button.addEventListener("click",function(){
    openProfileDestination(button.dataset.profileDestination);
  });
});

if($("profileMenuLogoutBtn"))$("profileMenuLogoutBtn").addEventListener("click",logoutProfileSession);
if($("profileSignInLink"))$("profileSignInLink").addEventListener("click",closeProfileMenu);

document.addEventListener("click",closeProfileMenu);
document.addEventListener("keydown",function(event){
  if(event.key==="Escape")closeProfileMenu();
});

function profileMoney(value){
  const amount=Number(value||0);
  return "$"+amount.toFixed(6).replace(/0+$/,"").replace(/\.$/,".00");
}

function profileScopeLabel(scope){
  const labels={
    "inference.generate":"Generate",
    "inference.chat":"Chat completions",
    "usecases.run":"Use Case Studio",
    "speech.transcribe":"Speech transcription",
    "evaluation.run":"Evaluation",
    "dataset.inspect":"Dataset inspection",
    "finetuning.plan":"Fine-tune planner"
  };
  return labels[scope]||scope;
}

function renderProfileScopes(scopes){
  const root=$("profileScopeOptions");
  if(!root)return;
  root.innerHTML="";
  scopes.forEach(function(scope){
    const label=document.createElement("label");
    label.className="scope-option";
    const input=document.createElement("input");
    input.type="checkbox";
    input.value=scope;
    input.checked=["inference.generate","inference.chat","usecases.run","speech.transcribe"].includes(scope);
    const text=document.createElement("span");
    const strong=document.createElement("strong");
    strong.textContent=profileScopeLabel(scope);
    const small=document.createElement("small");
    small.textContent=scope;
    text.append(strong,small);
    label.append(input,text);
    root.appendChild(label);
  });
}

function renderProfileKeys(keys){
  const root=$("profileApiKeyList");
  if(!root)return;
  root.innerHTML="";
  if(!keys.length){
    root.innerHTML='<p class="hint">No API keys yet.</p>';
    return;
  }
  keys.forEach(function(key){
    const row=document.createElement("div");
    row.className="developer-list-row"+(key.revoked_at?" revoked":"");

    const info=document.createElement("div");
    const title=document.createElement("strong");
    title.textContent=key.name;
    const meta=document.createElement("small");
    meta.textContent=key.prefix+"… · "+(key.scopes||[]).map(profileScopeLabel).join(", ");
    info.append(title,meta);

    const side=document.createElement("div");
    side.className="developer-list-side";
    const status=document.createElement("span");
    status.className="status "+(key.revoked_at?"":"good");
    status.textContent=key.revoked_at?"Revoked":"Active";
    side.appendChild(status);

    if(!key.revoked_at){
      const revoke=document.createElement("button");
      revoke.className="text-button";
      revoke.type="button";
      revoke.textContent="Revoke";
      revoke.addEventListener("click",function(){revokeProfileKey(key.id);});
      side.appendChild(revoke);
    }
    row.append(info,side);
    root.appendChild(row);
  });
}

function renderProfileUsage(events){
  const body=$("profileUsageRows");
  if(!body)return;
  body.innerHTML="";
  if(!events.length){
    body.innerHTML='<tr><td colspan="7">No metered requests yet.</td></tr>';
    return;
  }
  events.forEach(function(event){
    const tr=document.createElement("tr");
    const values=[
      event.feature,
      Number(event.prompt_tokens).toLocaleString(),
      Number(event.completion_tokens).toLocaleString(),
      Number(event.total_tokens).toLocaleString(),
      event.measurement,
      profileMoney(Number(event.cost_microusd)/1_000_000),
      new Date(event.created_at).toLocaleString()
    ];
    values.forEach(function(value){
      const td=document.createElement("td");
      td.textContent=value;
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

function renderProfileWorkspace(data){
  profileState=data;
  $("profileSignedOut").classList.add("hidden");
  $("profileWorkspace").classList.remove("hidden");

  const account=data.account;
  renderHeaderProfile(account);
  $("profileGreeting").textContent=account.display_name||"Developer account";
  $("profileEmail").textContent=account.email+(account.is_demo?" · demo account":"");
  $("profileBalance").textContent=profileMoney(data.usage.balance_usd);
  $("profileTokens").textContent=Number(data.usage.total_tokens||0).toLocaleString();
  $("profileCost").textContent=profileMoney(data.usage.total_cost_usd);

  const active=(data.api_keys||[]).filter(function(key){return !key.revoked_at;});
  $("profileKeyCount").textContent=active.length;
  $("profileInputRate").textContent="$"+Number(data.pricing.input_usd_per_1m_tokens).toFixed(4);
  $("profileOutputRate").textContent="$"+Number(data.pricing.output_usd_per_1m_tokens).toFixed(4);

  renderProfileScopes(data.available_scopes||[]);
  renderProfileKeys(data.api_keys||[]);
  renderProfileUsage(data.usage.events||[]);

  $("profileCurl").textContent='curl -X POST '+location.origin+'/v1/generate \\\n'
    +'  -H "Authorization: Bearer $EDNAI_API_KEY" \\\n'
    +'  -H "Content-Type: application/json" \\\n'
    +'  -d \'{"model":"NCAIR1/N-ATLaS","messages":[{"role":"user","content":"Explain APIs simply."}]}\'';
}

async function refreshProfileWorkspace(){
  if(!$("profileWorkspace")||!$("profileSignedOut"))return;
  try{
    const data=await profileApi("/api/developer/me");
    renderProfileWorkspace(data);
  }catch(error){
    if(error.status===401){
      profileState=null;
      profileNewestKey="";
      $("profileWorkspace").classList.add("hidden");
      $("profileSignedOut").classList.remove("hidden");
      renderHeaderProfile(null);
      return;
    }
    showToast(error.message,"error");
  }
}

async function revokeProfileKey(id){
  if(!confirm("Revoke this API key? Applications using it will stop working."))return;
  try{
    await profileApi("/api/developer/keys/"+encodeURIComponent(id),{method:"DELETE"});
    showToast("API key revoked.","success");
    await refreshProfileWorkspace();
  }catch(error){
    showToast(error.message,"error");
  }
}

if($("profileRefreshBtn"))$("profileRefreshBtn").addEventListener("click",refreshProfileWorkspace);

if($("profileLogoutBtn"))$("profileLogoutBtn").addEventListener("click",logoutProfileSession);

if($("profileCreateApiKeyBtn"))$("profileCreateApiKeyBtn").addEventListener("click",async function(){
  const scopes=[...document.querySelectorAll("#profileScopeOptions input:checked")].map(function(x){return x.value;});
  if(!scopes.length){
    showToast("Select at least one permission.","error");
    return;
  }
  try{
    const created=await profileApi("/api/developer/keys",{
      method:"POST",
      body:JSON.stringify({
        name:$("profileApiKeyName").value||"API key",
        scopes:scopes
      })
    });
    profileNewestKey=created.key;
    $("profileNewApiKeySecret").textContent=created.key;
    $("profileNewKeyReveal").classList.remove("hidden");
    showToast("API key created. Copy it now.","success");
    await refreshProfileWorkspace();
  }catch(error){
    showToast(error.message,"error");
  }
});

if($("profileCopyNewApiKeyBtn"))$("profileCopyNewApiKeyBtn").addEventListener("click",async function(){
  if(!profileNewestKey)return;
  await copyText(profileNewestKey);
  showToast("API key copied.","success");
});

if($("profileCopyCurlBtn"))$("profileCopyCurlBtn").addEventListener("click",async function(){
  await copyText($("profileCurl").textContent);
  showToast("cURL example copied.","success");
});


function renderQuickstart(stack,markProgress=true){
  const next=quickstartSamples[stack]?stack:"python";
  if($("quickstartCode"))$("quickstartCode").textContent=quickstartSamples[next];
  document.querySelectorAll(".stack-tab").forEach(tab=>{
    tab.classList.toggle("active",tab.dataset.stack===next);
  });
  try{localStorage.setItem("ednai-quickstart-stack",next);}catch(_){}
  if(markProgress)completeOnboarding("stack");
}

document.querySelectorAll(".stack-tab").forEach(tab=>{
  tab.addEventListener("click",()=>renderQuickstart(tab.dataset.stack,true));
});

if($("copyQuickstartBtn"))$("copyQuickstartBtn").addEventListener("click",async()=>{
  await copyText($("quickstartCode").textContent);
  $("copyQuickstartBtn").textContent="Copied";
  completeOnboarding("ship");
  showToast("Integration code copied.","success");
  setTimeout(()=>{$("copyQuickstartBtn").textContent="Copy";},1200);
});

if($("downloadStarterLink"))$("downloadStarterLink").addEventListener("click",()=>{
  completeOnboarding("ship");
  showToast("Starter project download started.","success");
});

function focusPlayground(){
  consolePanel("playground");
  const target=$("panel-playground");
  if(target)target.scrollIntoView({behavior:"smooth",block:"start"});
  setTimeout(()=>{$("prompt").focus();},350);
}

if($("tryQuickstartBtn"))$("tryQuickstartBtn").addEventListener("click",()=>{
  $("system").value="You are a helpful Nigerian AI assistant. Answer clearly and concisely.";
  $("prompt").value="Explain what an API is to a new Nigerian developer in simple terms.";
  $("jsonMode").checked=false;
  focusPlayground();
});

function scrollToLaunchpad(){
  focusPlayground();
}
if($("heroStartBtn"))$("heroStartBtn").addEventListener("click",focusPlayground);
if($("quickstartNavBtn"))$("quickstartNavBtn").addEventListener("click",focusPlayground);

document.querySelectorAll(".template-card").forEach(card=>{
  card.addEventListener("click",()=>{
    if(card.dataset.template==="voice"){
      consolePanel("speech");
      const speech=$("panel-speech");
      if(speech)speech.scrollIntoView({behavior:"smooth",block:"start"});
      return;
    }
    const template=promptTemplates[card.dataset.template];
    if(!template)return;
    $("system").value=template.system;
    $("prompt").value=template.prompt;
    $("jsonMode").checked=template.json;
    $("maxTokens").value=template.maxTokens;
    $("temperature").value=".2";
    focusPlayground();
    showToast("Template loaded. Review it, then run N-ATLaS.","success");
  });
});

if($("composerExamplesBtn"))$("composerExamplesBtn").addEventListener("click",()=>{
  consolePanel("overview");
});

if($("hideTemplatesBtn"))$("hideTemplatesBtn").addEventListener("click",()=>{
  const grid=$("templateGrid");
  const hidden=grid.classList.toggle("collapsed");
  $("hideTemplatesBtn").textContent=hidden?"Show templates":"Hide templates";
});

if($("stepStack"))$("stepStack").addEventListener("click",scrollToLaunchpad);
if($("stepRun"))$("stepRun").addEventListener("click",focusPlayground);
if($("stepShip"))$("stepShip").addEventListener("click",scrollToLaunchpad);

function openCommandPalette(){
  const dialog=$("commandPalette");
  if(!dialog)return;
  if(!dialog.open)dialog.showModal();
  $("commandSearch").value="";
  document.querySelectorAll("#commandList button").forEach(button=>button.hidden=false);
  setTimeout(()=>$("commandSearch").focus(),30);
}
if($("closeCommandBtn"))$("closeCommandBtn").addEventListener("click",()=>$("commandPalette").close());

if($("commandSearch"))$("commandSearch").addEventListener("input",event=>{
  const query=event.target.value.trim().toLowerCase();
  document.querySelectorAll("#commandList button").forEach(button=>{
    button.hidden=query&&!button.textContent.toLowerCase().includes(query);
  });
});

document.querySelectorAll("[data-command]").forEach(button=>{
  button.addEventListener("click",()=>{
    const action=button.dataset.command;
    if(action==="docs"){
      window.location.href="/guide";
      return;
    }
    $("commandPalette").close();
    consolePanel(action);
    const target=$("panel-"+action);
    if(target)target.scrollIntoView({behavior:"smooth",block:"start"});
  });
});

document.addEventListener("keydown",event=>{
  if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="k"){
    event.preventDefault();
    openCommandPalette();
    return;
  }
  const tag=(document.activeElement&&document.activeElement.tagName||"").toLowerCase();
  if(event.key==="/"&&!["input","textarea","select"].includes(tag)&&!$("commandPalette").open){
    event.preventDefault();
    consolePanel("playground");
    $("prompt").focus();
  }
});


/* ---------- N-ATLaS Translation Studio ---------- */
const translationLanguageLabels={
  english:"English / Nigerian English",
  yoruba:"Yorùbá",
  hausa:"Hausa",
  igbo:"Igbo"
};
let lastTranslationResult="";

function translationPayload(){
  const source=$("translationSourceLanguage")?$("translationSourceLanguage").value:"english";
  const target=$("translationTargetLanguage")?$("translationTargetLanguage").value:"yoruba";
  return {
    language:target,
    inputs:{
      source_language:source,
      target_language:target,
      text:$("translationInput")?$("translationInput").value.trim():"",
      notes:$("translationNotes")?$("translationNotes").value.trim():""
    },
    temperature:0.1,
    max_tokens:900,
    json_mode:false
  };
}

function updateTranslationCount(){
  if(!$("translationInput")||!$("translationCharCount"))return;
  const length=$("translationInput").value.length;
  $("translationCharCount").textContent=length.toLocaleString()+" / 12,000 characters";
}

function updateTranslationCode(){
  if(!$("translationCode"))return;
  const payload=translationPayload();
  $("translationCode").textContent=
`curl -X POST ${location.origin}/v1/use-cases/translation \\\n`+
`  -H "Authorization: Bearer $EDNAI_API_KEY" \\\n`+
`  -H "Content-Type: application/json" \\\n`+
`  --data-binary @- <<'JSON'\n`+
JSON.stringify(payload,null,2)+
`\nJSON`;
}

function resetTranslationOutput(){
  lastTranslationResult="";
  if($("translationOutput"))$("translationOutput").value="";
  if($("translationCopyBtn"))$("translationCopyBtn").disabled=true;
  if($("translationToPlaygroundBtn"))$("translationToPlaygroundBtn").disabled=true;
  if($("translationMeta"))$("translationMeta").textContent="Ready";
}

function loadTranslationExample(){
  if(!$("translationInput"))return;
  $("translationSourceLanguage").value="english";
  $("translationTargetLanguage").value="yoruba";
  $("translationInput").value="Digital tools should be understandable and useful to everyone.";
  $("translationNotes").value="Keep the translation clear, natural and easy to understand.";
  updateTranslationCount();
  updateTranslationCode();
  resetTranslationOutput();
  showToast("Translation sample loaded.","success");
}

async function runTranslation(){
  const payload=translationPayload();
  if(!payload.inputs.text){
    showToast("Enter the text you want to translate.","error");
    if($("translationInput"))$("translationInput").focus();
    return;
  }
  if(payload.inputs.source_language===payload.inputs.target_language){
    showToast("Choose a different target language.","error");
    if($("translationTargetLanguage"))$("translationTargetLanguage").focus();
    return;
  }

  setButtonLoading($("runTranslationBtn"),true);
  if($("translationMeta"))$("translationMeta").textContent="Translating with N-ATLaS…";
  if($("translationOutput"))$("translationOutput").value="";

  try{
    const response=await fetch("/v1/use-cases/translation",{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify(payload)
    });
    const result=await readApiResponse(response);
    lastTranslationResult=result.text||"";
    $("translationOutput").value=lastTranslationResult;
    $("translationCopyBtn").disabled=!lastTranslationResult;
    $("translationToPlaygroundBtn").disabled=!lastTranslationResult;
    $("translationMeta").textContent=[
      translationLanguageLabels[payload.inputs.source_language]+" → "+translationLanguageLabels[payload.inputs.target_language],
      result.model||"NCAIR1/N-ATLaS",
      result.provider||"EDNAi",
      result.latency_ms!=null?result.latency_ms+" ms":""
    ].filter(Boolean).join(" · ");
    showToast("Translation completed with N-ATLaS.","success");
  }catch(error){
    lastTranslationResult="";
    $("translationOutput").value="Runtime error: "+error.message;
    $("translationMeta").textContent=error.status===429?"N-ATLaS quota temporarily exhausted":"Translation failed";
    $("translationCopyBtn").disabled=true;
    $("translationToPlaygroundBtn").disabled=true;
    showToast(error.message,"error");
  }finally{
    setButtonLoading($("runTranslationBtn"),false);
  }
}

if($("translationInput")){
  $("translationInput").addEventListener("input",()=>{
    updateTranslationCount();
    updateTranslationCode();
  });
}
if($("translationNotes"))$("translationNotes").addEventListener("input",updateTranslationCode);
if($("translationSourceLanguage"))$("translationSourceLanguage").addEventListener("change",()=>{
  updateTranslationCode();
  resetTranslationOutput();
});
if($("translationTargetLanguage"))$("translationTargetLanguage").addEventListener("change",()=>{
  updateTranslationCode();
  resetTranslationOutput();
});
if($("translationExampleBtn"))$("translationExampleBtn").addEventListener("click",loadTranslationExample);
if($("translationClearBtn"))$("translationClearBtn").addEventListener("click",()=>{
  $("translationInput").value="";
  $("translationNotes").value="";
  updateTranslationCount();
  updateTranslationCode();
  resetTranslationOutput();
  $("translationInput").focus();
});
if($("swapTranslationBtn"))$("swapTranslationBtn").addEventListener("click",()=>{
  const source=$("translationSourceLanguage").value;
  const target=$("translationTargetLanguage").value;
  $("translationSourceLanguage").value=target;
  $("translationTargetLanguage").value=source;
  if(lastTranslationResult){
    const previousSource=$("translationInput").value;
    $("translationInput").value=lastTranslationResult;
    $("translationOutput").value=previousSource;
    lastTranslationResult=previousSource;
    $("translationCopyBtn").disabled=!lastTranslationResult;
    $("translationToPlaygroundBtn").disabled=!lastTranslationResult;
  }else{
    resetTranslationOutput();
  }
  updateTranslationCount();
  updateTranslationCode();
});
if($("runTranslationBtn"))$("runTranslationBtn").addEventListener("click",runTranslation);
if($("translationInput"))$("translationInput").addEventListener("keydown",event=>{
  if((event.ctrlKey||event.metaKey)&&event.key==="Enter")runTranslation();
});
if($("translationCopyBtn"))$("translationCopyBtn").addEventListener("click",async()=>{
  if(!lastTranslationResult)return;
  await copyText(lastTranslationResult);
  showToast("Translation copied.","success");
});
if($("translationToPlaygroundBtn"))$("translationToPlaygroundBtn").addEventListener("click",()=>{
  if(!lastTranslationResult)return;
  $("prompt").value=lastTranslationResult;
  consolePanel("playground");
  $("panel-playground").scrollIntoView({behavior:"smooth",block:"start"});
  setTimeout(()=>$("prompt").focus(),300);
});
if($("copyTranslationCodeBtn"))$("copyTranslationCodeBtn").addEventListener("click",async()=>{
  await copyText($("translationCode").textContent);
  showToast("Translation API example copied.","success");
});

updateTranslationCount();
updateTranslationCode();


/* ---------- N-ATLaS Use Case Studio ---------- */
let useCaseRegistry=null;
let activeUseCase="chatbot";
let useCaseStack="python";
let lastUseCaseResult="";

function currentUseCaseDefinition(){
  return useCaseRegistry&&useCaseRegistry.use_cases
    ?useCaseRegistry.use_cases[activeUseCase]
    :null;
}

function renderUseCaseCatalog(){
  const root=$("useCaseCatalog");
  if(!root||!useCaseRegistry)return;
  root.innerHTML="";
  Object.entries(useCaseRegistry.use_cases).forEach(([slug,definition])=>{
    const button=document.createElement("button");
    button.type="button";
    button.className="usecase-card"+(slug===activeUseCase?" active":"");
    button.dataset.useCase=slug;

    const icon=document.createElement("span");
    icon.className="usecase-card-icon";
    icon.textContent=definition.icon;

    const copy=document.createElement("span");
    const title=document.createElement("strong");
    title.textContent=definition.title;
    const description=document.createElement("small");
    description.textContent=definition.description;
    copy.append(title,description);

    button.append(icon,copy);
    button.addEventListener("click",()=>selectUseCase(slug));
    root.appendChild(button);
  });
}

function renderUseCaseFields(definition){
  const root=$("useCaseFields");
  if(!root)return;
  root.innerHTML="";

  definition.fields.forEach(field=>{
    const label=document.createElement("label");
    label.textContent=field.label+(field.required?" *":"");

    let input;
    if(field.type==="select"){
      input=document.createElement("select");
      (field.options||[]).forEach(option=>{
        const node=document.createElement("option");
        node.value=option.value;
        node.textContent=option.label;
        input.appendChild(node);
      });
      input.value=field.default||((field.options||[])[0]?.value||"");
    }else if(field.type==="input"){
      input=document.createElement("input");
      input.type="text";
      input.placeholder=field.placeholder||"";
      input.value=field.default||"";
    }else{
      input=document.createElement("textarea");
      input.rows=5;
      input.placeholder=field.placeholder||"";
      input.value=field.default||"";
    }

    input.dataset.useCaseField=field.name;
    input.dataset.required=field.required?"true":"false";
    input.addEventListener("input",()=>{
      if(activeUseCase==="translation"&&field.name==="target_language"&&$("useCaseLanguage")){
        $("useCaseLanguage").value=input.value;
      }
      updateUseCaseCode();
    });
    input.addEventListener("change",()=>{
      if(activeUseCase==="translation"&&field.name==="target_language"&&$("useCaseLanguage")){
        $("useCaseLanguage").value=input.value;
      }
      updateUseCaseCode();
    });
    label.appendChild(input);

    if(field.help){
      const help=document.createElement("span");
      help.className="usecase-field-help";
      help.textContent=field.help;
      label.appendChild(help);
    }
    root.appendChild(label);
  });
}

function collectUseCaseInputs(){
  const values={};
  document.querySelectorAll("[data-use-case-field]").forEach(input=>{
    values[input.dataset.useCaseField]=input.value;
  });
  return values;
}

function selectUseCase(slug){
  if(!useCaseRegistry||!useCaseRegistry.use_cases[slug])return;
  activeUseCase=slug;
  const definition=useCaseRegistry.use_cases[slug];
  renderUseCaseCatalog();
  $("useCaseIcon").textContent=definition.icon;
  $("useCaseTitle").textContent=definition.title;
  $("useCaseDescription").textContent=definition.description;
  $("useCaseOutputLabel").textContent=definition.output_label||"N-ATLaS output";
  $("useCaseTemperature").value=definition.temperature;
  $("useCaseMaxTokens").value=definition.max_tokens;
  $("useCaseJsonMode").checked=false;
  renderUseCaseFields(definition);
  lastUseCaseResult="";
  $("useCaseResult").textContent="Run the workflow to see the N-ATLaS response here.";
  $("useCaseResult").className="usecase-result empty";
  $("useCaseMeta").textContent="";
  $("copyUseCaseResultBtn").disabled=true;
  $("useCaseToPlaygroundBtn").disabled=true;
  $("useCaseStatus").textContent="Ready";
  updateUseCaseCode();
}

function loadUseCaseExample(){
  const definition=currentUseCaseDefinition();
  if(!definition)return;
  const example=definition.example_inputs||{};
  document.querySelectorAll("[data-use-case-field]").forEach(input=>{
    if(Object.prototype.hasOwnProperty.call(example,input.dataset.useCaseField)){
      input.value=example[input.dataset.useCaseField];
    }
  });
  if(activeUseCase==="translation"&&example.target_language){
    $("useCaseLanguage").value=example.target_language;
  }
  updateUseCaseCode();
  showToast("Example loaded. Run it with N-ATLaS when ready.","success");
}

function updateUseCaseCode(){
  if(!useCaseRegistry||!currentUseCaseDefinition()||!$("useCaseCode"))return;
  const inputs=collectUseCaseInputs();
  const language=$("useCaseLanguage").value;
  const temperature=Number($("useCaseTemperature").value);
  const maxTokens=Number($("useCaseMaxTokens").value);
  const jsonMode=$("useCaseJsonMode").checked;

  const payload={
    language,
    inputs,
    temperature,
    max_tokens:maxTokens,
    json_mode:jsonMode
  };

  let code="";
  if(useCaseStack==="typescript"){
    code=`import { EDNAi } from "@ednai/sdk";

const ai = new EDNAi({
  baseUrl: "https://ednai-6znf.onrender.com",
  apiKey: process.env.EDNAI_API_KEY
});

const result = await ai.runUseCase(
  "${activeUseCase}",
  ${JSON.stringify(inputs,null,2)},
  {
    language: "${language}",
    temperature: ${temperature},
    maxTokens: ${maxTokens},
    jsonMode: ${jsonMode}
  }
);

console.log(result.text);`;
  }else if(useCaseStack==="curl"){
    code=`curl -X POST https://ednai-6znf.onrender.com/v1/use-cases/${activeUseCase} \\\n  -H "Authorization: Bearer $EDNAI_API_KEY" \\\n  -H "Content-Type: application/json" \\\n  --data-binary @- <<'JSON'
${JSON.stringify(payload,null,2)}
JSON`;
  }else{
    code=`import os
from ednai import EDNAi

ai = EDNAi(
    base_url="https://ednai-6znf.onrender.com",
    api_key=os.environ["EDNAI_API_KEY"],
)

result = ai.run_use_case(
    "${activeUseCase}",
    ${JSON.stringify(inputs,null,4)},
    language="${language}",
    temperature=${temperature},
    max_tokens=${maxTokens},
    json_mode=${jsonMode?"True":"False"},
)

print(result.text)`;
  }
  $("useCaseCode").textContent=code;
}

async function loadUseCaseRegistry(){
  try{
    const response=await fetch("/v1/use-cases",{cache:"no-store"});
    useCaseRegistry=await readApiResponse(response);
    renderUseCaseCatalog();
    selectUseCase(activeUseCase);
  }catch(error){
    if($("useCaseCatalog")){
      $("useCaseCatalog").innerHTML='<p class="hint">Could not load use-case definitions.</p>';
    }
    if($("useCaseStatus"))$("useCaseStatus").textContent="Registry unavailable";
  }
}

if($("loadUseCaseExampleBtn"))$("loadUseCaseExampleBtn").addEventListener("click",loadUseCaseExample);
if($("useCaseLanguage"))$("useCaseLanguage").addEventListener("change",updateUseCaseCode);
if($("useCaseTemperature"))$("useCaseTemperature").addEventListener("input",updateUseCaseCode);
if($("useCaseMaxTokens"))$("useCaseMaxTokens").addEventListener("input",updateUseCaseCode);
if($("useCaseJsonMode"))$("useCaseJsonMode").addEventListener("change",updateUseCaseCode);

document.querySelectorAll(".usecase-stack").forEach(button=>{
  button.addEventListener("click",()=>{
    useCaseStack=button.dataset.usecaseStack;
    document.querySelectorAll(".usecase-stack").forEach(item=>{
      item.classList.toggle("active",item===button);
    });
    updateUseCaseCode();
  });
});

if($("runUseCaseBtn"))$("runUseCaseBtn").addEventListener("click",async()=>{
  const definition=currentUseCaseDefinition();
  if(!definition)return;

  const inputs=collectUseCaseInputs();
  const missing=definition.fields.find(field=>field.required&&!String(inputs[field.name]||"").trim());
  if(missing){
    const input=document.querySelector('[data-use-case-field="'+missing.name+'"]');
    showToast("Complete "+missing.label+" first.","error");
    if(input)input.focus();
    return;
  }

  setButtonLoading($("runUseCaseBtn"),true);
  $("useCaseStatus").textContent="Running N-ATLaS…";
  $("useCaseResult").textContent="Generating with N-ATLaS";
  $("useCaseResult").className="usecase-result generating";
  $("useCaseMeta").textContent="";

  try{
    const response=await fetch("/v1/use-cases/"+activeUseCase,{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({
        language:$("useCaseLanguage").value,
        inputs,
        temperature:Number($("useCaseTemperature").value),
        max_tokens:Number($("useCaseMaxTokens").value),
        json_mode:$("useCaseJsonMode").checked
      })
    });
    const result=await readApiResponse(response);
    lastUseCaseResult=result.text||"";
    $("useCaseResult").textContent=lastUseCaseResult||"(N-ATLaS returned an empty response.)";
    $("useCaseResult").className="usecase-result";
    $("useCaseMeta").textContent=[
      result.use_case,
      result.language,
      result.model,
      result.provider||"EDNAi",
      result.latency_ms!=null?result.latency_ms+" ms":""
    ].filter(Boolean).join(" · ");
    $("useCaseStatus").textContent="Completed";
    $("copyUseCaseResultBtn").disabled=!lastUseCaseResult;
    $("useCaseToPlaygroundBtn").disabled=!lastUseCaseResult;
    showToast(definition.title+" completed with N-ATLaS.","success");
  }catch(error){
    lastUseCaseResult="";
    $("useCaseResult").textContent="Runtime error: "+error.message;
    $("useCaseResult").className="usecase-result";
    $("useCaseStatus").textContent=error.status===429?"Quota exhausted":"Request failed";
    showToast(error.message,"error");
  }finally{
    setButtonLoading($("runUseCaseBtn"),false);
  }
});

if($("copyUseCaseResultBtn"))$("copyUseCaseResultBtn").addEventListener("click",async()=>{
  if(!lastUseCaseResult)return;
  await copyText(lastUseCaseResult);
  showToast("N-ATLaS result copied.","success");
});

if($("useCaseToPlaygroundBtn"))$("useCaseToPlaygroundBtn").addEventListener("click",()=>{
  if(!lastUseCaseResult)return;
  $("prompt").value=lastUseCaseResult;
  consolePanel("playground");
  $("panel-playground").scrollIntoView({behavior:"smooth",block:"start"});
  setTimeout(()=>$("prompt").focus(),300);
});

if($("copyUseCaseCodeBtn"))$("copyUseCaseCodeBtn").addEventListener("click",async()=>{
  await copyText($("useCaseCode").textContent);
  showToast("Integration code copied.","success");
});

loadUseCaseRegistry();


/* ---------- Speech Studio ---------- */
const officialAsrModels={
  english:"NCAIR1/NigerianAccentedEnglish",
  yoruba:"NCAIR1/Yoruba-ASR",
  hausa:"NCAIR1/Hausa-ASR",
  igbo:"NCAIR1/Igbo-ASR"
};

function updateSelectedAsrModel(){
  if($("selectedAsrModel")){
    $("selectedAsrModel").textContent=officialAsrModels[$("asrLanguage").value]||"";
  }
}
let selectedAudioBlob=null;
let selectedAudioName="audio.webm";
let selectedAudioUrl=null;
let mediaRecorder=null;
let mediaStream=null;
let recordingChunks=[];
let recordingStartedAt=0;
let recordingTimerHandle=null;

function setAsrStatus(text,state){
  if(!$("asrStatus"))return;
  $("asrStatus").textContent=text;
  $("asrStatus").className="status "+(state||"");
}

function resetRecordingTimer(){
  clearInterval(recordingTimerHandle);
  recordingTimerHandle=null;
  if($("recordingTimer"))$("recordingTimer").textContent="Not recording";
}

function updateRecordingTimer(){
  if(!$("recordingTimer"))return;
  const elapsed=Math.max(0,Math.floor((Date.now()-recordingStartedAt)/1000));
  const minutes=String(Math.floor(elapsed/60)).padStart(2,"0");
  const seconds=String(elapsed%60).padStart(2,"0");
  $("recordingTimer").textContent=minutes+":"+seconds;
}

function setAudioBlob(blob,name){
  selectedAudioBlob=blob;
  selectedAudioName=name||"audio.webm";
  if(selectedAudioUrl)URL.revokeObjectURL(selectedAudioUrl);
  selectedAudioUrl=URL.createObjectURL(blob);
  if($("asrPreview")){
    $("asrPreview").src=selectedAudioUrl;
    $("asrPreview").classList.remove("hidden");
  }
  if($("asrDropZone")){
    const strong=$("asrDropZone").querySelector("strong");
    const small=$("asrDropZone").querySelector("small");
    if(strong)strong.textContent=selectedAudioName;
    if(small)small.textContent=(blob.size/1024/1024).toFixed(2)+" MB · ready to transcribe";
  }
  setAsrStatus("Audio ready","good");
}

function clearAudio(){
  selectedAudioBlob=null;
  selectedAudioName="audio.webm";
  if(selectedAudioUrl){
    URL.revokeObjectURL(selectedAudioUrl);
    selectedAudioUrl=null;
  }
  if($("asrFile"))$("asrFile").value="";
  if($("asrPreview")){
    $("asrPreview").removeAttribute("src");
    $("asrPreview").classList.add("hidden");
  }
  if($("asrTranscript"))$("asrTranscript").value="";
  if($("asrMeta"))$("asrMeta").textContent="Select or record audio to begin.";
  if($("asrWer"))$("asrWer").textContent="—";
  if($("asrCer"))$("asrCer").textContent="—";
  if($("asrRefWords"))$("asrRefWords").textContent="—";
  if($("copyTranscriptBtn"))$("copyTranscriptBtn").disabled=true;
  if($("useTranscriptBtn"))$("useTranscriptBtn").disabled=true;
  if($("asrDropZone")){
    const strong=$("asrDropZone").querySelector("strong");
    const small=$("asrDropZone").querySelector("small");
    if(strong)strong.textContent="Drop an audio file here";
    if(small)small.textContent="or click to choose WAV, MP3, M4A, OGG or WebM · max 25 MB";
  }
  setAsrStatus("Ready","");
}

if($("asrDropZone")){
  $("asrDropZone").addEventListener("click",()=>$("asrFile").click());
  ["dragenter","dragover"].forEach(type=>$("asrDropZone").addEventListener(type,event=>{
    event.preventDefault();
    $("asrDropZone").classList.add("dragover");
  }));
  ["dragleave","drop"].forEach(type=>$("asrDropZone").addEventListener(type,event=>{
    event.preventDefault();
    $("asrDropZone").classList.remove("dragover");
  }));
  $("asrDropZone").addEventListener("drop",event=>{
    const file=event.dataTransfer.files&&event.dataTransfer.files[0];
    if(!file)return;
    if(file.size>25*1024*1024){
      showToast("Audio files are limited to 25 MB.","error");
      return;
    }
    setAudioBlob(file,file.name);
  });
}
if($("asrFile"))$("asrFile").addEventListener("change",()=>{
  const file=$("asrFile").files&&$("asrFile").files[0];
  if(!file)return;
  if(file.size>25*1024*1024){
    showToast("Audio files are limited to 25 MB.","error");
    $("asrFile").value="";
    return;
  }
  setAudioBlob(file,file.name);
});

async function toggleRecording(){
  if(mediaRecorder&&mediaRecorder.state==="recording"){
    mediaRecorder.stop();
    return;
  }
  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia||typeof MediaRecorder==="undefined"){
    showToast("Microphone recording is not supported in this browser.","error");
    return;
  }
  try{
    mediaStream=await navigator.mediaDevices.getUserMedia({audio:true});
    const preferred=MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ?"audio/webm;codecs=opus"
      :"";
    mediaRecorder=new MediaRecorder(mediaStream,preferred?{mimeType:preferred}:undefined);
    recordingChunks=[];
    mediaRecorder.ondataavailable=event=>{
      if(event.data&&event.data.size)recordingChunks.push(event.data);
    };
    mediaRecorder.onstop=()=>{
      const type=mediaRecorder.mimeType||"audio/webm";
      const blob=new Blob(recordingChunks,{type});
      setAudioBlob(blob,"microphone-recording.webm");
      mediaStream.getTracks().forEach(track=>track.stop());
      mediaStream=null;
      $("recordAudioBtn").classList.remove("recording");
      $("recordAudioBtn").innerHTML='<span class="record-dot"></span> Record microphone';
      resetRecordingTimer();
    };
    mediaRecorder.start(250);
    recordingStartedAt=Date.now();
    updateRecordingTimer();
    recordingTimerHandle=setInterval(updateRecordingTimer,500);
    $("recordAudioBtn").classList.add("recording");
    $("recordAudioBtn").innerHTML='<span class="record-dot"></span> Stop recording';
    setAsrStatus("Recording","warn");
  }catch(error){
    showToast("Microphone access failed: "+error.message,"error");
  }
}
if($("recordAudioBtn"))$("recordAudioBtn").addEventListener("click",toggleRecording);
if($("clearAudioBtn"))$("clearAudioBtn").addEventListener("click",clearAudio);

if($("transcribeBtn"))$("transcribeBtn").addEventListener("click",async()=>{
  if(!selectedAudioBlob){
    showToast("Upload or record audio first.","error");
    return;
  }
  const button=$("transcribeBtn");
  setButtonLoading(button,true);
  setAsrStatus("Transcribing","warn");
  if($("asrMeta"))$("asrMeta").textContent="Sending audio to the official NCAIR ASR runtime…";
  try{
    const form=new FormData();
    form.append("language",$("asrLanguage").value);
    form.append("file",selectedAudioBlob,selectedAudioName);
    const started=performance.now();
    const response=await fetch("/v1/audio/transcriptions",{method:"POST",body:form});
    const result=await readApiResponse(response);
    const latency=result.latency_ms??Math.round(performance.now()-started);
    $("asrTranscript").value=result.text||"";
    $("asrMeta").textContent=result.model+" · "+(result.provider||"EDNAi")+" · "+latency+" ms";
    $("copyTranscriptBtn").disabled=!result.text;
    $("useTranscriptBtn").disabled=!result.text;
    setAsrStatus("Transcribed","good");
    showToast("Official NCAIR transcription completed.","success");
  }catch(error){
    setAsrStatus(error.status===429?"Quota exhausted":"Failed","warn");
    $("asrMeta").textContent=error.message;
    showToast(error.message,"error");
  }finally{
    setButtonLoading(button,false);
  }
});

if($("copyTranscriptBtn"))$("copyTranscriptBtn").addEventListener("click",async()=>{
  await copyText($("asrTranscript").value);
  showToast("Transcript copied.","success");
});
if($("scoreTranscriptBtn"))$("scoreTranscriptBtn").addEventListener("click",async()=>{
  const reference=$("asrReference").value.trim();
  const hypothesis=$("asrTranscript").value.trim();
  if(!reference||!hypothesis){
    showToast("Add both a reference transcript and an ASR transcript first.","error");
    return;
  }
  setButtonLoading($("scoreTranscriptBtn"),true);
  try{
    const response=await fetch("/api/studio/speech/score",{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({reference,hypothesis})
    });
    const result=await readApiResponse(response);
    $("asrWer").textContent=(Number(result.wer)*100).toFixed(1)+"%";
    $("asrCer").textContent=(Number(result.cer)*100).toFixed(1)+"%";
    $("asrRefWords").textContent=result.reference_words;
    showToast("ASR quality metrics calculated.","success");
  }catch(error){
    showToast(error.message,"error");
  }finally{
    setButtonLoading($("scoreTranscriptBtn"),false);
  }
});

renderOnboarding();
let savedStack="python";
try{savedStack=localStorage.getItem("ednai-quickstart-stack")||"python";}catch(_){}
renderQuickstart(savedStack,false);

workspaceRestore();
refreshHeaderProfile();

try{
  const pendingPrompt=sessionStorage.getItem("ednai-pending-prompt");
  if(pendingPrompt && $("prompt")){
    $("prompt").value=pendingPrompt;
    sessionStorage.removeItem("ednai-pending-prompt");
    showToast("Session restored. Your prompt is ready to run.","success");
  }
}catch(_){}

const requestedPanel=(location.hash||"#overview").slice(1);
if(["playground","usecases","speech","evaluate","dataset","finetune","runtime","profile","overview"].includes(requestedPanel))consolePanel(requestedPanel);

window.addEventListener("hashchange",function(){
  const next=(location.hash||"#overview").slice(1);
  if(["playground","usecases","speech","evaluate","dataset","finetune","runtime","profile","overview"].includes(next)){
    consolePanel(next);
  }
});
