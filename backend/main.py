import asyncio
import base64, hashlib, hmac, time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc
from .config import WATCHLIST, POLL_SECONDS, DB_URL_WARNING
from .sources import fetch_market, fetch_rss, fetch_gdelt, fetch_provider_status
from .scoring import build_signal
from .db import SessionLocal, EventRecord, SignalRecord, SignalOutcome, PushSubscription
from .pipeline import persist_events, persist_market, persist_signal, update_outcomes, run_cycle
from .providers import fetch_fear_greed, fetch_github_activity
from .config import PUSH_ENABLED, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_EMAIL, APP_PASSWORD, APP_SECRET

worker_task=None

def _make_token():
    payload=str(int(time.time()+86400)).encode()
    sig=hmac.new(APP_SECRET.encode(),payload,hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload+b"."+sig).decode()

def _valid_token(token):
    if not APP_PASSWORD: return True
    try:
        raw=base64.urlsafe_b64decode(token.encode()); exp,sig=raw.split(b".",1)
        if int(exp)<int(time.time()): return False
        expected=hmac.new(APP_SECRET.encode(),exp,hashlib.sha256).digest()
        return hmac.compare_digest(sig,expected)
    except Exception: return False

def require_auth(x_app_token: str|None):
    if APP_PASSWORD and not _valid_token(x_app_token or ""): raise HTTPException(401,detail="Login required")


