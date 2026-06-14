# AtomPay — Backend Changes Log & Rationale

This document records everything changed on the backend during the Redis /
distributed-architecture work, how it differs from the original AtomPay coding
patterns, and the performance issue (and fix) that followed.

---

## 1. How the new code differs from the original AtomPay patterns

| Original pattern | What was introduced | Final status |
|---|---|---|
| Inline errors: `return res.status(x).json({ msg })` | Custom `class AppError extends Error` (error classes) | **Reverted** — now inline, matching the rest of the codebase |
| Response key always `msg` | Old rate limiter used `{ message }` (an inconsistency) | Changed to `{ msg }` — now consistent with all controllers |
| Flat directories (`controllers/`, `middlewares/`, `db/`) | A new `config/` directory for the Redis file | **Reverted** — Redis now lives in `db/redis.js` |
| Sparse comments, occasional `// FIX:` notes | Heavier JSDoc-style comment blocks | Trimmed toward the original terse style |
| Pure in-memory, **synchronous** middleware (a `Map`) | **Async middleware doing network I/O** to Redis | Kept (required for distributed limiting) — see §3 |
| `rateLimiter({ windowMs, max, message })` | Added a required `keyPrefix` + optional `identifier` | Kept (needed to namespace keys and key per-user) |
| No external infra dependencies | Added the `ioredis` package + a remote Redis dependency | Kept |
| `.then()` chains (original idempotency middleware) | `async/await` | Kept (stylistic) |

Everything else was kept identical to the original style: arrow-function
factories, `module.exports = { ... }`, camelCase, 4-space indentation.

---

## 2. Every backend step taken, and why

1. **`db/redis.js` (new)** — a single shared `ioredis` client (`getRedis`), a
   dedicated BullMQ-connection factory (`createBullConnection`), and
   `closeRedis()`.
   **Why:** one connection should be reused for all commands (the idiomatic
   Redis "pool"); BullMQ later needs its *own* connection with different
   settings, so it can't share the cache client. Centralizing this avoids
   opening a connection per request.

2. **Added the `ioredis` dependency.**
   **Why:** it is the standard Node Redis client and what the rate limiter
   (and later BullMQ) communicate through.

3. **Rewrote `middlewares/rateLimiter.js`: in-memory `Map` → Redis sorted-set
   sliding window.**
   **Why:** the original counted hits in a per-process `Map`. With two or more
   backend instances, each instance kept its own counter, so the effective
   limit became `max × number_of_instances` and brute-force protection broke at
   scale. Redis is shared state, so the limit holds across all instances. The
   implementation uses a single `MULTI` (remove expired entries → add the
   current timestamp → count → set expiry), so it is **one round-trip, not
   four**.

4. **Added `keyPrefix` per limiter and per-user `identifier`s** (auth limiters
   key on IP; AI chat = `user.id`, 10/min; transfer = `user.id`, 30/min).
   **Why:** different limiters must not collide on the same Redis keys, and the
   AI/transfer limits should be per authenticated user (after `authMiddleware`),
   not per IP.

5. **Fail-open on Redis errors** — on any Redis failure the middleware logs and
   calls `next()`.
   **Why:** a Redis blip should not lock everyone out of login. Trade-off:
   rate-limiting is silently disabled during a Redis outage.

6. **Custom error classes → reverted to inline `res.status().json()`.**
   **Why:** consistency with the existing codebase and easier to explain.

7. **`config/` → `db/`.** Moved the Redis file to match the existing flat
   directory convention; removed `config/`.

8. **`.claude/` added to `.gitignore`.**
   **Why:** `.claude/` is created locally by the Claude Code editor extension to
   store local settings/permissions. It was never committed, and gitignoring it
   guarantees it never will be.

---

## 3. Why it became slow, and how to fix it for low latency

### Cause
The original rate limiter read a local in-memory `Map` (~0.001 ms). The new one
makes a network call to the Redis Cloud instance on **every** rate-limited
request (login, signup, OTP, transfer, AI). Measured round-trip latency to the
current Redis instance was **~78 ms average, up to ~332 ms**. That round-trip is
paid *before the handler runs*, so every such request got ~78 ms slower.

The root reason: the Redis instance is in a **region far from where the app
runs**. Redis itself is sub-millisecond; the wire distance is the problem.

### Fixes, ranked by impact
1. **Co-locate Redis with the backend (the real fix → ~1 ms).** Put Redis in the
   same region/datacenter as the backend — e.g. Railway's own Redis plugin
   (same internal network) or a Redis Cloud / Upstash instance created in the
   exact region the backend runs in. This alone takes ~78 ms → ~1 ms.
2. **Pre-warm the connection at startup** so the first request doesn't pay
   connection setup: call `getRedis()` once in `index.js` on boot.
3. **Command timeout so a slow Redis fails open fast** — `commandTimeout: 200`
   and `maxRetriesPerRequest: 1` are now set in `db/redis.js`, so a stalled
   Redis makes a request wait at most ~200 ms instead of hanging.
4. **Two-tier limiter (optional)** — check a local in-memory counter first
   (0 ms fast path) and reconcile with Redis only periodically. Keeps latency
   near zero while staying multi-instance-safe.
5. **Lua script (`EVALSHA`)** instead of `MULTI` — still one round-trip, slightly
   less overhead. Minor; only worth it after #1.

> Note: measure latency from a **deployed** instance (backend → Redis), not from
> a laptop. After co-locating, expect ~1–3 ms.
