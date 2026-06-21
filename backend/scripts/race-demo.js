#!/usr/bin/env node
/**
 * AtomPay — Concurrency / Race-Condition demo (for a screen recording).
 *
 * Fires several transfer requests AT THE SAME TIME from one account and prints a
 * clean, colour-coded report showing that the server lets exactly ONE through
 * and rejects the rest — proving no double-spend.
 *
 * It uses only Node's built-in fetch (Node 18+), so there are no dependencies.
 *
 * ── Usage (PowerShell) ────────────────────────────────────────────────
 *   $env:TOKEN="<access token from browser localStorage 'token'>"
 *   $env:RECEIVER="bob"; $env:PIN="123456"
 *   node scripts/race-demo.js
 *
 * ── Usage (bash) ──────────────────────────────────────────────────────
 *   TOKEN="..." RECEIVER="bob" PIN="123456" node scripts/race-demo.js
 *
 * ── Options (env vars) ────────────────────────────────────────────────
 *   BASE      API base url        (default http://localhost:3000/api)
 *   AMOUNT    rupees per transfer (default 100000)
 *   COUNT     concurrent requests (default 2)
 *   MODE      "race" -> each request gets a unique Idempotency-Key
 *                       (genuinely concurrent transfers; ACID/velocity guard)
 *             "idem" -> all requests share ONE Idempotency-Key
 *                       (double-submit; SETNX idempotency guard)
 *             (default "race")
 */

const crypto = require("crypto");

const BASE = process.env.BASE || "http://localhost:3000/api";
const TOKEN = process.env.TOKEN;
const RECEIVER = process.env.RECEIVER;
const PIN = process.env.PIN;
const AMOUNT = Number(process.env.AMOUNT || 100000);
const COUNT = Number(process.env.COUNT || 2);
const MODE = (process.env.MODE || "race").toLowerCase();

const c = {
  reset: "\x1b[0m", bold: "\x1b[1m", dim: "\x1b[90m",
  green: "\x1b[32m", red: "\x1b[31m", yellow: "\x1b[33m",
  orange: "\x1b[38;5;208m", cyan: "\x1b[36m",
};
const inr = (n) => "₹" + new Intl.NumberFormat("en-IN").format(n);
const line = (ch = "─") => ch.repeat(64);

function usageExit() {
  console.log(`${c.red}Missing required env vars.${c.reset}
Set at least TOKEN, RECEIVER and PIN. Example (bash):
  ${c.cyan}TOKEN="<paste access token>" RECEIVER="bob" PIN="123456" node scripts/race-demo.js${c.reset}
Tip: get the token from the browser devtools console:  ${c.dim}localStorage.getItem("token")${c.reset}`);
  process.exit(1);
}
if (!TOKEN || !RECEIVER || !PIN) usageExit();

const authHeaders = { Authorization: `Bearer ${TOKEN}` };

async function getBalance() {
  try {
    const res = await fetch(`${BASE}/wallet/balance`, { headers: authHeaders });
    const data = await res.json();
    return typeof data.balance === "number" ? data.balance : null;
  } catch { return null; }
}

async function fire(i, idemKey) {
  const headers = { "Content-Type": "application/json", ...authHeaders };
  if (idemKey) headers["Idempotency-Key"] = idemKey;
  const start = performance.now();
  let status = 0, msg = "";
  try {
    const res = await fetch(`${BASE}/transaction/transfer`, {
      method: "POST",
      headers,
      body: JSON.stringify({ receiverUsername: RECEIVER, amount: AMOUNT, pin: PIN }),
    });
    status = res.status;
    const text = await res.text();
    try { msg = JSON.parse(text).msg ?? text; } catch { msg = text; }
  } catch (e) { msg = e.message; }
  return { i, status, msg, ms: performance.now() - start };
}

