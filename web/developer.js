const $=(id)=>document.getElementById(id);

function showToast(message,state){
  const toast=$("toast");
  if(!toast)return;
  toast.textContent=message;
  toast.className="toast show "+(state||"");
  clearTimeout(showToast.timer);
  showToast.timer=setTimeout(()=>{toast.className="toast";},3200);
}

async function api(path,options={}){
  const response=await fetch(path,{
    credentials:"same-origin",
    ...options,
    headers:{
      ...(options.body?{"content-type":"application/json"}:{}),
      ...(options.headers||{})
    }
  });
  let body={};
  try{body=await response.json();}catch(_){}
  if(!response.ok){
    const detail=typeof body.detail==="string"?body.detail:JSON.stringify(body.detail||body);
    const error=new Error(detail||("HTTP "+response.status));
    error.status=response.status;
    throw error;
  }
  return body;
}

function money(value){
  return "$"+Number(value||0).toFixed(6).replace(/0+$/,"").replace(/\.$/,".00");
}

function scopeLabel(scope){
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

let state=null;
let newestKey="";

function renderDashboard(data){
  state=data;
  $("authView").classList.add("hidden");
  $("dashboardView").classList.remove("hidden");

  const account=data.account;
  $("developerGreeting").textContent=account.display_name||"Developer account";
  $("developerEmail").textContent=account.email+(account.is_demo?" · demo account":"");
  $("developerBalance").textContent=money(data.usage.balance_usd);
  $("developerTokens").textContent=Number(data.usage.total_tokens||0).toLocaleString();
  $("developerCost").textContent=money(data.usage.total_cost_usd);

  const active=(data.api_keys||[]).filter(key=>!key.revoked_at);
  $("developerKeyCount").textContent=active.length;

  $("inputRate").textContent="$"+Number(data.pricing.input_usd_per_1m_tokens).toFixed(4);
  $("outputRate").textContent="$"+Number(data.pricing.output_usd_per_1m_tokens).toFixed(4);

  renderScopes(data.available_scopes||[]);
  renderKeys(data.api_keys||[]);
  renderUsage(data.usage.events||[]);

  $("developerCurl").textContent=`curl -X POST ${location.origin}/v1/generate \\\n  -H "Authorization: Bearer $EDNAI_API_KEY" \\\n  -H "Content-Type: application/json" \\\n  -d '{"model":"NCAIR1/N-ATLaS","messages":[{"role":"user","content":"Explain APIs simply."}]}'`;
}

function renderScopes(scopes){
  const root=$("scopeOptions");
  root.innerHTML="";
  scopes.forEach((scope,index)=>{
    const label=document.createElement("label");
    label.className="scope-option";
    const input=document.createElement("input");
    input.type="checkbox";
    input.value=scope;
    input.checked=["inference.generate","inference.chat","usecases.run","speech.transcribe"].includes(scope);
    const text=document.createElement("span");
    text.innerHTML="<strong>"+scopeLabel(scope)+"</strong><small>"+scope+"</small>";
    label.append(input,text);
    root.appendChild(label);
  });
}

function renderKeys(keys){
  const root=$("apiKeyList");
  root.innerHTML="";
  if(!keys.length){
    root.innerHTML='<p class="hint">No API keys yet.</p>';
    return;
  }
  keys.forEach(key=>{
    const row=document.createElement("div");
    row.className="developer-list-row"+(key.revoked_at?" revoked":"");

    const info=document.createElement("div");
    const title=document.createElement("strong");
    title.textContent=key.name;
    const meta=document.createElement("small");
    meta.textContent=key.prefix+"… · "+(key.scopes||[]).map(scopeLabel).join(", ");
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
      revoke.addEventListener("click",()=>revokeKey(key.id));
      side.appendChild(revoke);
    }

    row.append(info,side);
    root.appendChild(row);
  });
}

