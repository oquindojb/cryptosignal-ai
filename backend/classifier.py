import re
from urllib.parse import urlparse
from .config import EVENT_RULES, PRIMARY_DOMAINS


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def primary_verified(asset_id: str | None, url: str) -> bool:
    if not asset_id:
        return False
    domain = domain_of(url)
    for allowed in PRIMARY_DOMAINS.get(asset_id, set()):
        if domain == allowed or domain.endswith("." + allowed):
            return True
    return False


def classify_event(title: str):
    t = title.lower()
    pos = []
    neg = []
    for word, weight in EVENT_RULES["positive"].items():
        if re.search(r"\b" + re.escape(word) + r"\b", t):
            pos.append((word, weight))
    for word, weight in EVENT_RULES["negative"].items():
        if re.search(r"\b" + re.escape(word) + r"\b", t):
            neg.append((word, weight))
    total = sum(w for _, w in pos) + sum(w for _, w in neg)
    sentiment = max(-100, min(100, total * 2.2))
    if pos and not neg:
        event_type = pos[0][0]
    elif neg and not pos:
        event_type = neg[0][0]
    elif pos or neg:
        event_type = "mixed"
    else:
        event_type = "other"
    impact = min(100, 45 + abs(total) * 1.8)
    return sentiment, impact, event_type
