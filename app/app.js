const $ = (s) => document.querySelector(s);

function actionClass(action){
  return action.toLowerCase().replace(" ","");
}
function changeClass(v){ return v > 0 ? "up" : v < 0 ? "down" : "neutral"; }

function renderMarket(){
  $("#marketGrid").innerHTML = assets.slice(0,4).map(a => `
    <div class="market-card">
      <div class="row"><span class="ticker">${a.ticker}</span><span class="${changeClass(a.change)}">${a.change > 0 ? "+" : ""}${Number(a.change || 0).toFixed(2)}%</span></div>
      <div class="price">${a.price}</div>
      <div class="muted">${a.name}</div>
    </div>`).join("");
}

function renderActionable(){
  const actionable = signals.filter(s => s.action === "BUY" || s.action === "SELL")
    .sort((a,b) => (Number(b.confidence)||0) - (Number(a.confidence)||0));
  const title = $("#actionableTitle");
  const summary = $("#actionableSummary");
  const list = $("#actionableList");
  if(!actionable.length){
    title.textContent = "No actionable signal right now";
    summary.textContent = "The latest evidence does not meet the app's threshold for a directional BUY or SELL signal. HOLD / NO SIGNAL is shown instead.";
    list.innerHTML = `<div class="actionable-empty">Waiting for a sufficiently fresh catalyst, verified evidence, and market confirmation.</div>`;
    return;
  }
  title.textContent = `${actionable.length} actionable signal${actionable.length === 1 ? "" : "s"} detected`;
  summary.textContent = "These are the current BUY / SELL signals with the strongest confidence. Open a signal below to review the evidence and risks before acting.";
  list.innerHTML = actionable.slice(0,3).map(s => `
    <button class="actionable-item" data-signal-index="${signals.indexOf(s)}">
      <span class="actionable-symbol">${s.ticker}</span>
      <span class="badge ${actionClass(s.action)}">${s.action}</span>
      <span class="actionable-headline">${s.headline}</span>
      <span class="actionable-confidence">${s.confidence}% confidence</span>
    </button>`).join("");
  document.querySelectorAll('.actionable-item').forEach(el => el.onclick=()=>openDetail(Number(el.dataset.signalIndex)));
}

function renderSignals(filter="all"){
  const rows = filter === "all" ? signals : signals.filter(s => s.action === filter);
  $("#signals").innerHTML = rows.map((s,i) => `
    <article class="signal-card" data-index="${signals.indexOf(s)}">
      <div class="signal-top">
        <div><div class="asset">${s.ticker}</div><div class="muted">${s.freshness}</div></div>
        <span class="badge ${actionClass(s.action)}">${s.action}</span>
      </div>
      <div class="headline">${s.headline}</div>
      <div class="muted">${s.summary}</div>
      <div class="metrics">
        <div class="metric"><label>Signal</label><strong>${s.score}/100</strong></div>
        <div class="metric"><label>Confidence</label><strong>${s.confidence}%</strong></div>
        <div class="metric"><label>Reaction</label><strong>${s.reaction}</strong></div>
      </div>
      <div class="meter"><span style="width:${s.score}%"></span></div>
      <div class="scoreline"><span>Evidence strength</span><span>${s.primary_verified ? "✓ Primary verified" : "Secondary / discovery source"}</span></div>
    </article>`).join("");

  document.querySelectorAll(".signal-card").forEach(c => c.onclick = () => openDetail(Number(c.dataset.index)));
}

function renderTable(){
  $("#assetTable").innerHTML = assets.map(a => {
    const s = signals.find(x => x.ticker === a.ticker);
    return `<tr>
      <td><strong>${a.ticker}</strong><br><span class="muted">${a.name}</span></td>
      <td>${s ? `<span class="mini-badge ${actionClass(s.action)}">${s.action}</span>` : `<span class="mini-badge nosignal">NO SIGNAL</span>`}</td>
      <td>${s ? s.score : "—"}</td>
      <td>${s ? s.confidence + "%" : "—"}</td>
      <td class="${changeClass(a.change)}">${a.change > 0 ? "+" : ""}${a.change}%</td>
      <td class="muted">${s ? s.headline : "No material event detected"}</td>
    </tr>`;
  }).join("");
}

