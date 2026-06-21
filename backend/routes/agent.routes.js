const express = require("express");
const router = express.Router();
const authMiddleware = require("../middlewares/auth.middlewares");
const { rateLimiter } = require("../middlewares/rateLimiter");

const AGENT_URL = (process.env.AGENT_URL || "http://localhost:8000").replace(/\/$/, "");

// Per-user limit on the LLM-backed chat endpoint to prevent API billing exhaustion.
// Keyed by authenticated user id, so it must run after authMiddleware.
const aiChatLimiter = rateLimiter({
    keyPrefix: "rl:ai-chat",
    windowMs: 60 * 1000,
    max: 10,
    identifier: (req) => req.user.id,
    message: "You're sending messages too fast. Please wait a minute before chatting again.",
});

/**
 * POST /api/agent/chat
 * Proxies chat messages to the Python AtomAI, injecting the authenticated userId.
 */
router.post("/chat", authMiddleware, aiChatLimiter, async (req, res) => {
    try {
        const { message } = req.body;

        if (!message || !message.trim()) {
            return res.status(400).json({ msg: "Message is required" });
        }

        const response = await fetch(`${AGENT_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: message.trim(),
                user_id: req.user.id,
            }),
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            return res.status(response.status).json({
                msg: errData.detail || "AtomAI is temporarily unavailable",
            });
        }

        const data = await response.json();
        return res.status(200).json(data);
    } catch (err) {
        console.error("Agent proxy error:", err.message);
        return res.status(503).json({
            msg: "AtomAI is currently offline. Please try again later.",
        });
    }
});

/**
 * POST /api/agent/clear-history
 * Clears conversation history for the authenticated user.
 */
router.post("/clear-history", authMiddleware, async (req, res) => {
    try {
        const response = await fetch(`${AGENT_URL}/clear-history`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: req.user.id }),
        });

        const data = await response.json();
        return res.status(200).json(data);
    } catch (err) {
        console.error("Agent clear-history error:", err.message);
        return res.status(503).json({ msg: "AtomAI is currently offline." });
    }
});

/**
 * Helper: forward a JSON POST to the AtomAI, injecting the authenticated userId.
 */
async function proxyToAgent(path, req, res, extraBody = {}) {
    try {
        const response = await fetch(`${AGENT_URL}${path}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...req.body, ...extraBody, user_id: req.user.id }),
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            return res.status(response.status).json({
                msg: errData.detail || "AtomAI is temporarily unavailable",
            });
        }

        const data = await response.json();
        return res.status(200).json(data);
    } catch (err) {
        console.error(`Agent proxy error (${path}):`, err.message);
        return res.status(503).json({ msg: "AtomAI is currently offline. Please try again later." });
    }
}

/**
 * POST /api/agent/analytics
 * Deterministic analytics bundle (spending, MoM trends, recurring, forecast, budget).
 */
router.post("/analytics", authMiddleware, (req, res) => proxyToAgent("/analytics", req, res));

/**
 * POST /api/agent/memory — read current short-term memory for the user.
 */
router.post("/memory", authMiddleware, (req, res) => proxyToAgent("/memory", req, res));

/**
 * POST /api/agent/memory/budget — set the user's monthly budget.
 */
router.post("/memory/budget", authMiddleware, (req, res) => proxyToAgent("/memory/budget", req, res));

/**
 * POST /api/agent/memory/savings-goal — set the user's savings goal.
 */
router.post("/memory/savings-goal", authMiddleware, (req, res) => proxyToAgent("/memory/savings-goal", req, res));

/**
 * POST /api/agent/memory/clear — clear the user's short-term memory.
 */
router.post("/memory/clear", authMiddleware, (req, res) => proxyToAgent("/memory/clear", req, res));

/**
 * GET /api/agent/capabilities
 * Returns the agent's capabilities for the frontend UI.
 */
router.get("/capabilities", authMiddleware, async (req, res) => {
    try {
        const response = await fetch(`${AGENT_URL}/capabilities`);
        const data = await response.json();
        return res.status(200).json(data);
    } catch (err) {
        return res.status(503).json({ msg: "AtomAI is currently offline." });
    }
});

/**
 * GET /api/agent/health
 * Health check for the AtomAI service.
 */
router.get("/health", async (req, res) => {
    try {
        const response = await fetch(`${AGENT_URL}/health`);
        const data = await response.json();
        return res.status(200).json(data);
    } catch (err) {
        return res.status(503).json({
            status: "offline",
            msg: "AtomAI is not running",
        });
    }
});

module.exports = router;
