import hashlib
import asyncio
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import httpx
from .config import RSS_FEEDS, WATCHLIST, COINGECKO_API_KEY, BINANCE_ENABLED, KRAKEN_ENABLED, COINBASE_ENABLED, FEAR_GREED_ENABLED
from .models import MarketAsset, NewsEvent
from .classifier import classify_event, primary_verified
from .dedupe import event_key
from .providers import fetch_binance_market, fetch_kraken_market, fetch_coinbase_market, fetch_fear_greed


def _now(): return datetime.now(timezone.utc)

def _asset_from_title(title: str):
    t = title.lower()
    for aid, meta in WATCHLIST.items():
        for alias in meta["aliases"]:
            if alias in t:
                return aid
    return None

async def fetch_market():
    # CoinGecko remains the primary aggregate source; exchange APIs cross-check it
    # and act as automatic fallbacks when it is unavailable.
    ids = ",".join(WATCHLIST.keys())
    headers = {"x-cg-demo-api-key": COINGECKO_API_KEY} if COINGECKO_API_KEY else {}
    cg = {}
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {"vs_currency":"usd","ids":ids,"price_change_percentage":"24h","per_page":100,"page":1}
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(url, params=params, headers=headers); r.raise_for_status()
            for x in r.json(): cg[x["symbol"].upper()] = {"price":x.get("current_price"),"change_24h":x.get("price_change_percentage_24h"),"volume_24h":x.get("total_volume"),"market_cap":x.get("market_cap"),"name":x.get("name"),"id":x.get("id")}
    except Exception:
        cg = {}
    providers=[]
    async def safe(name, fn):
        try: return name, await fn()
        except Exception: return name, {}
    if BINANCE_ENABLED: providers.append(safe("binance", fetch_binance_market))
    if KRAKEN_ENABLED: providers.append(safe("kraken", fetch_kraken_market))
    if COINBASE_ENABLED: providers.append(safe("coinbase", fetch_coinbase_market))
    results=await asyncio.gather(*providers) if providers else []
    pmap={name:data for name,data in results}
    assets=[]
    for aid,meta in WATCHLIST.items():
        sym=meta["symbol"]; vals=[]
        for src,data in pmap.items():
            if data.get(sym,{}).get("price") is not None: vals.append(float(data[sym]["price"]))
        base=cg.get(sym,{})
        if base.get("price") is not None: vals.append(float(base["price"]))
        if not vals: continue
        vals.sort(); median=vals[len(vals)//2]
        # Prefer live exchange rolling-24h change over the slower aggregate feed.
        # CoinGecko remains the fallback for assets not covered by an exchange.
        live_changes=[d[sym].get("change_24h") for name,d in pmap.items() if d.get(sym,{}).get("change_24h") is not None]
        if live_changes:
            live_changes=sorted(float(x) for x in live_changes)
            change=live_changes[len(live_changes)//2]
        else:
            change=base.get("change_24h")
        volume=base.get("volume_24h")
        if volume is None:
            vols=[d[sym].get("volume_24h") for d in pmap.values() if d.get(sym,{}).get("volume_24h") is not None]
            volume=sum(vols)/len(vols) if vols else None
        assets.append(MarketAsset(id=aid,symbol=sym,name=base.get("name",meta["name"]),price=median,change_24h=change,volume_24h=volume,market_cap=base.get("market_cap")))
    return assets

async def fetch_provider_status():
    status={}
    async def check(name, fn):
        try:
            data=await fn(); return name, {"ok":bool(data),"items":len(data) if isinstance(data,dict) else 0}
        except Exception as e: return name,{"ok":False,"error":str(e)}
    checks=[]
    if BINANCE_ENABLED: checks.append(check("Binance",fetch_binance_market))
    if KRAKEN_ENABLED: checks.append(check("Kraken",fetch_kraken_market))
    if COINBASE_ENABLED: checks.append(check("Coinbase",fetch_coinbase_market))
    if FEAR_GREED_ENABLED: checks.append(check("Alternative.me Fear & Greed",fetch_fear_greed))
    for name,res in await asyncio.gather(*checks): status[name]=res
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get("https://api.coingecko.com/api/v3/ping"); status["CoinGecko"]={"ok":r.is_success}
    except Exception as e: status["CoinGecko"]={"ok":False,"error":str(e)}
    return status

async def fetch_rss():
    events=[]; now=_now()
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for feed_url in RSS_FEEDS:
            try:
                r=await client.get(feed_url); r.raise_for_status()
                root=ET.fromstring(r.text)
                channel=root.find("channel") if root.tag.lower().endswith("rss") else root
                items=list(channel.findall("item")) if channel is not None else []
                for item in items[:50]:
                    title=(item.findtext("title") or "").strip()
                    link=(item.findtext("link") or "").strip()
                    if not title or not link: continue
                    aid=_asset_from_title(title)
                    if not aid: continue
                    pub=(item.findtext("pubDate") or "").strip()
                    published=None
                    if pub:
                        from email.utils import parsedate_to_datetime
                        try: published=parsedate_to_datetime(pub).astimezone(timezone.utc)
                        except Exception: pass
                    sentiment, impact, event_type = classify_event(title)
                    event_id=event_key(aid,title)
                    events.append(NewsEvent(event_id=event_id, asset_id=aid, asset_symbol=WATCHLIST[aid]["symbol"], title=title, url=link, source=feed_url, published_at=published, first_seen_at=now, source_type="rss", credibility=70, novelty=65, impact=impact, sentiment=sentiment, primary_verified=primary_verified(aid,link), event_type=event_type, canonical_event_id=event_id))
            except Exception:
                continue
    return events

async def fetch_gdelt(symbol: str):
    query=f'"{symbol}" (crypto OR cryptocurrency OR token)'
    url="https://api.gdeltproject.org/api/v2/doc/doc"
    params={"query":query,"mode":"artlist","maxrecords":25,"timespan":"1h","sort":"datedesc","format":"json"}
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.get(url,params=params); r.raise_for_status(); data=r.json()
    now=_now(); aid=next((k for k,v in WATCHLIST.items() if v["symbol"]==symbol),None); events=[]
    for item in data.get("articles",[]):
        title=item.get("title","").strip(); link=item.get("url","")
        if not title or not link: continue
        sentiment, impact, event_type = classify_event(title)
        eid=event_key(aid,title)
        events.append(NewsEvent(event_id=eid, asset_id=aid, asset_symbol=symbol, title=title, url=link, source=item.get("domain","GDELT"), published_at=None, first_seen_at=now, source_type="gdelt", credibility=55, novelty=60, impact=impact, sentiment=sentiment, primary_verified=primary_verified(aid,link), event_type=event_type, canonical_event_id=eid))
    return events