function openDetail(i){
  const s = signals[i];
  $("#detailTitle").textContent = `${s.ticker} — ${s.action}`;
  $("#detailBody").innerHTML = `
    <div class="metrics">
      <div class="metric"><label>Signal score</label><strong>${s.score}/100</strong></div>
      <div class="metric"><label>Confidence</label><strong>${s.confidence}%</strong></div>
      <div class="metric"><label>Freshness</label><strong>${s.freshness}</strong></div>
    </div>
    <div class="dialog-section">
      <h3>What changed?</h3>
      <p class="muted">${s.summary}</p>
      <div class="source">${s.source}${s.primary_verified ? " · ✓ Primary source verified" : " · Secondary/discovery source"}</div>
    </div>
    <div class="dialog-section">
      <h3>Score breakdown</h3>
      ${s.factors.map(([k,v]) => `<div class="reason"><span>${k}</span><b>${v}</b></div>`).join("")}
    </div>
    <div class="dialog-section">
      <h3>Evidence</h3>
      ${s.evidence.map(e => `<div class="reason"><span>${e}</span><b>✓</b></div>`).join("")}
    </div>
    <div class="dialog-section">
      <h3>What could invalidate the signal?</h3>
      <div class="risk">${s.risks}</div>
    </div>`;
  $("#detailDialog").showModal();
}

$("#closeDialog").onclick = () => $("#detailDialog").close();
$("#filter").onchange = e => renderSignals(e.target.value);
renderMarket();
renderActionable();
renderSignals();
renderTable();
$("#signalCount").textContent = signals.filter(s => s.action !== "HOLD").length;

let deferredInstallPrompt = null;
const installBtn = $("#installBtn");
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
  installBtn.hidden = false;
});
installBtn.onclick = async () => {
  if (!deferredInstallPrompt) return;
  deferredInstallPrompt.prompt();
  await deferredInstallPrompt.userChoice;
  deferredInstallPrompt = null;
  installBtn.hidden = true;
};
window.addEventListener("appinstalled", () => { installBtn.hidden = true; });

function applyLiveData(d){
  if(d.market?.length){
    assets.length = 0;
    d.market.forEach(a => assets.push({
      ticker:a.symbol, name:a.name,
      price:a.price == null ? "—" : "$"+Number(a.price).toLocaleString(undefined,{maximumFractionDigits:6}),
      change:Number(a.change_24h || 0)
    }));
  }
  if(d.signals?.length){
    signals.length = 0;
    d.signals.forEach(s => signals.push({
      ticker:s.symbol, action:s.action, score:s.score, confidence:s.confidence,
      headline:s.headline,
      freshness:s.freshness_minutes == null ? "—" : `${s.freshness_minutes} minutes ago`,
      reaction:s.market_reaction == null ? "—" : `${s.market_reaction > 0 ? "+" : ""}${Number(s.market_reaction).toFixed(2)}%`,
      volume:"—", source:s.evidence?.[0] || "Live API",
      primary_verified:!!s.primary_verified,
      summary:"Generated from currently available market and news evidence.",
      factors:(s.reasons||[]).map(x=>[x.factor,x.value]),
      risks:s.risks||[], evidence:s.evidence||[]
    }));
  }
  renderMarket(); renderActionable(); renderSignals($("#filter").value); renderTable();
  $("#signalCount").textContent = signals.filter(s => s.action === "BUY" || s.action === "SELL").length;
  const ts = d.fetched_at ? new Date(d.fetched_at) : new Date();
  if(!Number.isNaN(ts.getTime())) $("#marketUpdated").textContent = `Market data updated ${ts.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"})}`;
}

async function requestLive(endpoint="/dashboard", options={}){
  const api=(window.CRYPTOSIGNAL_API || "/api");
  const {timeoutMs=30000,...fetchOptions}=options;
  const doFetch=()=>{
    const token=localStorage.getItem("cs_app_token")||"";
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),timeoutMs);
    return fetch(api+endpoint,{cache:"no-store",...fetchOptions,signal:controller.signal,headers:{"Accept":"application/json",...(token?{"X-App-Token":token}:{}),...(fetchOptions.headers||{})}}).finally(()=>clearTimeout(timer));
  };
  let r=await doFetch();
  if(r.status===401){
    const password=prompt("CryptoSignal AI password:");
    if(password===null) throw new Error("Login cancelled.");
    const lr=await fetch(api+"/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password})});
    let ld=null; try{ld=await lr.json();}catch{}
    if(!lr.ok) throw new Error(ld?.detail||"Login failed");
    localStorage.setItem("cs_app_token",ld.token||"");
    r=await doFetch();
  }
  let payload=null; try{payload=await r.json();}catch{}
  if(!r.ok) throw new Error(payload?.detail||`Server returned HTTP ${r.status}`);
  return payload;
}

async function bootLive(){
  try{
    // Load fast market data first so the mobile dashboard does not wait for news scanning.
    const m = await requestLive("/market");
    applyLiveData({market:m.assets || []});
    document.querySelector(".status").innerHTML='<i></i> Live API';
    $("#lastScan").textContent = "Live market data loaded";
  }catch(e){
    document.querySelector(".status").innerHTML='<i style="background:#ff7777"></i> Live data unavailable';
    $("#lastScan").textContent = `Live connection failed: ${e.message}`;
  }
  // Then load the heavier intelligence dashboard without blocking the market cards.
  try{
    const d = await requestLive("/dashboard", {timeoutMs:60000});
    applyLiveData(d);
    document.querySelector(".status").innerHTML='<i></i> Live API';
    $("#lastScan").textContent = `Intelligence loaded ${new Date().toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"})}`;
  }catch(e){
    $("#lastScan").textContent = `Market live · intelligence refresh failed: ${e.message}`;
  }
}