async def worker():
    while True:
        try: await run_cycle()
        except Exception: pass
        await asyncio.sleep(POLL_SECONDS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task
    worker_task=asyncio.create_task(worker())
    yield
    worker_task.cancel()
    try: await worker_task
    except asyncio.CancelledError: pass

app=FastAPI(title="CryptoSignal AI API",version="0.7.1",lifespan=lifespan)

@app.on_event("startup")
async def startup_notice():
    if DB_URL_WARNING:
        print(f"[CryptoSignal AI] WARNING: {DB_URL_WARNING}")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.post("/api/login")
async def login(payload: dict):
    if not APP_PASSWORD: return {"ok":True,"token":""}
    if payload.get("password") != APP_PASSWORD: raise HTTPException(401,detail="Incorrect password")
    return {"ok":True,"token":_make_token()}

@app.get("/api/health")
async def health(): return {"ok":True,"service":"cryptosignal-api","version":"0.7.1"}

@app.post("/api/scan")
async def scan(x_app_token: str|None = Header(default=None)):
    require_auth(x_app_token)
    try:
        market,signals=await run_cycle()
        return {"market":[x.model_dump(mode="json") for x in market],"signals":[x.model_dump(mode="json") for x in signals],"fetched_at":datetime.now(timezone.utc).isoformat()}
    except Exception as exc: raise HTTPException(502,detail=str(exc))



@app.get("/api/push/public-key")
async def push_public_key():
    return {"enabled": bool(PUSH_ENABLED and VAPID_PUBLIC_KEY), "public_key": VAPID_PUBLIC_KEY if PUSH_ENABLED else ""}

@app.post("/api/push/subscribe")
async def push_subscribe(payload: dict, x_app_token: str|None = Header(default=None)):
    require_auth(x_app_token)
    if not payload.get("endpoint") or not payload.get("keys",{}).get("p256dh") or not payload.get("keys",{}).get("auth"):
        raise HTTPException(400, detail="Invalid push subscription")
    db=SessionLocal()
    try:
        row=db.scalar(select(PushSubscription).where(PushSubscription.endpoint==payload["endpoint"]))
        if not row:
            row=PushSubscription(endpoint=payload["endpoint"],p256dh=payload["keys"]["p256dh"],auth=payload["keys"]["auth"]); db.add(row)
        else:
            row.p256dh=payload["keys"]["p256dh"]; row.auth=payload["keys"]["auth"]
        db.commit(); return {"ok":True}
    finally: db.close()

@app.get("/api/providers")
async def providers(x_app_token: str|None = Header(default=None)):
    require_auth(x_app_token)
    return {"providers": await fetch_provider_status()}

@app.get("/api/fear-greed")
async def fear_greed(x_app_token: str|None = Header(default=None)):
    require_auth(x_app_token)
    try: return await fetch_fear_greed()
    except Exception as exc: raise HTTPException(502, detail=f"Fear & Greed unavailable: {exc}")

@app.get("/api/developer-activity/{symbol}")
async def developer_activity(symbol:str,x_app_token: str|None = Header(default=None)):
    require_auth(x_app_token)
    symbol=symbol.upper()
    if symbol not in [v["symbol"] for v in WATCHLIST.values()]: raise HTTPException(404,detail="Symbol not in watchlist")
    try: return await fetch_github_activity(symbol) or {"repo":None,"recent_commits":0}
    except Exception as exc: raise HTTPException(502,detail=f"Developer activity unavailable: {exc}")

@app.get("/api/performance")
async def performance(x_app_token: str|None = Header(default=None)):
    require_auth(x_app_token)
    db=SessionLocal()
    try:
        rows=db.scalars(select(SignalOutcome).where(SignalOutcome.status=="observed")).all()
        result={}
        for r in rows:
            key=f"{r.symbol}:{r.horizon}"
            result.setdefault(key,{"symbol":r.symbol,"horizon":r.horizon,"n":0,"wins":0,"avg_return_pct":0.0,"returns":[]})
            x=result[key]; x["n"]+=1; x["wins"]+=1 if (r.return_pct or 0)>0 else 0; x["returns"].append(r.return_pct or 0)
        for x in result.values(): x["avg_return_pct"]=round(sum(x["returns"])/len(x["returns"]),3) if x["returns"] else 0; x["win_rate_pct"]=round(x["wins"]/x["n"]*100,1) if x["n"] else 0; del x["returns"]
        return {"observed_outcomes":sum(x["n"] for x in result.values()),"by_symbol_horizon":list(result.values()),"note":"Performance is based on signals generated after deployment; it is not a historical backtest."}
    finally: db.close()

@app.get("/api/market")
async def market(x_app_token: str|None = Header(default=None)):
    require_auth(x_app_token)
    try: return {"assets":[x.model_dump() for x in await fetch_market()],"fetched_at":datetime.now(timezone.utc).isoformat()}
    except Exception as exc: raise HTTPException(502,detail=f"Market provider unavailable: {exc}")

@app.get("/api/news/{symbol}")
async def news(symbol:str, x_app_token: str|None = Header(default=None)):
    require_auth(x_app_token)
    symbol=symbol.upper()
    if symbol not in [v["symbol"] for v in WATCHLIST.values()]: raise HTTPException(404,detail="Symbol not in watchlist")
    try:
        events=await fetch_gdelt(symbol); persist_events(events)
        return {"events":[x.model_dump(mode="json") for x in events]}
    except Exception as exc: raise HTTPException(502,detail=str(exc))

@app.get("/api/dashboard")
async def dashboard(x_app_token: str|None = Header(default=None)):
    require_auth(x_app_token)
    market=await fetch_market(); persist_market(market); rss=await fetch_rss(); persist_events(rss)
    signals=[]
    for asset in market:
        events=[e for e in rss if e.asset_symbol==asset.symbol]
        if not events:
            try:
                events=await fetch_gdelt(asset.symbol); persist_events(events)
            except Exception: events=[]
        signals.append(build_signal(asset,events).model_dump(mode="json"))
    return {"market":[x.model_dump(mode="json") for x in market],"signals":signals}

@app.get("/api/events")
async def events(symbol:str|None=None,limit:int=50,x_app_token: str|None = Header(default=None)):
    require_auth(x_app_token)
    db=SessionLocal()
    try:
        q=select(EventRecord).order_by(desc(EventRecord.first_seen_at)).limit(min(limit,200))
        if symbol: q=select(EventRecord).where(EventRecord.asset_symbol==symbol.upper()).order_by(desc(EventRecord.first_seen_at)).limit(min(limit,200))
        rows=db.scalars(q).all()
        return {"events":[{"id":r.id,"event_id":r.event_id,"canonical_event_id":r.canonical_event_id,"symbol":r.asset_symbol,"title":r.title,"url":r.url,"source":r.source,"published_at":r.published_at,"first_seen_at":r.first_seen_at,"primary_verified":r.primary_verified,"event_type":r.event_type,"sentiment":r.sentiment,"impact":r.impact} for r in rows]}
    finally: db.close()

@app.get("/api/outcomes")
async def outcomes(symbol:str|None=None,limit:int=100,x_app_token: str|None = Header(default=None)):
    require_auth(x_app_token)
    db=SessionLocal()
    try:
        q=select(SignalOutcome).order_by(desc(SignalOutcome.target_at)).limit(min(limit,500))
        if symbol: q=select(SignalOutcome).where(SignalOutcome.symbol==symbol.upper()).order_by(desc(SignalOutcome.target_at)).limit(min(limit,500))
        rows=db.scalars(q).all()
        return {"outcomes":[{"signal_id":r.signal_id,"symbol":r.symbol,"horizon":r.horizon,"target_at":r.target_at,"return_pct":r.return_pct,"status":r.status,"observed_at":r.observed_at} for r in rows]}
    finally: db.close()


# Serve the mobile/web app from the same origin so the deployed server is installable
# as a PWA on iPhone and Android without a separate frontend server.
APP_DIR = __import__("pathlib").Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=str(APP_DIR), html=True), name="app")
