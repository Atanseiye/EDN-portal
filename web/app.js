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
