# Firebase Setup Guide

## Authentication

Enable these providers in Firebase Authentication:

- Email/password
- Google, optional

The browser uses Firebase Web Auth to sign in and sends the ID token to `/session-login`. The FastAPI backend verifies the token with Firebase Admin SDK and creates a secure HTTP-only session cookie.

## Firestore

Enable Cloud Firestore and use this app-owned layout:

```text
users/{uid}/profile/main
users/{uid}/expenses/{expenseId}
users/{uid}/income/{incomeId}
users/{uid}/goals/{goalId}
users/{uid}/budgets/{budgetId}
users/{uid}/lendBorrow/{entryId}
users/{uid}/investments/{investmentId}
users/{uid}/wishlist/{wishlistId}
users/{uid}/recurring/{paymentId}
users/{uid}/settings/main
users/{uid}/reports/{reportId}
```

All backend services receive the verified Firebase `uid` and build document paths from that `uid`.
Every document written by the app includes `createdAt`, `updatedAt`, and `userId`.

## Environment Variables

Use `FIREBASE_CREDENTIALS_JSON` on Render for the Firebase Admin SDK service account.

For local development, you can also use:

```bash
cp .env.example .env
# Then place serviceAccountKey.json in the project root.
```

The frontend also needs the Firebase Web App config variables listed in `.env.example`.

## Security Rules

Deploy `firestore.rules` to restrict client access to each user's own subtree.
