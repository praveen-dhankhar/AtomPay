# Contributing to AtomPay

Thanks for taking the time to improve AtomPay. This project is a full-stack
wallet system, so small, well-scoped changes are easier to review than broad
rewrites.

## Development Setup

Install dependencies for the services you plan to work on:

```bash
cd backend && npm install
cd ../frontend && npm install
cd ../ai-agent && python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create local environment files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
cp ai-agent/.env.example ai-agent/.env
```

Run services in separate terminals:

```bash
cd backend && npm start
cd backend && npm run start:worker
cd ai-agent && uvicorn main:app --host 0.0.0.0 --port 8000 --reload
cd frontend && npm run dev
```

## Pull Request Guidelines

- Keep the pull request focused on one behavior, bug, or documentation area.
- Explain the problem, the fix, and how you verified it.
- Update the README or `.env.example` files when setup, routes, or environment
  variables change.
- Do not commit secrets, `.env` files, dependency folders, database dumps, or
  local IDE settings.
- Preserve the wallet invariants: no negative balances, no partial transfers,
  and no duplicate charge on retries.

## Suggested Checks

Run the checks relevant to the files you changed:

```bash
# Backend syntax smoke check
node --check backend/index.js
node --check backend/app.js

# Frontend
cd frontend
npm run lint
npm run build

# AtomAI
cd ai-agent
python3 -m py_compile *.py
```

## Good First Contributions

- Add CI for backend syntax checks, frontend build, and Python compile checks.
- Add focused tests around transfer idempotency and concurrent transfer failure.
- Improve API documentation and examples.
- Harden the AtomAI service with internal service authentication.
- Improve frontend accessibility and responsive behavior.
