const $=id=>document.getElementById(id);
const label=k=>k.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());
async function load(){
  try{
    const r=await fetch("/api/v1/challenge/readiness",{cache:"no-store"});
    if(!r.ok)throw new Error("Could not load readiness.");
    const d=await r.json();
    const v=d.validation||{};
    const n=Number(v.competition_eligible_voice_interactions||0);
    const target=Number(v.validation_target||50);
    $("voiceCount").textContent=n;
    $("progressBar").style.width=Math.min(100,Math.round((n/target)*100))+"%";
    $("remaining").textContent=v.validation_target_met
      ?"Minimum real-user validation target reached."
      :(v.remaining_to_target ?? (target-n))+" qualifying real voice interactions remaining.";
    $("readyLabel").textContent=d.ready?"Challenge qualification gates met":"Qualification gates still open";
    $("readyLabel").className=d.ready?"ready-yes":"ready-no";
    $("checks").innerHTML=Object.entries(d.checks||{}).map(([k,ok])=>
      '<article class="criterion '+(ok?"pass":"fail")+'"><span>'+(ok?"✓":"○")+'</span><div><strong>'+label(k)+'</strong><small>'+(ok?"Verified":"Not yet verified")+'</small></div></article>'
    ).join("");
    $("models").innerHTML=Object.entries(d.required_models||{}).map(([k,v])=>
      '<article class="criterion"><span>↗</span><div><strong>'+label(k)+'</strong><small>'+v+'</small></div></article>'
    ).join("");
  }catch(e){
    $("readyLabel").textContent="Readiness unavailable";
    $("remaining").textContent=e.message;
  }
}
load();
setInterval(load,30000);
