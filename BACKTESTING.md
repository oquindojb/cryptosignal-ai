# Signal validation and backtesting

The app now records forward outcomes at 1h, 6h, 24h and 7d and exposes `/api/performance`.

This is deliberately separate from historical backtesting: a true backtest must use data that was available at the simulated decision time and must enforce strict no-lookahead rules.

Recommended v0.7 validation workflow:
1. Accumulate at least 30–90 days of event, market and signal history.
2. Export timestamped market/news data.
3. Replay the deterministic signal engine chronologically.
4. Compare BUY/SELL/HOLD against fixed horizons, transaction costs and slippage.
5. Calibrate confidence by asset and event type.
6. Keep a holdout period that the scoring rules never see during tuning.
