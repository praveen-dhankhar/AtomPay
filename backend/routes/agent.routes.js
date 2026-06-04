const express = require("express");
const router = express.Router();
const authMiddleware = require("../middlewares/auth.middlewares");

const AGENT_URL = (process.env.AGENT_URL || "http://localhost:8000").replace(/\/$/, "");

/**
 * POST /api/agent/chat
 * Proxies chat messages to the Python AI Agent, injecting the authenticated userId.
 */
router.post("/chat", authMiddleware, async (req, res) => {
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
                msg: errData.detail || "AI Agent is temporarily unavailable",
            });
        }

        const data = await response.json();
        return res.status(200).json(data);
    } catch (err) {
        console.error("Agent proxy error:", err.message);
        return res.status(503).json({
            msg: "AI Agent is currently offline. Please try again later.",
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
        return res.status(503).json({ msg: "AI Agent is currently offline." });
    }
});

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
        return res.status(503).json({ msg: "AI Agent is currently offline." });
    }
});

/**
 * GET /api/agent/health
 * Health check for the AI Agent service.
 */
router.get("/health", async (req, res) => {
    try {
        const response = await fetch(`${AGENT_URL}/health`);
        const data = await response.json();
        return res.status(200).json(data);
    } catch (err) {
        return res.status(503).json({
            status: "offline",
            msg: "AI Agent is not running",
        });
    }
});

module.exports = router;
