const $=id=>document.getElementById(id);const s={interactionId:null,recorder:null,chunks:[],sessionId:crypto.randomUUID?.()||String(Date.now()),validationConsent:false};
const base=()=>({message:$("message").value.trim(),language:$("language").value,state:$("state").value||null,disco:$("disco").value||null,session_id:s.sessionId});
const loading=x=>{$("loading").classList.toggle("hidden",!x);$("askBtn").disabled=x;$("recordBtn").disabled=x};
const esc=x=>String(x??"").replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const list=(id,a)=>$(id).innerHTML=(a||[]).map(x=>"<li>"+esc(x)+"</li>").join("");
function contact(label,value,type){if(!value)return"";let h=type==="email"?"mailto:"+value:type==="website"?value:type==="phone"?"tel:"+value.split(",")[0].replace(/\s/g,""):"";return h?'<a href="'+esc(h)+'" target="'+(type==="website"?"_blank":"_self")+'">'+label+": "+esc(value)+"</a>":"<span>"+label+": "+esc(value)+"</span>"}
function render(d){s.interactionId=d.interaction_id;$("issueType").textContent=(d.issue_type||"").replaceAll("_"," ");$("summary").textContent=d.summary;list("rights",d.rights);list("steps",d.next_steps);$("regulatorName").textContent=d.escalation.regulator_name;$("regulatorNote").textContent=d.escalation.note;$("regulatorContacts").innerHTML=contact("Email",d.escalation.email,"email")+contact("Website",d.escalation.website,"website")+contact("Phone",d.escalation.phone,"phone")+(d.escalation.address?"<span>"+esc(d.escalation.address)+"</span>":"");$("sources").innerHTML=(d.sources||[]).map(x=>'<div class="source"><a href="'+esc(x.url)+'" target="_blank" rel="noopener">'+esc(x.title)+"</a><p>"+esc(x.authority)+" · "+esc(x.updated||"")+"</p><p>"+esc(x.excerpt)+"</p></div>").join("");$("disclaimer").textContent=d.disclaimer;$("result").classList.remove("hidden");$("draftPanel").classList.add("hidden");$("result").scrollIntoView({behavior:"smooth"})}
$("askBtn").onclick=async()=>{const p=base();if(p.message.length<3)return alert("Please describe what happened.");loading(true);try{const r=await fetch("/api/v1/advice",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)});if(!r.ok)throw new Error((await r.json()).detail||"Request failed");render(await r.json())}catch(e){alert(e.message)}finally{loading(false)}};
$("recordBtn").onclick=async()=>{if(s.recorder?.state==="recording"){s.recorder.stop();return}if(!navigator.mediaDevices?.getUserMedia)return alert("Voice recording is not supported in this browser.");try{const stream=await navigator.mediaDevices.getUserMedia({audio:true});s.chunks=[];s.recorder=new MediaRecorder(stream);s.recorder.ondataavailable=e=>s.chunks.push(e.data);s.recorder.onstop=async()=>{stream.getTracks().forEach(t=>t.stop());$("recordBtn").classList.remove("recording");$("recordText").textContent="Record voice";$("recordIcon").textContent="●";await sendVoice(new Blob(s.chunks,{type:s.recorder.mimeType||"audio/webm"}))};s.recorder.start();$("recordBtn").classList.add("recording");$("recordText").textContent="Stop & analyse";$("recordIcon").textContent="■"}catch(e){alert("Microphone permission is needed.")}};
async function sendVoice(blob){loading(true);try{const f=new FormData();s.validationConsent=$("validationConsent").checked;f.append("audio",blob,"complaint.webm");f.append("language",$("language").value);if($("state").value)f.append("state",$("state").value);if($("disco").value)f.append("disco",$("disco").value);f.append("session_id",s.sessionId);f.append("validation_consent",String(s.validationConsent));const r=await fetch("/api/v1/voice/advice",{method:"POST",body:f});if(!r.ok)throw new Error((await r.json()).detail||"Voice request failed");const d=await r.json();const p=d.summary.split("\n\n");if(p[0].startsWith("Transcript:")){$("message").value=p[0].replace("Transcript:","").trim();d.summary=p.slice(1).join("\n\n")}render(d)}catch(e){alert(e.message)}finally{loading(false)}}
$("draftBtn").onclick=async()=>{const p={...base(),complainant_name:null,phone:null,email:null,address:null,desired_resolution:null};const r=await fetch("/api/v1/complaint",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)});if(!r.ok)return alert("Could not generate draft");const d=await r.json();$("draftSubject").textContent=d.subject;$("draftBody").textContent=d.body;list("draftChecklist",d.checklist);$("draftPanel").classList.remove("hidden")};
$("copyDraft").onclick=async()=>{await navigator.clipboard.writeText($("draftSubject").textContent+"\n\n"+$("draftBody").textContent);$("copyDraft").textContent="Copied";setTimeout(()=>$("copyDraft").textContent="Copy",1200)};
$("newBtn").onclick=()=>{$("result").classList.add("hidden");$("message").value="";window.scrollTo({top:0,behavior:"smooth"})};
document.querySelectorAll("[data-helpful]").forEach(b=>b.onclick=async()=>{if(!s.interactionId)return;const r=await fetch("/api/v1/feedback",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({interaction_id:s.interactionId,helpful:b.dataset.helpful==="true",understood_language:true,resolved_or_actionable:b.dataset.helpful==="true",consent_to_validation:s.validationConsent})});$("feedbackStatus").textContent=r.ok?"Thank you — validation response recorded.":"Could not record feedback."});

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
  }catch(_){
    $("modelStatus").textContent="Model status unavailable";
  }
}
refreshReadiness();
