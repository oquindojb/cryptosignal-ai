from __future__ import annotations
from datetime import datetime, timezone
import asyncio, httpx
from .config import BINANCE_SYMBOLS, KRAKEN_SYMBOLS, COINBASE_SYMBOLS, GITHUB_REPOS, GITHUB_TOKEN
from .models import MarketAsset


def now(): return datetime.now(timezone.utc)

async def _get(client, url, **kwargs):
    r = await client.get(url, **kwargs)
    r.raise_for_status()
    return r.json()

async def fetch_binance_market():
    symbols=list(BINANCE_SYMBOLS.values())
    url='https://data-api.binance.vision/api/v3/ticker/24hr'
    async with httpx.AsyncClient(timeout=12) as c:
        data=await _get(c,url,params={'symbols':'["'+ '\",\"'.join(symbols) +'\"]'})
    by={x.get('symbol'):x for x in data if isinstance(x,dict)}
    return {sym:{'price':float(x['lastPrice']),'change_24h':float(x['priceChangePercent']),'volume_24h':float(x['quoteVolume'])}
            for sym,b in BINANCE_SYMBOLS.items() if (x:=by.get(b)) and x.get('lastPrice')}

async def fetch_kraken_market():
    pairs=','.join(KRAKEN_SYMBOLS.values())
    url='https://api.kraken.com/0/public/Ticker'
    async with httpx.AsyncClient(timeout=12) as c:
        data=await _get(c,url,params={'pair':pairs})
    result=data.get('result',{})
    out={}
    for sym,pair in KRAKEN_SYMBOLS.items():
        x=result.get(pair) or result.get(pair.replace('XBT','XXBT'))
        if x:
            try:
                last=float(x['c'][0]); openp=float(x['o']); vol=float(x['v'][1]); change=(last/openp-1)*100 if openp else None
                out[sym]={'price':last,'change_24h':change,'volume_24h':vol}
            except Exception: pass
    return out

async def fetch_coinbase_market():
    async with httpx.AsyncClient(timeout=10) as c:
        async def one(sym, product):
            try:
                x=await _get(c,f'https://api.exchange.coinbase.com/products/{product}/ticker')
                return sym,{'price':float(x['price'])}
            except Exception: return sym,None
        rows=await asyncio.gather(*(one(s,p) for s,p in COINBASE_SYMBOLS.items()))
    return {s:v for s,v in rows if v}

async def fetch_fear_greed():
    url='https://api.alternative.me/fng/'
    async with httpx.AsyncClient(timeout=10) as c:
        data=await _get(c,url,params={'limit':1})
    x=(data.get('data') or [{}])[0]
    return {'value':int(x.get('value',0)),'classification':x.get('value_classification','Unknown'),'timestamp':x.get('timestamp')}

async def fetch_github_activity(symbol):
    repo=GITHUB_REPOS.get(symbol)
    if not repo: return None
    headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2026-03-10'}
    if GITHUB_TOKEN: headers['Authorization']=f'Bearer {GITHUB_TOKEN}'
    url=f'https://api.github.com/repos/{repo}/commits'
    async with httpx.AsyncClient(timeout=10,headers=headers) as c:
        data=await _get(c,url,params={'per_page':5})
    return {'repo':repo,'recent_commits':len(data),'latest_commit':(data[0].get('commit',{}).get('author',{}).get('date') if data else None)}


async def fetch_microstructure(symbol):
    from .config import BINANCE_SYMBOLS, KRAKEN_SYMBOLS
    b=BINANCE_SYMBOLS.get(symbol); k=KRAKEN_SYMBOLS.get(symbol)
    results=[]
    async with httpx.AsyncClient(timeout=8) as c:
        if b:
            try:
                x=await _get(c,'https://data-api.binance.vision/api/v3/depth',params={'symbol':b,'limit':20})
                bid=sum(float(q)*float(p) for p,q in x.get('bids',[])); ask=sum(float(q)*float(p) for p,q in x.get('asks',[])); results.append(('Binance', (bid-ask)/(bid+ask) if bid+ask else 0))
            except Exception: pass
        if k:
            try:
                x=await _get(c,'https://api.kraken.com/0/public/Depth',params={'pair':k,'count':20})
                book=next(iter(x.get('result',{}).values())); bid=sum(float(p)*float(q) for p,q,*_ in book.get('bids',[])); ask=sum(float(p)*float(q) for p,q,*_ in book.get('asks',[])); results.append(('Kraken',(bid-ask)/(bid+ask) if bid+ask else 0))
            except Exception: pass
    if not results: return None,[]
    return sum(v for _,v in results)/len(results), [n for n,_ in results]
