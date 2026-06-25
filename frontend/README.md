# AtomPay Frontend

React/Vite client for AtomPay.

## Local Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The app expects the backend API at `VITE_API_BASE_URL`, which defaults to:

```text
http://localhost:3000/api
```

## Main Screens

- `Dashboard.jsx` - wallet balance, QR code, recent activity, and daily limit.
- `Transfer.jsx` - username/QR transfer flow with idempotency headers.
- `Transactions.jsx` - wallet ledger and filters.
- `AiChat.jsx` - AtomAI chat, analytics, tips, budget, and insights.
- `Settings.jsx` - password/PIN changes and logout.

Shared API behavior lives in `src/api.js`, including access-token refresh and
custom request headers such as `Idempotency-Key`.
