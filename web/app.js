const $=(id)=>document.getElementById(id);
let history=[];

const quickstartSamples={
  python:`from ednai import EDNAi

ai = EDNAi(
    base_url="https://ednai-6znf.onrender.com"
)

result = ai.generate(
    "Ka bayyana API da Hausa.",
    temperature=0.2
)

print(result.text)`,
  typescript:`import { EDNAi } from "@ednai/sdk";

const ai = new EDNAi({
  baseUrl: "https://ednai-6znf.onrender.com"
});

const result = await ai.generate(
  "Ka bayyana API da Hausa.",
  { temperature: 0.2 }
);

console.log(result.text);`,
  curl:`curl -X POST \
  https://ednai-6znf.onrender.com/v1/chat/completions \
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
  toast.textContent=message;
  toast.className="toast show "+(type||"");
  clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>{toast.className="toast";},2800);
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
    const message=(body&&body.detail)||(body&&body.error)||text.trim()||("Request failed ("+response.status+")");
    const error=new Error(message);
    error.status=response.status;
    error.retryAfter=response.headers.get("retry-after");
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
  $("messages").scrollTop=$("messages").scrollHeight;
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
      heroStatus.className="runtime-inline "+(connected?"good":"warn");
      heroStatus.querySelector("span").textContent=connected?"N-ATLaS runtime connected":"Runtime not connected";
    }
  }catch{
    $("runtimeStatus").textContent="Offline";
    $("runtimeStatus").className="status warn";
    if(heroStatus){
      heroStatus.className="runtime-inline warn";
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
    addMessage("assistant",`Runtime error: ${e.message}`);
    $("meta").textContent=e.status===429?"Free ZeroGPU quota temporarily exhausted":"Request failed";
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
  document.querySelectorAll(".console-panel").forEach(function(panel){
    panel.classList.toggle("active",panel.id==="panel-"+name);
  });
  document.querySelectorAll(".console-tab").forEach(function(tab){
    tab.classList.toggle("active",tab.dataset.panel===name);
  });
  window.history.replaceState(null,"","#"+name);
  if(name==="runtime")refreshRuntimeWorkspace();
}

document.querySelectorAll(".console-tab").forEach(function(tab){
  tab.addEventListener("click",function(){consolePanel(tab.dataset.panel);});
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
  const target=$("launchpad");
  if(target)target.scrollIntoView({behavior:"smooth",block:"center"});
}
if($("heroStartBtn"))$("heroStartBtn").addEventListener("click",scrollToLaunchpad);
if($("quickstartNavBtn"))$("quickstartNavBtn").addEventListener("click",scrollToLaunchpad);

document.querySelectorAll(".template-card").forEach(card=>{
  card.addEventListener("click",()=>{
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
  const target=document.querySelector(".template-section");
  if(target)target.scrollIntoView({behavior:"smooth",block:"center"});
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

renderOnboarding();
let savedStack="python";
try{savedStack=localStorage.getItem("ednai-quickstart-stack")||"python";}catch(_){}
renderQuickstart(savedStack,false);

workspaceRestore();
const requestedPanel=(location.hash||"#playground").slice(1);
if(["playground","evaluate","dataset","finetune","runtime","overview"].includes(requestedPanel))consolePanel(requestedPanel);
