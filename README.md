# D-OS

MONEY OPERATING SYSTEM

Version 1.0.0 · Designed & Developed by DAIVIK A.D.

D-OS is a Render-ready personal finance operating system built with FastAPI, Jinja2, Firebase Authentication, Cloud Firestore, IBM CRT Phosphor Green theme, and Chart.js local charts.

The app uses Firebase as the only primary database and includes no relational database or migration layer.

## Firestore Structure

All financial data is scoped below the authenticated Firebase user:

```text
users/
  userId/
    profile/
      main
    expenses/
    income/
    goals/
    budgets/
    lendBorrow/
    investments/
    wishlist/
    recurring/
    settings/
    reports/
```

Every server-side CRUD helper starts from `users/{uid}` after verifying the Firebase session cookie, so users never query another user's financial records.
Every Firestore document written by the app includes `createdAt`, `updatedAt`, and `userId`.

## Local Run

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`.

You need Firebase environment variables before login and protected pages will work. Copy `.env.example` to `.env` and load those variables in your shell or process manager.

## Development Bypass

For local UI development only:

```bash
APP_ENV=development
DEV_BYPASS_LOGIN=true
```

When both flags are set, Firebase Authentication is skipped, a mock user is created, and sample data is served from memory. The app shows `Development Mode - Authentication Disabled`. In production, Firebase Authentication is always required.

## Firebase Setup

1. Create a Firebase project.
2. Enable Authentication providers:
   - Email/password
   - Google, if you want Google login
3. Create a Web App in Firebase and copy its web config into:
   - `FIREBASE_API_KEY`
   - `FIREBASE_AUTH_DOMAIN`
   - `FIREBASE_PROJECT_ID`
   - `FIREBASE_STORAGE_BUCKET`
   - `FIREBASE_MESSAGING_SENDER_ID`
   - `FIREBASE_APP_ID`
   - `FIREBASE_MEASUREMENT_ID`
4. Enable Cloud Firestore.
5. Create a Firebase Admin service account key.
6. On Render, set the full JSON as `FIREBASE_CREDENTIALS_JSON`.

Do not commit Firebase credentials.

## Render Deployment

This repo includes:

- `render.yaml`
- `runtime.txt`
- `.python-version`
- `requirements.txt`

Deploy with Render Blueprint or a Python Web Service:

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
Health Check: /health
```

Set these Render environment variables:

```text
APP_ENV=production
APP_HOST=https://your-render-service.onrender.com
SESSION_COOKIE_NAME=dos_session
SESSION_DAYS=7
DEFAULT_CURRENCY=₹
PYTHON_VERSION=3.13.7
FIREBASE_CREDENTIALS_JSON={...full service account json...}
FIREBASE_API_KEY=AIzaSyAGTO-nn4leLu5rji8TpeweEfRLwFcgJvE
FIREBASE_AUTH_DOMAIN=d-os-59476.firebaseapp.com
FIREBASE_PROJECT_ID=d-os-59476
FIREBASE_STORAGE_BUCKET=d-os-59476.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID=460980841419
FIREBASE_APP_ID=1:460980841419:web:d120e639dde0e16297244e
FIREBASE_MEASUREMENT_ID=G-ZSC2R0TLNP
FIREBASE_CLIENT_EMAIL=...
FIREBASE_PRIVATE_KEY=...
```

## Features

- Firebase email/password login, registration, forgot password, optional Google login, profile, logout
- Secure HTTP-only Firebase session cookies
- Dashboard with daily/monthly income and expense, remaining budget, savings, goals, lending summaries, recent transactions, quick actions, and D-engine tip
- Expense and income CRUD with category, amount, date, note, filters, search, and CSV export
- Goals with custom names, images/icons, target amount, saved amount, remaining amount, target date, contribution math, completion estimate, progress, and status
- Investment calculator for SIP, fixed deposit, recurring deposit, and custom investments with growth graph and saved plans
- Visualization page with monthly, weekly, daily, category, budget, savings, income/expense, goals, cash flow, investment, lending/borrowing, heatmap, top category, comparison, weekday, and net-worth charts
- Rule-based local Smart D-engine warnings and practical tips
- Monthly and category budgets with health and daily limit
- Lend and borrow tracking with phone, amount, due date, status, reminders, receive/pay summaries
- Recurring payments and wishlist, including wishlist-to-goal conversion
- Reports with CSV and PDF export

## Project Tree

```text
app/
  core/              config, template filters, navigation
  firebase/          Admin SDK init, auth middleware, Firestore schema constants
  models/            default profile/category data
  repositories/      authenticated Firestore repository wrappers
  routes/            FastAPI route modules
  services/          Firebase facade, Firestore CRUD, profile, finance calculations
  utils/             formatting and parsing helpers
templates/           Jinja2 pages and partials
static/              CSS, JS, local chart/HTMX helpers, assets
docs/                image prompts and setup guides
render.yaml          Render Blueprint
runtime.txt          Python runtime hint
.python-version      Render Python version pin
firestore.rules      Client-side Firestore security rules
```

## References

- Render Python version docs: https://render.com/docs/python-version
- Firebase Admin SDK setup: https://firebase.google.com/docs/admin/setup
- Firestore server client quickstart: https://firebase.google.com/docs/firestore/quickstart-server
- Firebase session cookies: https://firebase.google.com/docs/auth/admin/manage-cookies
