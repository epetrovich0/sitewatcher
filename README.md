# 🔭 SiteWatcher

Uptime monitoring service with Telegram alerts. Built with FastAPI + React + Docker.

## Features

| Feature | Free | Pro |
|---|---|---|
| Monitored sites | 1 | 50 |
| Check interval | 60 min | 1 min |
| Up/down alerts | ✅ | ✅ |
| Slow response alerts | ✅ | ✅ |
| Content change detection | ❌ | ✅ |
| Telegram integration | ✅ | ✅ |

---

## Quick Start

### 1. Clone & configure

```bash
git clone <repo>
cd sitewatcher
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
```env
SECRET_KEY=your-strong-random-secret
TELEGRAM_BOT_TOKEN=your_bot_token    # from @BotFather
FRONTEND_URL=http://localhost        # or your domain
```

### 2. Start with Docker

```bash
docker-compose up -d
```

App runs at `http://localhost` (frontend) and `http://localhost:8000` (API).

### 3. Create a Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the token to `TELEGRAM_BOT_TOKEN` in `.env`

### 4. Register the Telegram webhook

After deploying to a public URL:

```bash
pip install httpx python-dotenv
python setup_webhook.py https://your-domain.com
```

For local development, use [ngrok](https://ngrok.com/):
```bash
ngrok http 8000
python setup_webhook.py https://xxxx.ngrok.io
```

---

## Development (hot reload)

```bash
# Backend only
cd backend
pip install -r requirements.txt
cp .env.example .env  # edit as needed
uvicorn app.main:app --reload

# Frontend only
cd frontend
npm install
npm run dev
```

Or with Docker Compose:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## Project Structure

```
sitewatcher/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   │   ├── auth.py        # Register/login/JWT
│   │   │   ├── sites.py       # CRUD + check-now
│   │   │   ├── telegram.py    # Webhook + bot commands
│   │   │   └── billing.py     # Pro activation
│   │   ├── core/
│   │   │   └── config.py      # Settings from .env
│   │   ├── db/
│   │   │   └── database.py    # SQLAlchemy async setup
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── services/
│   │   │   ├── checker.py     # HTTP site checks
│   │   │   ├── scheduler.py   # APScheduler jobs
│   │   │   ├── telegram.py    # Alert message formatting
│   │   │   └── auth.py        # JWT + password utils
│   │   └── main.py            # FastAPI app
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/         # Dashboard, Auth, Settings, Upgrade
│   │   ├── components/    # SiteCard, AddSiteModal, StatusBadge, Logs
│   │   ├── store/         # Auth context
│   │   └── api.js         # Axios client
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
└── setup_webhook.py
```

---

## API Overview

| Endpoint | Method | Description |
|---|---|---|
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | Login, get JWT |
| `/api/auth/me` | GET | Current user + limits |
| `/api/sites/` | GET | List user's sites |
| `/api/sites/` | POST | Add site |
| `/api/sites/{id}` | PATCH | Update site |
| `/api/sites/{id}` | DELETE | Delete site |
| `/api/sites/{id}/check-now` | POST | Trigger immediate check |
| `/api/sites/{id}/logs` | GET | Check history |
| `/api/telegram/webhook` | POST | Telegram bot webhook |
| `/api/telegram/link-url` | GET | Get Telegram deep link |
| `/api/billing/activate-pro` | POST | Activate Pro (demo) |

---

## Adding Real Payments

The `/api/billing/activate-pro` endpoint is a demo stub. To add real payments:

1. **Stripe**: Add `stripe` to requirements, create a checkout session, use a Stripe webhook to call `user.is_paid = True` after successful payment.
2. **LiqPay / YooMoney**: Same pattern — verify payment server-side, then flip the flag.

The Telegram bot will automatically notify the user when Pro is activated.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./sitewatcher.db` | Database URL |
| `SECRET_KEY` | — | JWT signing key (change in prod!) |
| `TELEGRAM_BOT_TOKEN` | — | From @BotFather |
| `FRONTEND_URL` | `http://localhost:3000` | Used in Telegram links |
| `FREE_TIER_MAX_SITES` | `1` | Max sites on free plan |
| `FREE_TIER_MIN_INTERVAL` | `60` | Min check interval (min) on free |
| `PAID_TIER_MAX_SITES` | `50` | Max sites on Pro |
| `PAID_TIER_MIN_INTERVAL` | `1` | Min check interval (min) on Pro |
