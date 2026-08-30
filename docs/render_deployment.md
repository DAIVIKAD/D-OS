# Render Deployment Guide

## Blueprint

The repo includes `render.yaml`, so you can create a Render Blueprint from the repository.

## Manual Web Service

Use these settings:

```text
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

Set `PYTHON_VERSION=3.13.7` or let Render read `.python-version`.

## Required Environment Variables

```text
APP_ENV=production
APP_HOST=https://your-service.onrender.com
SESSION_COOKIE_NAME=dos_session
SESSION_DAYS=7
DEFAULT_CURRENCY=₹
FIREBASE_CREDENTIALS_JSON={...}
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

D-OS is configured for Render deployment.
