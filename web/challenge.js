const $=(id)=>document.getElementById(id);
function nice(k){return k.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());}

async function refresh(){
  try{
    const r=await fetch("/api/challenge/readiness",{cache:"no-store"});
    const d=await r.json();
    $("readyLabel").textContent=d.ready?"Submission gates met":"Build/validation in progress";
    $("readyLabel").className=d.ready?"ready-yes":"ready-no";
    $("betaCount").textContent=d.validation.unique_external_beta_testers||0;
    $("checks").innerHTML=Object.entries(d.checks).map(([k,v]) =>
      '<article class="criterion '+(v?'pass':'fail')+'"><span>'+(v?'✓':'○')+'</span><div><strong>'+nice(k)+'</strong><small>'+(v?'Verified':'Not yet verified')+'</small></div></article>'
    ).join("");
  }catch(e){
    $("readyLabel").textContent="Readiness unavailable";
  }
}

$("feedbackForm").addEventListener("submit",async(e)=>{
  e.preventDefault();
  const features=[...document.querySelectorAll('input[name="feature"]:checked')].map(x=>x.value);
  if(!features.length){$("formStatus").textContent="Select at least one feature you actually tested.";return;}
  $("formStatus").textContent="Submitting…";
  const payload={
    tester_identity:$("testerIdentity").value,
    display_name:$("displayName").value||null,
    affiliation:$("affiliation").value||null,
    role:$("role").value||null,
    features,
    rating:Number($("rating").value),
    useful:$("useful").value==="true",
    blocker:$("blocker").value||null,
    notes:$("notes").value||null,
    external_tester:$("externalTester").checked,
    consent:$("consent").checked
  };
  try{
    const r=await fetch("/api/beta/feedback",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(payload)});
    const body=await r.json();
    if(!r.ok)throw new Error(body.detail||"Submission failed");
    $("formStatus").textContent="Feedback recorded and queued for external-tester verification. Thank you.";
    $("feedbackForm").reset();
    await refresh();
  }catch(err){$("formStatus").textContent=err.message;}
});
refresh();
