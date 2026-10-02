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

function openProfile(){
  const params=new URLSearchParams(window.location.search);
  const requested=params.get("return");
  const safeReturn=requested&&requested.startsWith("/")&&!requested.startsWith("//")
    ? requested
    : "/#profile";
  window.location.href=safeReturn;
}

async function redirectIfSignedIn(){
  try{
    await api("/api/developer/me");
    openProfile();
  }catch(error){
    if(error.status!==401)showToast(error.message,"error");
  }
}

function showLoginFlow(){
  $("registerPanel").classList.add("hidden");
  $("loginFlow").classList.remove("hidden");
  $("loginEmail").focus();
}

function showRegisterFlow(){
  $("loginFlow").classList.add("hidden");
  $("registerPanel").classList.remove("hidden");
  const email=$("loginEmail").value.trim();
  if(email && !$("registerEmail").value)$("registerEmail").value=email;
  $("registerEmail").focus();
}

$("openRegisterBtn").addEventListener("click",showRegisterFlow);
$("backToLoginBtn").addEventListener("click",showLoginFlow);

$("loginForm").addEventListener("submit",async event=>{
  event.preventDefault();
  $("loginStatus").textContent="Signing in…";
  try{
    await api("/api/developer/login",{
      method:"POST",
      body:JSON.stringify({
        email:$("loginEmail").value,
        password:$("loginPassword").value
      })
    });
    $("loginStatus").textContent="";
    showToast("Signed in. Opening Profile / Settings…","success");
    setTimeout(openProfile,250);
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
    showToast("Account created. Opening Profile / Settings…","success");
    setTimeout(openProfile,250);
  }catch(error){
    $("registerStatus").textContent=error.message;
  }
});

$("demoRequestForm").addEventListener("submit",async event=>{
  event.preventDefault();
  const button=event.currentTarget.querySelector("button[type=submit]");
  const status=$("demoRequestStatus");
  const email=$("demoRequestEmail").value.trim();
  button.disabled=true;
  status.textContent="Requesting demo access…";
  try{
    const result=await api("/api/developer/demo-request",{
      method:"POST",
      body:JSON.stringify({email})
    });
    status.textContent=result.message||"Demo access has been sent to your email.";
    event.currentTarget.reset();
    showToast("Demo request received.","success");
  }catch(error){
    status.textContent=error.message;
  }finally{
    button.disabled=false;
  }
});

redirectIfSignedIn();