function renderUsage(events){
  const body=$("usageRows");
  body.innerHTML="";
  if(!events.length){
    body.innerHTML='<tr><td colspan="7">No metered requests yet.</td></tr>';
    return;
  }
  events.forEach(event=>{
    const tr=document.createElement("tr");
    const values=[
      event.feature,
      Number(event.prompt_tokens).toLocaleString(),
      Number(event.completion_tokens).toLocaleString(),
      Number(event.total_tokens).toLocaleString(),
      event.measurement,
      money(Number(event.cost_microusd)/1_000_000),
      new Date(event.created_at).toLocaleString()
    ];
    values.forEach(value=>{
      const td=document.createElement("td");
      td.textContent=value;
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

async function loadAccount(){
  try{
    const data=await api("/api/developer/me");
    renderDashboard(data);
  }catch(error){
    if(error.status===401){
      $("dashboardView").classList.add("hidden");
      $("authView").classList.remove("hidden");
      return;
    }
    showToast(error.message,"error");
  }
}

async function revokeKey(id){
  if(!confirm("Revoke this API key? Applications using it will stop working."))return;
  try{
    await api("/api/developer/keys/"+encodeURIComponent(id),{method:"DELETE"});
    showToast("API key revoked.","success");
    await loadAccount();
  }catch(error){
    showToast(error.message,"error");
  }
}

$("fillDemoBtn").addEventListener("click",()=>{
  $("loginEmail").value="demo@edn.com";
  $("loginPassword").value="12345";
  $("loginEmail").focus();
});

$("loginForm").addEventListener("submit",async event=>{
  event.preventDefault();
  $("loginStatus").textContent="Signing in…";
  try{
    const data=await api("/api/developer/login",{
      method:"POST",
      body:JSON.stringify({
        email:$("loginEmail").value,
        password:$("loginPassword").value
      })
    });
    $("loginStatus").textContent="";
    showToast("Signed in.","success");
    await loadAccount();
  }catch(error){
    $("loginStatus").textContent=error.message;
  }
});

$("registerForm").addEventListener("submit",async event=>{
  event.preventDefault();
  $("registerStatus").textContent="Creating account…";
  try{
    await api("/api/developer/register",{
      method:"POST",
      body:JSON.stringify({
        display_name:$("registerName").value,
        email:$("registerEmail").value,
        password:$("registerPassword").value
      })
    });
    $("registerStatus").textContent="";
    showToast("Developer account created.","success");
    await loadAccount();
  }catch(error){
    $("registerStatus").textContent=error.message;
  }
});

$("createApiKeyBtn").addEventListener("click",async()=>{
  const scopes=[...document.querySelectorAll("#scopeOptions input:checked")].map(x=>x.value);
  if(!scopes.length){
    showToast("Select at least one permission.","error");
    return;
  }
  try{
    const created=await api("/api/developer/keys",{
      method:"POST",
      body:JSON.stringify({
        name:$("apiKeyName").value||"API key",
        scopes
      })
    });
    newestKey=created.key;
    $("newApiKeySecret").textContent=created.key;
    $("newKeyReveal").classList.remove("hidden");
    showToast("API key created. Copy it now.","success");
    await loadAccount();
  }catch(error){
    showToast(error.message,"error");
  }
});

$("copyNewApiKeyBtn").addEventListener("click",async()=>{
  if(!newestKey)return;
  await navigator.clipboard.writeText(newestKey);
  showToast("API key copied.","success");
});

$("copyDeveloperCurlBtn").addEventListener("click",async()=>{
  await navigator.clipboard.writeText($("developerCurl").textContent);
  showToast("cURL example copied.","success");
});

$("refreshDeveloperBtn").addEventListener("click",loadAccount);
$("logoutDeveloperBtn").addEventListener("click",async()=>{
  try{await api("/api/developer/logout",{method:"POST"});}catch(_){}
  state=null;
  newestKey="";
  $("newKeyReveal").classList.add("hidden");
  $("dashboardView").classList.add("hidden");
  $("authView").classList.remove("hidden");
  showToast("Signed out.","success");
});

loadAccount();
