# CryptoSignal AI — Easy Setup for Windows (No Coding Required)

This guide is designed for someone who does **not** know Python, Docker, Linux, or app development.

## What you are building

Your Windows PC is only used to upload the project. The CryptoSignal AI server runs in the cloud, so your PC can be turned off and the scanner can keep running.

**Phone → HTTPS → CryptoSignal AI cloud server → news + market sources**

## Recommended hosting: Railway

Railway can build this project directly from its Dockerfile, provide HTTPS, manage environment variables, and keep persistent data on a volume or a managed PostgreSQL database.

### One-time setup

1. Create a Railway account at https://railway.com/.
2. Create a GitHub account at https://github.com/ if you do not already have one.
3. Create a **new private GitHub repository** named `cryptosignal-ai`.
4. Upload the contents of this folder to that repository. You can do this from GitHub's web interface; you do **not** need Git installed.
5. In Railway choose **New Project → Deploy from GitHub Repo** and select `cryptosignal-ai`.
6. Railway detects the root `Dockerfile` and builds the service automatically.
7. Add a PostgreSQL database in the same Railway project.
8. In the app service's Variables, create `DATABASE_URL` as a reference to the PostgreSQL service's `DATABASE_URL`.
9. Add the provider variables shown in `backend/.env.example` (for example `COINGECKO_API_KEY` if you have one). Keep keys in Railway Variables, never in the frontend.
10. Generate a public domain for the app service under Networking.
11. Open the generated HTTPS URL. The CryptoSignal AI mobile dashboard should appear.

## Persistent database

For the cloud deployment, use Railway PostgreSQL rather than the local SQLite database. The app automatically uses `DATABASE_URL` when it is provided.

## Phone installation

### iPhone

1. Open the HTTPS app URL in Safari.
2. Tap Share.
3. Tap **Add to Home Screen**.
4. Tap **Add**.

### Android

1. Open the HTTPS app URL in Chrome.
2. Tap the browser menu.
3. Choose **Install app** or **Add to Home screen**.

## Updating the app

When a new version is ready, the only normal maintenance step is to upload the updated files to the same GitHub repository. Railway can automatically redeploy when connected to the repository.

## If something goes wrong

Do not run random commands or delete services. Send the error message/screenshot to ChatGPT and we can troubleshoot it step by step.

## Security rules

- Never publish `.env` files containing real API keys.
- Never paste API keys into `app/` files.
- Keep the GitHub repository private.
- Use Railway Variables for secrets.
- Do not run the server as a public Windows process when the cloud deployment is available.


## v0.6 provider setup

You do not need to create accounts for Binance, Kraken, Coinbase, Alternative.me, GDELT or RSS feeds for their public-data features. The app uses them as free/public sources where available and automatically tolerates individual provider failures.

Optional settings:
- `COINGECKO_API_KEY`: improves CoinGecko access if you have a key.
- `GITHUB_TOKEN`: recommended only if you want higher GitHub API limits. GitHub documents 60 unauthenticated REST requests/hour and 5,000/hour for authenticated users.
- `OPENAI_API_KEY`: optional paid AI extraction; it does not make the final BUY/HOLD/SELL decision.
- `PUSH_ENABLED` + VAPID keys: enables phone push notifications.
- `APP_PASSWORD` + `APP_SECRET`: strongly recommended for a public deployment.

## What the app now monitors

Market: CoinGecko, Binance, Kraken, Coinbase, plus exchange order-book pressure.

News: RSS feeds, GDELT, and primary-source domain verification.

Context: Alternative.me Fear & Greed and optional GitHub developer activity.

Validation: forward outcomes at 1h/6h/24h/7d and performance statistics.

Native mobile: a Capacitor wrapper is included for future App Store/Google Play packaging; the PWA remains the easiest installation.
