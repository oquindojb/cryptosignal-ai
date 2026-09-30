import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

WATCHLIST = {
    "bitcoin": {"symbol": "BTC", "name": "Bitcoin", "aliases": ["bitcoin", "btc"]},
    "ethereum": {"symbol": "ETH", "name": "Ethereum", "aliases": ["ethereum", "eth"]},
    "quant-network": {"symbol": "QNT", "name": "Quant", "aliases": ["quant", "qnt", "quant network"]},
    "chainlink": {"symbol": "LINK", "name": "Chainlink", "aliases": ["chainlink", "link"]},
    "xrp": {"symbol": "XRP", "name": "XRP", "aliases": ["xrp", "ripple"]},
    "hedera-hashgraph": {"symbol": "HBAR", "name": "Hedera", "aliases": ["hedera", "hbar"]},
    "solana": {"symbol": "SOL", "name": "Solana", "aliases": ["solana", "sol"]},
}

RSS_FEEDS = [x.strip() for x in os.getenv("RSS_FEEDS", "https://www.coindesk.com/arc/outboundfeeds/rss/;https://cointelegraph.com/rss").replace(";",",").split(",") if x.strip()]
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")
BINANCE_ENABLED = os.getenv("BINANCE_ENABLED", "true").lower() == "true"
KRAKEN_ENABLED = os.getenv("KRAKEN_ENABLED", "true").lower() == "true"
COINBASE_ENABLED = os.getenv("COINBASE_ENABLED", "true").lower() == "true"
FEAR_GREED_ENABLED = os.getenv("FEAR_GREED_ENABLED", "true").lower() == "true"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
PUSH_ENABLED = os.getenv("PUSH_ENABLED", "false").lower() == "true"
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_EMAIL = os.getenv("VAPID_EMAIL", "mailto:admin@example.com")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
APP_SECRET = os.getenv("APP_SECRET", "change-me")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "300"))
# Railway/Postgres connection handling. Railway may expose postgres:// URLs, while
# SQLAlchemy expects postgresql://. Also tolerate accidental surrounding quotes.
_DEFAULT_DB_URL = f"sqlite:///{(Path(__file__).resolve().parent.parent / "data" / "cryptosignal.db").as_posix()}"
_RAW_DB_URL = (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or "").strip().strip('\"')
if _RAW_DB_URL.startswith("${{") or _RAW_DB_URL.startswith("${"):
    # An unresolved Railway variable reference should not crash the entire service.
    DB_URL = _DEFAULT_DB_URL
    DB_URL_WARNING = "DATABASE_URL appears to be an unresolved Railway variable reference; using local SQLite."
else:
    DB_URL = _RAW_DB_URL.replace("postgres://", "postgresql://", 1) if _RAW_DB_URL else _DEFAULT_DB_URL
    DB_URL_WARNING = ""

# Domains that can substantiate an event as a first-party/primary source.
PRIMARY_DOMAINS = {
    "bitcoin": {"bitcoin.org"},
    "ethereum": {"ethereum.org", "blog.ethereum.org", "ethereum.foundation"},
    "quant-network": {"quant.network", "quant.network/blog"},
    "chainlink": {"chain.link", "blog.chain.link"},
    "xrp": {"ripple.com", "xrpl.org"},
    "hedera-hashgraph": {"hedera.com", "docs.hedera.com"},
    "solana": {"solana.com", "solana.org", "solanafoundation.org"},
}

# Conservative deterministic event-language classifier. It is deliberately transparent
# and is intended to be replaced/enriched by structured LLM extraction later.
EVENT_RULES = {
    "positive": {
        "partnership": 18, "integration": 15, "adoption": 18, "launch": 14,
        "approval": 20, "approved": 20, "etf": 15, "listing": 10, "mainnet": 16,
        "upgrade": 12, "funding": 10, "investment": 10, "acquisition": 10,
        "contract": 12, "settlement": 8, "milestone": 8,
    },
    "negative": {
        "hack": -28, "hacked": -28, "exploit": -30, "breach": -25, "stolen": -28,
        "lawsuit": -14, "ban": -25, "banned": -25, "delist": -24, "delisting": -24,
        "shutdown": -20, "outage": -18, "halt": -18, "fraud": -30, "scam": -30,
        "unlock": -10, "liquidation": -18, "investigation": -14,
    },
}


# Exchange symbol mappings for public market-data cross-checks.
BINANCE_SYMBOLS = {
    "BTC":"BTCUSDT", "ETH":"ETHUSDT", "QNT":"QNTUSDT", "LINK":"LINKUSDT",
    "XRP":"XRPUSDT", "HBAR":"HBARUSDT", "SOL":"SOLUSDT"
}
KRAKEN_SYMBOLS = {
    "BTC":"XBTUSD", "ETH":"ETHUSD", "QNT":"QNTUSD", "LINK":"LINKUSD",
    "XRP":"XRPUSD", "HBAR":"HBARUSD", "SOL":"SOLUSD"
}
COINBASE_SYMBOLS = {
    "BTC":"BTC-USD", "ETH":"ETH-USD", "QNT":"QNT-USD", "LINK":"LINK-USD",
    "XRP":"XRP-USD", "HBAR":"HBAR-USD", "SOL":"SOL-USD"
}
GITHUB_REPOS = {
    "BTC":"bitcoin/bitcoin", "ETH":"ethereum/go-ethereum", "QNT":"quant-network/overledger",
    "LINK":"smartcontractkit/chainlink", "XRP":"XRPLF/rippled", "HBAR":"hashgraph/hedera-services",
    "SOL":"solana-labs/solana"
}
