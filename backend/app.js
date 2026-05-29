require('dotenv').config();
const express = require("express");
const cors = require("cors");
const authRouter = require("./routes/auth.routes");
const transactionRouter = require("./routes/transection.routes");
const walletRouter = require("./routes/wallet.routes");

const app = express();
app.set("trust proxy", 1);

// ── Security: restrict CORS to known origins ──
const allowedOrigins = (process.env.CORS_ORIGINS || "*").split(",").map(s => s.trim());
app.use(cors({
    origin: allowedOrigins.includes("*") ? "*" : allowedOrigins,
    methods: ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization", "Idempotency-Key"]
}));

// ── Security: limit request body size to prevent large-payload DoS ──
app.use(express.json({ limit: "100kb" }));

// ── Security: set essential security headers ──
app.use((req, res, next) => {
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("X-Frame-Options", "DENY");
    res.setHeader("X-XSS-Protection", "1; mode=block");
    res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
    res.removeHeader("X-Powered-By");
    next();
});

app.get("/api", async function (req, res) {
    res.status(200).json({
        msg: "working properly",
        maintenance: process.env.MAINTENANCE_MODE === "true"
    })
});

// ── Maintenance Mode: return 503 for all other routes when enabled ──
app.use((req, res, next) => {
    if (process.env.MAINTENANCE_MODE === "true") {
        return res.status(503).json({
            msg: "AtomPay is currently under maintenance. We'll be back shortly!",
            maintenance: true
        });
    }
    next();
});
app.use("/api/auth", authRouter);
app.use("/api/wallet", walletRouter);
app.use("/api/transaction", transactionRouter);

module.exports = app;
