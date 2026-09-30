from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from .db import SessionLocal, EventRecord, MarketSnapshot, SignalRecord, SignalOutcome
from .sources import fetch_market, fetch_rss, fetch_gdelt
from .config import WATCHLIST
from .scoring import build_signal
from .dedupe import similarity
from .ai_extract import enrich
from .push import notify_signal
from .providers import fetch_microstructure

HORIZONS={"1h":timedelta(hours=1),"6h":timedelta(hours=6),"24h":timedelta(hours=24),"7d":timedelta(days=7)}

def _now(): return datetime.now(timezone.utc)

def persist_events(events):
    db=SessionLocal(); inserted=[]
    try:
        for e in events:
            existing=db.scalar(select(EventRecord).where(EventRecord.event_id==e.event_id))
            if existing:
                # Upgrade evidence if the same story is later found from a primary source.
                if e.primary_verified and not existing.primary_verified:
                    existing.primary_verified=True; existing.credibility=max(existing.credibility,e.credibility)
                continue
            canonical=e.canonical_event_id or e.event_id
            # Lightweight cluster against recent events for the same asset.
            recent=db.scalars(select(EventRecord).where(EventRecord.asset_symbol==e.asset_symbol).order_by(EventRecord.first_seen_at.desc()).limit(40)).all()
            for old in recent:
                if similarity(e.title, old.title)>=0.78:
                    canonical=old.canonical_event_id
                    break
            row=EventRecord(event_id=e.event_id,canonical_event_id=canonical,asset_id=e.asset_id,asset_symbol=e.asset_symbol,title=e.title,url=e.url,source=e.source,source_type=e.source_type,published_at=e.published_at,first_seen_at=e.first_seen_at,credibility=e.credibility,novelty=e.novelty,impact=e.impact,sentiment=e.sentiment,primary_verified=e.primary_verified,event_type=e.event_type)
            db.add(row); inserted.append(row)
        db.commit(); return inserted
    finally: db.close()

def persist_market(market):
    db=SessionLocal(); now=_now()
    try:
        for a in market:
            if a.price is not None:
                db.add(MarketSnapshot(symbol=a.symbol,price=a.price,change_24h=a.change_24h,volume_24h=a.volume_24h,captured_at=now))
        db.commit()
    finally: db.close()

def persist_signal(signal, entry_price):
    db=SessionLocal(); now=_now()
    try:
        if signal.canonical_event_id:
            existing=db.scalar(select(SignalRecord).where(SignalRecord.canonical_event_id==signal.canonical_event_id, SignalRecord.action==signal.action))
            if existing:
                return existing.id
        row=SignalRecord(symbol=signal.symbol,action=signal.action,score=signal.score,confidence=signal.confidence,headline=signal.headline,canonical_event_id=signal.canonical_event_id,created_at=now,entry_price=entry_price)
        db.add(row); db.flush()
        for horizon,delta in HORIZONS.items():
            db.add(SignalOutcome(signal_id=row.id,symbol=signal.symbol,horizon=horizon,target_at=now+delta,status="pending"))
        db.commit(); return row.id
    finally: db.close()

def update_outcomes(current_market):
    prices={a.symbol:a.price for a in current_market if a.price is not None}
    now=_now(); db=SessionLocal(); updated=0
    try:
        rows=db.scalars(select(SignalOutcome).where(SignalOutcome.status=="pending",SignalOutcome.target_at<=now)).all()
        for out in rows:
            signal=db.get(SignalRecord,out.signal_id)
            price=prices.get(out.symbol)
            if not signal or signal.entry_price is None or price is None: continue
            out.return_pct=(price/signal.entry_price-1)*100
            out.status="observed"; out.observed_at=now; updated+=1
        db.commit(); return updated
    finally: db.close()

async def run_cycle():
    market=await fetch_market(); persist_market(market)
    rss=await fetch_rss(); persist_events(rss)
    all_events=list(rss)
    by_symbol={a.symbol:[] for a in market}
    for e in rss: by_symbol.setdefault(e.asset_symbol,[]).append(e)
    # Sample GDELT concurrently so Scan Now does not wait through seven sequential requests.
    async def discover(a):
        try:
            return a.symbol, await fetch_gdelt(a.symbol)
        except Exception:
            return a.symbol, []
    discovered=await asyncio.gather(*(discover(a) for a in market))
    for symbol,gd in discovered:
        if gd:
            persist_events(gd); all_events.extend(gd); by_symbol.setdefault(symbol,[]).extend(gd)
    # Optional structured AI extraction. AI enriches evidence classification only;
    # the deterministic scoring engine remains responsible for the final signal.
    enriched=0
    for e in all_events[:10]:
        if enriched>=5: break
        if not e.event_type or e.event_type=='other':
            ai=await enrich(e.title)
            if ai:
                e.sentiment=max(-100,min(100,float(ai.get('sentiment',e.sentiment))))
                e.impact=max(0,min(100,float(ai.get('impact',e.impact))))
                e.novelty=max(0,min(100,float(ai.get('novelty',e.novelty))))
                e.event_type=str(ai.get('event_type',e.event_type))[:64]
                enriched+=1
    signals=[]
    async def build_one(a):
        s=build_signal(a,by_symbol.get(a.symbol,[]))
        try:
            imbalance,sources=await fetch_microstructure(a.symbol)
            s.orderbook_imbalance=imbalance
            s.data_sources=sorted(set(s.data_sources+sources))
            if imbalance is not None:
                s.reasons.append({"factor":"Order-book pressure","value":f"{imbalance*100:+.1f}%"})
        except Exception: pass
        return s
    signals=await asyncio.gather(*(build_one(a) for a in market))
    for a,s in zip(market,signals):
        if s.action in {"BUY","SELL"} and s.confidence>=55 and s.canonical_event_id:
            persist_signal(s,a.price)
            await notify_signal(s.symbol,s.action,s.score,s.confidence,s.headline)
    update_outcomes(market)
    return market,signals