$("#scanBtn").onclick = async () => {
  const btn = $("#scanBtn");
  const last = $("#lastScan");
  const old = btn.innerHTML;
  btn.disabled = true;
  btn.style.opacity = ".7";
  btn.innerHTML = "Scanning…";
  last.textContent = "Running full market + news + order-book scan…";
  try{
    const d = await requestLive("/scan", {method:"POST", timeoutMs:120000});
    applyLiveData(d);
    document.querySelector(".status").innerHTML='<i></i> Live API';
    last.textContent = `Full scan completed ${new Date().toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"})}`;
  }catch(e){
    document.querySelector(".status").innerHTML='<i style="background:#ff7777"></i> Scan failed';
    last.textContent = `Scan failed: ${e.message}`;
  }finally{
    btn.disabled = false;
    btn.style.opacity = "";
    btn.innerHTML = old;
  }
};

$("#actionableScan").onclick = () => $("#scanBtn").click();


bootLive();

// Fast market refresh: public exchange endpoints update independently of the heavier news scan.
let refreshBusy = false;
setInterval(async () => {
  if(document.hidden || refreshBusy) return;
  refreshBusy = true;
  try{
    const m = await requestLive("/market");
    applyLiveData({market:m.assets || []});
    document.querySelector(".status").innerHTML='<i></i> Live API';
  }catch(e){
    // Keep the last known values visible, but mark the connection as stale.
    document.querySelector(".status").innerHTML='<i style="background:#e9c76c"></i> Market reconnecting';
  }finally{ refreshBusy = false; }
}, 15000);

// Refresh the heavier intelligence layer periodically; Scan Now remains the manual full refresh.
setInterval(async () => {
  if(document.hidden || refreshBusy) return;
  refreshBusy = true;
  try{
    const d = await requestLive("/dashboard", {timeoutMs:60000});
    applyLiveData(d);
  }catch(e){}
  finally{ refreshBusy = false; }
}, 60000);

async function loadIntelligencePanels(){
  try{
    const fg=await requestLive('/fear-greed');
    $('#fearGreed').textContent=`${fg.value}/100 · ${fg.classification}`;
    $('#fearGreedText').textContent='Alternative.me Fear & Greed Index';
  }catch(e){ $('#fearGreed').textContent='Unavailable'; }
  try{
    const d=await requestLive('/providers');
    $('#providerStatus').innerHTML=Object.entries(d.providers||{}).map(([name,x])=>`<span><b>${name}</b><em class="${x.ok?'provider-ok':'provider-bad'}">${x.ok?'● online':'● unavailable'}</em></span>`).join('');
  }catch(e){ $('#providerStatus').textContent='Provider status unavailable'; }
  try{
    const d=await requestLive('/performance');
    $('#performanceHeadline').textContent=d.observed_outcomes ? `${d.observed_outcomes} signal outcomes measured` : 'Waiting for enough completed signals';
    $('#performanceText').textContent=d.observed_outcomes ? 'These are live forward outcomes from signals generated by the app—not a historical backtest.' : 'The app will automatically record 1h, 6h, 24h and 7d outcomes.';
  }catch(e){}
}

function urlBase64ToUint8Array(base64String){
  const padding='='.repeat((4-base64String.length%4)%4);
  const base64=(base64String+padding).replace(/-/g,'+').replace(/_/g,'/');
  const raw=atob(base64); return Uint8Array.from([...raw].map(c=>c.charCodeAt(0)));
}

$('#alertsBtn').onclick=async()=>{
  const status=$('#alertsStatus');
  try{
    if(!('serviceWorker' in navigator) || !('PushManager' in window)) throw new Error('This browser does not support web push.');
    const key=await requestLive('/push/public-key');
    if(!key.enabled || !key.public_key) throw new Error('Push notifications are not configured on the server yet.');
    const reg=await navigator.serviceWorker.ready;
    const permission=await Notification.requestPermission();
    if(permission!=='granted') throw new Error('Notification permission was not granted.');
    const sub=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:urlBase64ToUint8Array(key.public_key)});
    await requestLive('/push/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(sub.toJSON())});
    status.textContent='Alerts enabled on this device.';
    $('#alertsBtn').textContent='Alerts enabled';
  }catch(e){ status.textContent=e.message; }
};

loadIntelligencePanels();
