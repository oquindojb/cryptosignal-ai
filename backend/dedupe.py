import hashlib
import re
from difflib import SequenceMatcher
from urllib.parse import urlparse

STOP = {"the","a","an","and","or","of","to","for","in","on","with","as","is","are","from","by","new","crypto","cryptocurrency"}

def normalize_title(title: str) -> str:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return " ".join(w for w in words if w not in STOP)

def event_key(asset_id: str | None, title: str) -> str:
    base = f"{asset_id or ''}|{normalize_title(title)}"
    return hashlib.sha256(base.encode()).hexdigest()[:24]

def similarity(a: str, b: str) -> float:
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0
    return SequenceMatcher(None, na, nb).ratio()

def source_domain(url: str) -> str:
    return urlparse(url).netloc.lower()
