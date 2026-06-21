#!/usr/bin/env node
/**
 * AtomPay — load test runner (reproducible benchmarks for docs/LOAD_TEST.md).
 *
 * Benchmarks the application layer (GET /api) and, if a TOKEN is given, the
 * Redis-cached read path (GET /api/wallet/balance). Uses autocannon (devDep).
 *
 * ── Usage ─────────────────────────────────────────────────────────────
 *   node scripts/loadtest.js                 # app-layer only (no auth)
 *   TOKEN="<access token>" node scripts/loadtest.js   # + cached-read test
 *
 * ── Options (env vars) ────────────────────────────────────────────────
 *   BASE         API base url   (default http://localhost:3000/api)
 *   DURATION     seconds/run    (default 10)
 *   CONNECTIONS  comma list     (default "50,100,200")
 *   TOKEN        JWT access token to also benchmark /wallet/balance
 */

const autocannon = require("autocannon");

const BASE = process.env.BASE || "http://localhost:3000/api";
const DURATION = Number(process.env.DURATION || 10);
const LEVELS = (process.env.CONNECTIONS || "50,100,200").split(",").map(s => Number(s.trim()));
const TOKEN = process.env.TOKEN;

const run = (title, url, connections, headers) =>
  new Promise((resolve, reject) => {
    autocannon({ url, connections, duration: DURATION, headers, title }, (err, r) => {
      if (err) return reject(err);
      resolve({
        connections,
        rps: Math.round(r.requests.average),
        p50: r.latency.p50,
        p99: r.latency.p99,
        non2xx: r.non2xx,
        errors: r.errors,
        timeouts: r.timeouts,
      });
    });
  });

const table = (title, rows) => {
  console.log(`\n${title}`);
  console.log("  conn |   req/s | p50(ms) | p99(ms) | non-2xx | errors");
  console.log("  -----+---------+---------+---------+---------+-------");
  for (const x of rows) {
    console.log(
      `  ${String(x.connections).padStart(4)} | ${String(x.rps).padStart(7)} | ` +
      `${String(x.p50).padStart(7)} | ${String(x.p99).padStart(7)} | ` +
      `${String(x.non2xx).padStart(7)} | ${String(x.errors).padStart(6)}`
    );
  }
};

(async () => {
  console.log(`AtomPay load test → ${BASE}   (duration ${DURATION}s/run)\n`);

  // Warm up so the first measured run isn't paying cold-start costs.
  process.stdout.write("Warming up… ");
  await run("warmup", `${BASE}`, 20).catch(() => {});
  console.log("done");

  const appRows = [];
  for (const c of LEVELS) appRows.push(await run(`/api c=${c}`, `${BASE}`, c));
  table("① Application layer — GET /api (no datastore)", appRows);

  if (TOKEN) {
    const hdr = { Authorization: `Bearer ${TOKEN}` };
    await run("warmup-balance", `${BASE}/wallet/balance`, 10, hdr).catch(() => {});
    const readRows = [];
    for (const c of LEVELS) readRows.push(await run(`/balance c=${c}`, `${BASE}/wallet/balance`, c, hdr));
    table("② Cached read — GET /api/wallet/balance (Redis)", readRows);
  } else {
    console.log("\n② Cached-read test skipped — set TOKEN to include it.");
  }

  console.log("\nDone.");
  process.exit(0);
})();
