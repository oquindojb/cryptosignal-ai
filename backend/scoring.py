from datetime import datetime, timezone
from .models import Signal, NewsEvent, MarketAsset


def clamp(x, lo=0, hi=100): return max(lo, min(hi, x))

def build_signal(asset: MarketAsset, events: list[NewsEvent]) -> Signal:
    if not events:
        return Signal(symbol=asset.symbol, action="NO SIGNAL", score=50, confidence=28, headline="No material fresh event detected", reasons=[{"factor":"Evidence","value":"Insufficient fresh evidence"}], risks=["No current catalyst strong enough to justify a directional call."], evidence=[], event_ids=[], data_sources=[])
    # Prefer verified, impactful, recent events. Keep multiple independent sources as evidence.
    events = sorted(events, key=lambda e: (e.primary_verified, e.impact, e.novelty), reverse=True)
    e = events[0]
    now=datetime.now(timezone.utc)
    age=max(0,(now-(e.published_at or e.first_seen_at)).total_seconds()/60)
    freshness=clamp(100-age*1.5)
    event_strength=0.30*e.credibility+0.25*e.novelty+0.30*e.impact+0.15*(100 if e.primary_verified else 0)
    direction=e.sentiment/100.0
    market=asset.change_24h or 0
    priced_in_penalty=min(25,abs(market)*2.2)
    raw=50+direction*event_strength*0.48+(freshness-50)*0.12-priced_in_penalty
    if e.primary_verified: raw += 4 if direction > 0 else -2
    if direction > .2 and raw >= 68: action="BUY"
    elif direction < -.2 and raw <= 38: action="SELL"
    elif raw >= 57 or raw <= 43: action="HOLD"
    else: action="NO SIGNAL"
    independent=max(1,len({x.source for x in events}))
    confidence=clamp(20+.30*e.credibility+.20*e.novelty+.20*e.impact+.15*freshness+.10*(100 if e.primary_verified else 0)+min(10,independent*2))
    reasons=[
        {"factor":"Event type","value":e.event_type},
        {"factor":"Source credibility","value":f"{e.credibility:.0f}/100"},
        {"factor":"Primary-source verified","value":"Yes" if e.primary_verified else "No"},
        {"factor":"Novelty / freshness","value":f"{e.novelty:.0f}/100"},
        {"factor":"Potential impact","value":f"{e.impact:.0f}/100"},
        {"factor":"Market reaction","value":f"{market:+.2f}%"},
        {"factor":"Priced-in penalty","value":f"-{priced_in_penalty:.0f}"},
    ]
    risks=[
        "Headline classification is deterministic and can miss context, sarcasm, or conflicting details.",
        "A large existing price move can mean the market has already priced in part of the information.",
        "Broader BTC/market conditions can overwhelm an asset-specific catalyst.",
    ]
    if not e.primary_verified: risks.insert(0,"Primary-source confirmation is still missing.")
    evidence=[f"Source: {e.source}",f"First detected: {e.first_seen_at.isoformat()}",f"Event cluster: {e.canonical_event_id or e.event_id}"]
    return Signal(symbol=asset.symbol, action=action, score=int(clamp(raw)), confidence=int(clamp(confidence)), headline=e.title, freshness_minutes=int(age), market_reaction=market, volume_change=None, reasons=reasons, risks=risks, evidence=evidence, event_ids=[x.event_id for x in events[:5]], canonical_event_id=e.canonical_event_id, primary_verified=e.primary_verified, data_sources=sorted({x.source_type for x in events}))
