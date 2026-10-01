const $=(id)=>document.getElementById(id);

function docsInitials(account){
  if(!account)return "P";
  const source=(account.display_name||account.email||"Profile").trim();
  if(source.includes(" ")){
    return source.split(/\s+/).slice(0,2).map(part=>part[0]||"").join("").toUpperCase();
  }
  return source.slice(0,2).toUpperCase();
}

function docsRenderProfile(account){
  if(!$("docsProfileAvatar"))return;
  $("docsProfileAvatar").textContent=docsInitials(account);
  $("docsProfileName").textContent=account?(account.display_name||"Developer account"):"Developer account";
  $("docsProfileEmail").textContent=account?account.email:"Sign in to manage your account";
  $("docsProfileSignIn").classList.toggle("hidden",Boolean(account));
  $("docsProfileLogout").classList.toggle("hidden",!account);
}

async function docsFetchProfile(){
  try{
    const response=await fetch("/api/developer/me",{credentials:"same-origin"});
    if(response.status===401){docsRenderProfile(null);return;}
    if(!response.ok)throw new Error("Unable to load account");
    const data=await response.json();
    docsRenderProfile(data.account);
  }catch(_){
    docsRenderProfile(null);
  }
}

function docsCloseProfileMenu(){
  if(!$("docsProfileMenu")||!$("docsProfileMenuBtn"))return;
  $("docsProfileMenu").classList.add("hidden");
  $("docsProfileMenuBtn").setAttribute("aria-expanded","false");
}

function docsToggleProfileMenu(){
  if(!$("docsProfileMenu")||!$("docsProfileMenuBtn"))return;
  const opening=$("docsProfileMenu").classList.contains("hidden");
  $("docsProfileMenu").classList.toggle("hidden",!opening);
  $("docsProfileMenuBtn").setAttribute("aria-expanded",String(opening));
}

if($("docsProfileMenuBtn"))$("docsProfileMenuBtn").addEventListener("click",event=>{
  event.stopPropagation();
  docsToggleProfileMenu();
});
if($("docsProfileMenu"))$("docsProfileMenu").addEventListener("click",event=>event.stopPropagation());
document.addEventListener("click",docsCloseProfileMenu);
document.addEventListener("keydown",event=>{if(event.key==="Escape")docsCloseProfileMenu();});

document.querySelectorAll("[data-docs-profile-target]").forEach(button=>{
  button.addEventListener("click",()=>{
    docsCloseProfileMenu();
    const target=button.dataset.docsProfileTarget;
    const destination=target==="keys"?"keys":target==="usage"?"usage":"account";
    try{sessionStorage.setItem("ednai-profile-target",destination);}catch(_){}
    window.location.href="/#profile";
  });
});

if($("docsProfileLogout"))$("docsProfileLogout").addEventListener("click",async()=>{
  try{await fetch("/api/developer/logout",{method:"POST",credentials:"same-origin"});}catch(_){}
  docsRenderProfile(null);
  docsCloseProfileMenu();
  window.location.href="/";
});

document.querySelectorAll(".docs-sidebar a").forEach(link=>{
  link.addEventListener("click",()=>{
    document.querySelectorAll(".docs-sidebar a").forEach(item=>item.classList.remove("active"));
    link.classList.add("active");
  });
});

if("IntersectionObserver" in window){
  const links=[...document.querySelectorAll(".docs-sidebar a[href^='#']")];
  const map=new Map(links.map(link=>[link.getAttribute("href").slice(1),link]));
  const observer=new IntersectionObserver(entries=>{
    const visible=entries.filter(entry=>entry.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];
    if(!visible)return;
    links.forEach(link=>link.classList.remove("active"));
    const link=map.get(visible.target.id);
    if(link)link.classList.add("active");
  },{rootMargin:"-18% 0px -68% 0px",threshold:0});
  map.forEach((_,id)=>{
    const section=document.getElementById(id);
    if(section)observer.observe(section);
  });
}

docsFetchProfile();
