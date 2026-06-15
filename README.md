<div align="center">

# ⚡ AtomPay 
### A Production-Grade Digital Wallet Built with Precision & Care

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-B73BFE?style=for-the-badge&logo=vite&logoColor=FFD62E)
![Node.js](https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white)
![Express](https://img.shields.io/badge/Express-000000?style=for-the-badge&logo=express&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![Zod](https://img.shields.io/badge/Zod-3E67B1?style=for-the-badge&logo=zod&logoColor=white)

**[Built by Akshay Dhankhar](https://github.com/AkshayDhankhar1)**

*Not just another tutorial project. Built to understand what actually happens when ₹500 moves from one wallet to another, and how to protect it when things go wrong in the middle.*

</div>

---

## 🙋‍♂️ The Story Behind AtomPay

Picture this: You are at a tea stall, you scan the QR code, press pay, and your signal drops. You hit retry. *Bam!* Your account is debited twice. We've all been there, and honestly? *Dimaag kharab ho jata hai.* 

I built AtomPay because I wanted to look under the hood of digital payment systems. Most apps hide the complexity, but AtomPay embraces it. It's built on a singular, non-negotiable philosophy: **Jab paise hawa mein hote hain, 'hope' is not an acceptable architecture.** 

Every single feature here—from atomic transactions to idempotency keys—was written to solve a real-world edge case. It's professional-grade, but hand-crafted with a deeply personal obsession with breaking things and fixing them.

---

## 🚀 The Core Philosophy (Features)

Kyunki security aur reliability me koi jugaad nahi chalta. 🛡️

### 1. Bulletproof Transactions (The Backend Heartbeat)
- **All or Nothing:** Atomic money transfers via MongoDB sessions. If step 14 fails, steps 1 through 13 rollback automatically. No partial credits, no missing funds.
- **Race Condition Safety:** Balance is checked *twice* (once outside the transaction, once *inside* the locked session) to prevent concurrent double-spending.
- **Idempotency Keys:** Network went buffering? The frontend sends an `Idempotency-Key` and the backend stakes an atomic Redis `SET NX` claim *before* touching MongoDB — so a double-tap or auto-retry replays the cached response instead of charging twice. No race window, no double charges.

### 2. Fort Knox Level Security 
- **Dual Tokens:** 15-minute Access Tokens paired with 7-day Refresh Tokens. 
- **OTP Verification:** Email OTPs sent via NodeMailer using `speakeasy`, acting as a mandatory 2FA.
- **Independent Hashes:** UPI PINs and Passwords are hashed separately (`bcrypt`) and protected via `select: false`.
- **Distributed Rate Limiting (Redis):** A Redis sorted-set sliding window enforces limits across *every* backend instance in a single round-trip (auth keyed by IP, AI chat & transfers keyed per user). Brute-force protection holds at scale instead of resetting per process.

### 3. Distributed & Production-Ready (Redis Backbone)
- **Read-through Caching:** Balance and transaction history are served from Redis and invalidated **only after** a successful 2-phase commit, so financial data is fast but never stale.
- **Async Event Queues (BullMQ):** Transaction emails and audit logs are pushed to Redis-backed queues and handled by a **separate worker process** (`npm run start:worker`), with retries and backoff. The HTTP request returns the moment the money has moved — heavy work never blocks the response. *(OTP emails stay synchronous by design — they're auth-critical and short-lived.)*
- **Graceful Shutdown:** On `SIGTERM`/`SIGINT`, the API drains in-flight requests (including active Mongo transactions) before closing queues, Mongo, and Redis — with a 10s safety net. The worker finishes its active jobs before exiting.
- **Connection Pooling:** A bounded, reused MongoDB pool (`maxPoolSize`/`minPoolSize` + timeouts) and a single pre-warmed, multiplexed Redis client — no connection churn per request.
- **Fail-Open Everywhere:** Caching, idempotency, and queueing all degrade gracefully — a Redis blip can never break a legitimate transfer.

### 4. Beautiful & Responsive Frontend (React + Vite)
- Polished, mobile-responsive UI specifically tailored to feel like a premium Fintech app (think Cred/PhonePe vibes).
- Real-time QR Code scanning integrated directly into the browser.
- Seamless, micro-animated user-flows.

---

## 🏗️ How a Transfer *Actually* Works

When you click "Pay", a very intense checklist runs in milliseconds:

```text
1.  Basic Checks: Amount ≥ ₹1? Self-transfer? Sender/Receiver active?
2.  PIN Verification: Compare hashed UPI PIN.
3.  Fraud Check: Run DB Aggregation -> Last 24hr sent + this amount ≤ ₹1,00,000?
4.  Idempotency Check: Was a request with this exact ID already handled?
5.  → START MONGODB SESSION
6.  Re-fetch both wallets & Re-check balances INSIDE the session lock 🔒
7.  Save transaction document as "pending"
8.  Deduct sender, credit receiver
9.  Update transaction document to "success"
10. → COMMIT SESSION

💥 On ANY failure between step 5 and 10:
→ Session aborts completely.
→ Both wallets revert to their exact previous state safely.
→ Transaction record is marked "failed" so the user knows exactly why.
```

---


## 📅 The Journey So Far (What's Next?)

I've tackled the hardest parts first:
- [x] Atomic Database Transactions
- [x] Aggregation-based Daily Caps
- [x] Email OTP authentication
- [x] Redis idempotency (atomic `SET NX`)
- [x] Distributed Rate Limiting (Redis sliding window)
- [x] Read-through caching (balance + history)
- [x] Async event queues (BullMQ workers)
- [x] Graceful shutdown + connection pooling
- [x] Real-time QR Code Payments

Still cooking:
- [ ] PIN lockout after 3 wrong attempts
- [ ] Wallet-to-Bank mock withdrawals
- [ ] Split Bill & Request Money functionality
- [ ] Webhooks
- [ ] Reconciliation Engine

---

<div align="center">

### Thank you for checking out AtomPay.
*Whether you're breaking the code, hiring me, or just reading through, I appreciate your time. Happy Coding! ✨*
Built by **[Akshay Dhankhar](https://github.com/AkshayDhankhar1)**

</div>