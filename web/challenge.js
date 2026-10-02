const $=(id)=>document.getElementById(id);
function nice(k){return k.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());}

let feedbackRevision=0;

function renderValidation(validation){
  const submitted=validation.unique_external_beta_submissions??0;
  const target=validation.beta_target??2;
  $("betaCount").textContent=submitted;
  $("betaReviewStatus").textContent=submitted>=target
    ? `${submitted} / ${target} submitted · requirement met`
    : `${submitted} / ${target} submitted · ${Math.max(0,target-submitted)} more needed`;
}

async function refresh(){
  const revision=feedbackRevision;
  try{
    const r=await fetch("/api/challenge/readiness",{cache:"no-store"});
    if(!r.ok)throw new Error("Readiness unavailable");
    const d=await r.json();
    if(revision!==feedbackRevision)return;
    $("readyLabel").textContent=d.ready?"Submission gates met":"Build/validation in progress";
    $("readyLabel").className=d.ready?"ready-yes":"ready-no";
    renderValidation(d.validation);
    $("checks").innerHTML=Object.entries(d.checks).map(([k,v]) =>
      '<article class="criterion '+(v?'pass':'fail')+'"><span>'+(v?'✓':'○')+'</span><div><strong>'+nice(k)+'</strong><small>'+(v?'Verified':'Not yet verified')+'</small></div></article>'
    ).join("");
  }catch(e){
    if(revision!==feedbackRevision)return;
    $("readyLabel").textContent="Readiness unavailable";
    if($("betaCount").textContent==="—")$("betaReviewStatus").textContent="Feedback count unavailable; reload to retry.";
  }
}

$("feedbackForm").addEventListener("submit",async(e)=>{
  e.preventDefault();
  const features=[...document.querySelectorAll('input[name="feature"]:checked')].map(x=>x.value);
  if(!features.length){$("formStatus").textContent="Select at least one feature you actually tested.";return;}
  if($("feedbackSubmit").disabled)return;
  $("feedbackSubmit").disabled=true;
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
    feedbackRevision++;
    renderValidation(body.validation);
    $("formStatus").textContent="Feedback recorded. The tester count is updated; repeat submissions from the same tester count once. Thank you.";
    $("feedbackForm").reset();
    void refresh();
  }catch(err){$("formStatus").textContent=err.message;}
  finally{$("feedbackSubmit").disabled=false;}
});
refresh();
