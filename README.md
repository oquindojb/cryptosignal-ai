# CryptoSignal AI v0.6.0 — Mobile Edition

CryptoSignal AI is an early-warning crypto market intelligence dashboard. It collects market/news evidence, clusters duplicate events, verifies configured first-party sources, scores signals deterministically, and records outcomes for later measurement.

## v0.6.0 focus

- Mobile-first responsive UI
- Installable PWA for iPhone and Android
- Same-origin frontend + FastAPI backend
- Cloud deployment ready for Railway
- Railway healthcheck and Docker configuration
- PostgreSQL-compatible database through `DATABASE_URL`
- Persistent signal/event/outcome records
- Event deduplication and primary-source verification
- BUY / HOLD / SELL / NO SIGNAL decision support
- Clear evidence, confidence, and risk display
- Manual "Scan now" control
- Offline app shell caching

## Important

Signals are decision support, not guarantees. The system should be evaluated through historical backtesting and live outcome tracking before being relied upon for financial decisions.

## Easiest deployment

Read **DEPLOY-EASY.md**. It is written for Windows users without coding experience and does not require installing Python, Docker, Git, or Linux on the PC.

## Local development (optional)

If you are technical, Docker Compose can run the app locally. This is optional; ordinary users should use the cloud deployment guide.