function tagFor(r) {
  if (r.status >= 200 && r.status < 300) return { ok: true, label: `${c.green}✅ SUCCESS${c.reset}`, why: "" };
  let why = "blocked";
  if (r.status === 409) why = "duplicate — idempotency SETNX";
  else if (r.status === 429) why = "rate limited";
  else if (/24 hours/i.test(r.msg)) why = "velocity cap (₹1,00,000 / 24h)";
  else if (/insufficient|sufficient/i.test(r.msg)) why = "insufficient balance — rolled back";
  else if (r.status >= 500) why = "race / write-conflict — atomic rollback";
  return { ok: false, label: `${c.yellow}🛡️  BLOCKED${c.reset}`, why };
}

(async () => {
  console.log(`${c.orange}${c.bold}${line("═")}${c.reset}`);
  console.log(`${c.orange}${c.bold}   AtomPay — Concurrency / Race-Condition Demo${c.reset}`);
  console.log(`${c.orange}${c.bold}${line("═")}${c.reset}`);
  const modeNote = MODE === "idem"
    ? "IDEM (shared Idempotency-Key → SETNX dedup)"
    : "RACE (distinct keys → ACID + velocity guard)";
  console.log(`Mode: ${c.bold}${modeNote}${c.reset}`);
  console.log(`Receiver: ${c.bold}@${RECEIVER}${c.reset}   Amount each: ${c.bold}${inr(AMOUNT)}${c.reset}   Concurrency: ${c.bold}${COUNT}${c.reset}\n`);

  const balBefore = await getBalance();
  console.log(`Balance before : ${c.bold}${balBefore === null ? "n/a" : inr(balBefore)}${c.reset}`);
  console.log(`\n${c.cyan}Firing ${COUNT} transfers simultaneously…${c.reset}\n`);

  const sharedKey = crypto.randomUUID();
  const t0 = performance.now();
  const offsets = [];
  const promises = [];
  for (let i = 1; i <= COUNT; i++) {
    const key = MODE === "idem" ? sharedKey : crypto.randomUUID();
    offsets[i] = performance.now() - t0;          // when this request was launched
    promises.push(fire(i, key));
  }
  const results = (await Promise.all(promises)).sort((a, b) => a.i - b.i);

  for (const r of results) {
    const t = tagFor(r);
    const off = `+${offsets[r.i].toFixed(1)}ms`.padEnd(9);
    const code = String(r.status).padEnd(3);
    const lat = `${r.ms.toFixed(0)}ms`.padStart(6);
    console.log(`  #${r.i}  ${c.dim}sent ${off}${c.reset} ← ${c.bold}${code}${c.reset} ${c.dim}(${lat})${c.reset}  ${t.label}`);
    console.log(`       ${c.dim}${r.msg}${t.why ? "  ·  " + t.why : ""}${c.reset}`);
  }

  const balAfter = await getBalance();
  const succeeded = results.filter(r => r.status >= 200 && r.status < 300).length;
  const blocked = results.length - succeeded;
  const moved = (balBefore !== null && balAfter !== null) ? balBefore - balAfter : null;
  const expected = AMOUNT * succeeded;
  const invariantOk = moved !== null && moved === expected;

  console.log(`\n${line()}`);
  console.log(`${c.bold}SUMMARY${c.reset}`);
  console.log(`  ${c.green}✅ Succeeded${c.reset} : ${c.bold}${succeeded}${c.reset}`);
  console.log(`  ${c.yellow}🛡️  Blocked${c.reset}   : ${c.bold}${blocked}${c.reset}   ${c.dim}(server prevented the race)${c.reset}`);
  console.log(`  Balance after : ${c.bold}${balAfter === null ? "n/a" : inr(balAfter)}${c.reset}`);
  if (moved !== null) {
    console.log(`  Money moved   : ${c.bold}${inr(moved)}${c.reset}  ${c.dim}(expected ${inr(expected)} = ${succeeded} × ${inr(AMOUNT)})${c.reset}`);
    console.log(`  Invariant     : ${invariantOk ? c.green + "OK ✅  no double-spend" : c.red + "MISMATCH ❌"}${c.reset}`);
  }
  console.log(line());
})();
