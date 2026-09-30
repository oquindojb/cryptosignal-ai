from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal

Action = Literal["BUY", "HOLD", "SELL", "NO SIGNAL"]

class MarketAsset(BaseModel):
    id: str
    symbol: str
    name: str
    price: float | None = None
    change_24h: float | None = None
    volume_24h: float | None = None
    market_cap: float | None = None

class NewsEvent(BaseModel):
    event_id: str
    asset_id: str | None = None
    asset_symbol: str | None = None
    title: str
    url: str
    source: str
    published_at: datetime | None = None
    first_seen_at: datetime
    source_type: str = "news"
    credibility: float = Field(50, ge=0, le=100)
    novelty: float = Field(50, ge=0, le=100)
    impact: float = Field(50, ge=0, le=100)
    sentiment: float = Field(0, ge=-100, le=100)
    primary_verified: bool = False
    event_type: str = "other"
    canonical_event_id: str | None = None

class Signal(BaseModel):
    symbol: str
    action: Action
    score: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    headline: str
    freshness_minutes: int | None = None
    market_reaction: float | None = None
    volume_change: float | None = None
    reasons: list[dict]
    risks: list[str]
    evidence: list[str]
    event_ids: list[str]
    canonical_event_id: str | None = None
    primary_verified: bool = False
    orderbook_imbalance: float | None = None
    data_sources: list[str] = Field(default_factory=list)

class Outcome(BaseModel):
    signal_id: int
    symbol: str
    action: Action
    horizon: str
    return_pct: float | None = None
    status: str
    observed_at: datetime | None = None
