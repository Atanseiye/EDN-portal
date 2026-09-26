const $=(id)=>document.getElementById(id);
let history=[];

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
  try{
    const r=await fetch("/health",{cache:"no-store"});
    const h=await r.json();
    $("runtimeStatus").textContent=h.direct_natlas_integration?"N-ATLaS connected":"Runtime not connected";
    $("runtimeStatus").className="status "+(h.direct_natlas_integration?"good":"warn");
  }catch{
    $("runtimeStatus").textContent="Offline";
    $("runtimeStatus").className="status warn";
  }
}
async function runPrompt(){
  const prompt=$("prompt").value.trim();
  if(!prompt)return;
  addMessage("user",prompt);
  history.push({role:"user",content:prompt});
  $("prompt").value="";
  $("meta").textContent="Running N-ATLaS…";
  $("sendBtn").disabled=true;
  $("runBtn").disabled=true;
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
        model:"NCAIR1/N-ATLaS",messages,
        temperature:Number($("temperature").value),
        max_tokens:Number($("maxTokens").value),
        json_mode:$("jsonMode").checked
      })
    });
    const body=await r.json();
    if(!r.ok)throw new Error(body.detail||"Request failed");
    addMessage("assistant",body.text);
    history.push({role:"assistant",content:body.text});
    const latency=body.latency_ms??Math.round(performance.now()-started);
    $("meta").textContent=\`\${body.provider||"EDNAi"} · \${latency} ms · \${body.model}\`;
  }catch(e){
    addMessage("assistant",\`Runtime error: \${e.message}\`);
    $("meta").textContent="Request failed";
  }finally{
    $("sendBtn").disabled=false;
    $("runBtn").disabled=false;
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
  catch(error){alert(error.message);return;}
  $("runEvalBtn").disabled=true;
  $("evalStatus").textContent="Running";
  try{
    const response=await fetch("/api/studio/evaluate",{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({cases:cases,temperature:0,max_tokens:512})
    });
    const report=await response.json();
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
    alert(error.message);
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
    const report=await response.json();
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
    alert(error.message);
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
    const plan=await response.json();
    if(!response.ok)throw new Error(plan.detail||"Could not generate plan");
    $("ftMethod").textContent=plan.method;
    $("ftEffectiveBatch").textContent=plan.effective_batch_size;
    $("ftSteps").textContent=plan.estimated_optimizer_steps;
    $("ftCommand").textContent=plan.command;
    $("ftWarnings").innerHTML=plan.warnings.map(function(warning){
      return "<div><strong>!</strong><span>"+warning+"</span></div>";
    }).join("");
  }catch(error){alert(error.message);}
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
    const result=await response.json();
    if(!response.ok)throw new Error(result.detail||"Probe failed");
    $("runtimeProbe").textContent=result.provenance_verified?"Verified":"Unverified";
  }catch(error){
    $("runtimeProbe").textContent="Unavailable";
    alert(error.message);
  }
});

workspaceRestore();
const requestedPanel=(location.hash||"#playground").slice(1);
if(["playground","evaluate","dataset","finetune","runtime","overview"].includes(requestedPanel))consolePanel(requestedPanel);
