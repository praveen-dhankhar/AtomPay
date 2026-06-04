import { useState, useEffect, useRef } from "react";
import { api } from "../api";
import BottomNav from "../components/BottomNav";
import "../styles/aichat.css";

// ── Simple Markdown Renderer ──
function renderMarkdown(text) {
  if (!text) return "";
  let html = text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/^### (.*$)/gm, '<h4 style="margin:8px 0 4px;color:var(--orange-light)">$1</h4>')
    .replace(/^## (.*$)/gm, '<h3 style="margin:10px 0 6px;color:var(--orange-light)">$1</h3>')
    .replace(/^# (.*$)/gm, '<h2 style="margin:12px 0 8px;color:var(--orange-light)">$1</h2>')
    .replace(/^[-•] (.*$)/gm, "<li>$1</li>")
    .replace(/^\d+\. (.*$)/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>")
    .replace(/\n{2,}/g, "</p><p>")
    .replace(/\n/g, "<br/>");
  return `<p>${html}</p>`;
}

// ── Tips Database ──
const TIPS_DATA = {
  general: {
    label: "General", icon: "📌",
    tips: [
      { text: "Follow the 50/30/20 rule: 50% needs, 30% wants, 20% savings", action: "Ask AI for personalized budget split" },
      { text: "Track every expense for a month to identify hidden spending patterns", action: "View Expense Tracker" },
      { text: "Set up automatic transfers to savings on payday — pay yourself first", action: "Learn more" },
      { text: "Review subscriptions monthly and cancel unused ones — the ₹99 ones add up fast", action: "Ask AI to analyze" },
      { text: "Use the 24-hour rule: wait before any non-essential purchase over ₹1,000", action: "Set reminder" },
    ]
  },
  budgeting: {
    label: "Budgeting", icon: "📊",
    tips: [
      { text: "Create category-wise monthly budgets — food, transport, entertainment, shopping", action: "Ask AI for help" },
      { text: "Envelope budgeting: allocate fixed amounts to each category digitally", action: "Learn more" },
      { text: "Track daily spending against weekly targets — small wins build momentum", action: "View expenses" },
      { text: "Set realistic budgets based on your last 3 months of actual spending data", action: "Ask AI to calculate" },
      { text: "Review and adjust your budget every month — a budget is a living document", action: "Get started" },
    ]
  },
  saving: {
    label: "Saving", icon: "🏦",
    tips: [
      { text: "Save first, spend later — treat savings as a non-negotiable fixed expense", action: "Set up auto-save" },
      { text: "Build an emergency fund covering 6 months of your essential expenses", action: "Calculate target" },
      { text: "Try the ₹500 note challenge: save every ₹500 note you receive for a month", action: "Start challenge" },
      { text: "Set specific savings goals with deadlines — 'Goa trip by December, ₹25,000'", action: "Create goal" },
      { text: "Automate everything: recurring transfers on salary day = zero willpower needed", action: "Learn more" },
    ]
  },
  investing: {
    label: "Investing", icon: "📈",
    tips: [
      { text: "Start SIPs even with ₹500/month — compound interest is the 8th wonder of the world", action: "Learn about SIPs" },
      { text: "Diversify your portfolio: don't put all money in a single instrument", action: "Learn more" },
      { text: "Keep 3-6 months expenses liquid, invest the rest for long-term growth", action: "Calculate reserves" },
      { text: "Index funds offer low-cost, passive investing — perfect for beginners", action: "Explore options" },
      { text: "Understand the difference between wants (iPhone) and investments (skills/courses)", action: "Ask AI" },
    ]
  },
  habits: {
    label: "Daily Habits", icon: "🔄",
    tips: [
      { text: "Cook at home more — eating out is 3-5x more expensive than home-cooked meals", action: "Track food spend" },
      { text: "Use public transport or carpooling to cut commute costs by 60-80%", action: "Calculate savings" },
      { text: "Buy generic/store brands for everyday items — same quality, 30% cheaper", action: "Learn more" },
      { text: "Plan weekly meals to reduce food waste and eliminate impulse grocery buying", action: "Start planning" },
      { text: "Use cashback and rewards strategically — but never spend extra just for rewards", action: "Optimize rewards" },
    ]
  },
};

// ── Quick Suggestion Chips ──
const SUGGESTIONS = [
  "What's my balance?",
  "Show spending analysis",
  "How much daily limit left?",
  "Last 5 transactions",
  "Give me saving tips",
  "Who do I send most money to?",
];

export default function AiChat({ token, user }) {
  const [activeTab, setActiveTab] = useState("chat");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [agentOnline, setAgentOnline] = useState(true);
  const [tipCategory, setTipCategory] = useState("general");

  // Expense tracker state
  const [expenseData, setExpenseData] = useState(null);
  const [expensePeriod, setExpensePeriod] = useState(30);
  const [expenseLoading, setExpenseLoading] = useState(false);

  // Insights state
  const [insightsData, setInsightsData] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Check agent health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api("/agent/health", {}, token);
        setAgentOnline(true);
      } catch {
        setAgentOnline(false);
      }
    };
    checkHealth();
  }, []);

  // Load expense data when tab is opened
  useEffect(() => {
    if (activeTab === "expenses" && !expenseData) {
      loadExpenseData();
    }
    if (activeTab === "insights" && !insightsData) {
      loadInsightsData();
    }
  }, [activeTab]);

  // Reload expense data when period changes
  useEffect(() => {
    if (activeTab === "expenses") {
      loadExpenseData();
    }
  }, [expensePeriod]);

  const loadExpenseData = async () => {
    setExpenseLoading(true);
    try {
      const msg = `Analyze my spending for the last ${expensePeriod} days. Give me the raw data in this exact JSON format and nothing else: {"total_sent": number, "sent_count": number, "total_received": number, "received_count": number, "net_flow": number, "top_recipients": [{"username": string, "amount": number, "count": number}], "daily_breakdown": [{"date": string, "amount": number, "count": number}]}`;
      const res = await api("/agent/chat", {
        method: "POST",
        body: JSON.stringify({ message: msg }),
      }, token);

      // Try to parse JSON from response
      try {
        const jsonMatch = res.response.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          setExpenseData(JSON.parse(jsonMatch[0]));
        }
      } catch {
        // If we can't parse, ask again with simpler query
        setExpenseData(null);
      }
    } catch (err) {
      console.error("Failed to load expense data:", err);
    } finally {
      setExpenseLoading(false);
    }
  };

  const loadInsightsData = async () => {
    setInsightsLoading(true);
    try {
      const [balRes, limitRes] = await Promise.all([
        api("/wallet/balance", {}, token),
        api("/agent/chat", {
          method: "POST",
          body: JSON.stringify({ message: "Check my daily limit usage. Reply with ONLY this JSON: {\"daily_limit\": number, \"used\": number, \"remaining\": number, \"percentage_used\": number, \"transaction_count_today\": number}" }),
        }, token),
      ]);

      let limitData = null;
      try {
        const jsonMatch = limitRes.response.match(/\{[\s\S]*\}/);
        if (jsonMatch) limitData = JSON.parse(jsonMatch[0]);
      } catch { /* ignore */ }

      setInsightsData({
        balance: balRes.balance || 0,
        walletStatus: balRes.status || "Active",
        currency: balRes.currency || "INR",
        dailyLimit: limitData,
      });
    } catch (err) {
      console.error("Failed to load insights:", err);
    } finally {
      setInsightsLoading(false);
    }
  };

  const sendMessage = async (msg) => {
    const text = msg || input.trim();
    if (!text || loading) return;

    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    const userMsg = { role: "user", content: text, time: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await api("/agent/chat", {
        method: "POST",
        body: JSON.stringify({ message: text }),
      }, token);

      const assistantMsg = { role: "assistant", content: res.response, time: new Date() };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg = {
        role: "assistant",
        content: "⚠️ Sorry, I couldn't process your request. The AI Agent might be offline. Please try again later.",
        time: new Date()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = async () => {
    try {
      await api("/agent/clear-history", {
        method: "POST",
        body: JSON.stringify({}),
      }, token);
    } catch { /* ignore */ }
    setMessages([]);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const autoGrow = (e) => {
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
  };

  const formatTime = (d) =>
    new Date(d).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });

  const formatAmount = (n) =>
    new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n || 0);

  const formatDate = (d) => {
    const date = new Date(d);
    return date.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
  };

  // ── Tab Definitions ──
  const TABS = [
    { id: "chat", icon: "💬", label: "Chat" },
    { id: "expenses", icon: "📊", label: "Expenses" },
    { id: "tips", icon: "💡", label: "Tips" },
    { id: "insights", icon: "🔍", label: "Insights" },
  ];

  return (
    <div className="ai-page">
      {/* Header */}
      <div className="ai-header">
        <div className="ai-header-left">
          <div className="ai-logo">✦</div>
          <div className="ai-header-title">
            <h2>AtomPay AI</h2>
            <span>Your Personal Finance Assistant</span>
          </div>
        </div>
        <div className="ai-header-actions">
          <div className={`ai-status ${agentOnline ? "" : "offline"}`}>
            <span className="ai-status-dot" />
            {agentOnline ? "Online" : "Offline"}
          </div>
          {activeTab === "chat" && messages.length > 0 && (
            <button className="ai-header-btn danger" onClick={clearChat} title="Clear chat">
              🗑
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="ai-tabs">
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`ai-tab ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="ai-tab-icon">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* ════════════════ CHAT TAB ════════════════ */}
      {activeTab === "chat" && (
        <div className="ai-chat-container">
          <div className="ai-messages">
            {messages.length === 0 && !loading ? (
              <div className="ai-welcome">
                <div className="ai-welcome-icon">✦</div>
                <h3>Hey {user?.username} 👋</h3>
                <p>I'm your AI-powered financial assistant. Ask me anything about your wallet, transactions, spending patterns, or get personalized money-saving tips!</p>
                <div className="ai-caps-grid">
                  {[
                    { icon: "💰", title: "Balance & Wallet", desc: "Check balance, wallet status" },
                    { icon: "📊", title: "Expense Tracking", desc: "Analyze your spending habits" },
                    { icon: "🔍", title: "Smart Search", desc: "Find any transaction instantly" },
                    { icon: "💡", title: "Money Tips", desc: "Personalized saving advice" },
                  ].map((cap, i) => (
                    <div
                      key={i}
                      className="ai-cap-card"
                      onClick={() => sendMessage(
                        i === 0 ? "What's my balance?" :
                        i === 1 ? "Analyze my spending this month" :
                        i === 2 ? "Show my recent transactions" :
                        "Give me tips to save money"
                      )}
                    >
                      <div className="ai-cap-icon">{cap.icon}</div>
                      <div className="ai-cap-title">{cap.title}</div>
                      <div className="ai-cap-desc">{cap.desc}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, i) => (
                  <div key={i} className={`ai-msg ${msg.role}`}>
                    <div className="ai-msg-avatar">
                      {msg.role === "assistant" ? "✦" : user?.username?.[0]?.toUpperCase() || "U"}
                    </div>
                    <div>
                      <div
                        className="ai-msg-bubble"
                        dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                      />
                      <div className="ai-msg-time">{formatTime(msg.time)}</div>
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="ai-typing">
                    <div className="ai-msg-avatar" style={{
                      background: "linear-gradient(135deg, var(--orange), #FF9100)",
                      width: 32, height: 32, borderRadius: 10,
                      display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14
                    }}>✦</div>
                    <div className="ai-typing-bubble">
                      <div className="ai-typing-dot" />
                      <div className="ai-typing-dot" />
                      <div className="ai-typing-dot" />
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Suggestions */}
          {messages.length === 0 && (
            <div className="ai-suggestions">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} className="ai-suggestion-chip" onClick={() => sendMessage(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="ai-input-area">
            <div className="ai-input-wrap">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => { setInput(e.target.value); autoGrow(e); }}
                onKeyDown={handleKeyDown}
                placeholder="Ask me anything about your finances..."
                rows={1}
                disabled={loading}
              />
              <button
                className="ai-send-btn"
                onClick={() => sendMessage()}
                disabled={!input.trim() || loading}
              >
                ↑
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ════════════════ EXPENSES TAB ════════════════ */}
      {activeTab === "expenses" && (
        <div className="ai-expense-tab">
          {/* Period Selector */}
          <div className="ai-period-selector">
            {[7, 14, 30, 60, 90].map(d => (
              <button
                key={d}
                className={`ai-period-btn ${expensePeriod === d ? "active" : ""}`}
                onClick={() => setExpensePeriod(d)}
              >
                {d}d
              </button>
            ))}
          </div>

          {expenseLoading ? (
            <div className="ai-loading"><div className="ai-loading-spinner" /></div>
          ) : expenseData ? (
            <>
              {/* Summary Cards */}
              <div className="ai-expense-summary">
                <div className="ai-expense-card">
                  <div className="card-icon">📤</div>
                  <div className="card-value red">{formatAmount(expenseData.total_sent)}</div>
                  <div className="card-label">Total Sent ({expenseData.sent_count || 0} txns)</div>
                </div>
                <div className="ai-expense-card">
                  <div className="card-icon">📥</div>
                  <div className="card-value green">{formatAmount(expenseData.total_received)}</div>
                  <div className="card-label">Total Received ({expenseData.received_count || 0} txns)</div>
                </div>
                <div className="ai-expense-card">
                  <div className="card-icon">{(expenseData.net_flow || 0) >= 0 ? "📈" : "📉"}</div>
                  <div className={`card-value ${(expenseData.net_flow || 0) >= 0 ? "green" : "red"}`}>
                    {formatAmount(Math.abs(expenseData.net_flow || 0))}
                  </div>
                  <div className="card-label">Net Flow ({(expenseData.net_flow || 0) >= 0 ? "Positive" : "Negative"})</div>
                </div>
                <div className="ai-expense-card">
                  <div className="card-icon">📊</div>
                  <div className="card-value orange">
                    {formatAmount((expenseData.total_sent || 0) / (expensePeriod || 1))}
                  </div>
                  <div className="card-label">Avg Daily Spend</div>
                </div>
              </div>

              {/* Top Recipients */}
              {expenseData.top_recipients?.length > 0 && (
                <div className="ai-top-recipients">
                  <div className="ai-section-title">🏆 Top Recipients</div>
                  {expenseData.top_recipients.map((r, i) => (
                    <div key={i} className="ai-recipient-item">
                      <div className="ai-recipient-rank">{i + 1}</div>
                      <div className="ai-recipient-info">
                        <div className="ai-recipient-name">@{r.username}</div>
                        <div className="ai-recipient-count">{r.count} transactions</div>
                      </div>
                      <div className="ai-recipient-amount">{formatAmount(r.amount)}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Daily Breakdown */}
              {expenseData.daily_breakdown?.length > 0 && (
                <div className="ai-daily-chart">
                  <div className="ai-section-title">📅 Daily Spending</div>
                  <div className="ai-daily-bar-container">
                    {expenseData.daily_breakdown.slice(0, 10).map((d, i) => {
                      const maxAmount = Math.max(...expenseData.daily_breakdown.map(x => x.amount));
                      const pct = maxAmount > 0 ? (d.amount / maxAmount) * 100 : 0;
                      return (
                        <div key={i} className="ai-daily-bar-row">
                          <div className="ai-daily-bar-label">{formatDate(d.date)}</div>
                          <div className="ai-daily-bar-track">
                            <div className="ai-daily-bar-fill" style={{ width: `${Math.max(pct, 8)}%` }}>
                              <span className="ai-daily-bar-amount">{formatAmount(d.amount)}</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="ai-empty-state">
              <div className="empty-icon">📊</div>
              <p>No expense data available yet. Start making transactions to see your spending analysis here!</p>
              <button className="empty-btn" onClick={loadExpenseData}>Retry Loading</button>
            </div>
          )}
          <div className="ai-bottom-pad" />
        </div>
      )}

      {/* ════════════════ TIPS TAB ════════════════ */}
      {activeTab === "tips" && (
        <div className="ai-tips-tab">
          {/* Category Selector */}
          <div className="ai-tips-categories">
            {Object.entries(TIPS_DATA).map(([key, cat]) => (
              <button
                key={key}
                className={`ai-tip-cat-btn ${tipCategory === key ? "active" : ""}`}
                onClick={() => setTipCategory(key)}
              >
                {cat.icon} {cat.label}
              </button>
            ))}
          </div>

          {/* Tips List */}
          {TIPS_DATA[tipCategory]?.tips.map((tip, i) => (
            <div key={i} className="ai-tip-card">
              <div className="ai-tip-number">{i + 1}</div>
              <div className="ai-tip-content">
                <div className="ai-tip-text">{tip.text}</div>
                <div className="ai-tip-action" onClick={() => {
                  setActiveTab("chat");
                  setTimeout(() => sendMessage(`Tell me more about: "${tip.text}"`), 100);
                }}>
                  💬 {tip.action} →
                </div>
              </div>
            </div>
          ))}
          <div className="ai-bottom-pad" />
        </div>
      )}

      {/* ════════════════ INSIGHTS TAB ════════════════ */}
      {activeTab === "insights" && (
        <div className="ai-insights-tab">
          {insightsLoading ? (
            <div className="ai-loading"><div className="ai-loading-spinner" /></div>
          ) : insightsData ? (
            <>
              {/* Balance Card */}
              <div className="ai-insight-card">
                <div className="ai-insight-header">
                  <span className="ai-insight-icon">💰</span>
                  <span className="ai-insight-title">Current Balance</span>
                </div>
                <div className="ai-insight-value" style={{ color: "var(--green)" }}>
                  {formatAmount(insightsData.balance)}
                </div>
                <div className="ai-insight-label">
                  Wallet: {insightsData.walletStatus} • {insightsData.currency}
                </div>
              </div>

              {/* Daily Limit Card */}
              {insightsData.dailyLimit && (
                <div className="ai-insight-card">
                  <div className="ai-insight-header">
                    <span className="ai-insight-icon">🛡️</span>
                    <span className="ai-insight-title">Daily Transfer Limit</span>
                  </div>
                  <div className="ai-insight-value" style={{
                    color: (insightsData.dailyLimit.percentage_used || 0) > 80 ? "var(--red)" : "var(--orange)"
                  }}>
                    {formatAmount(insightsData.dailyLimit.used)} <span style={{ fontSize: 16, color: "var(--text2)" }}>/ ₹1,00,000</span>
                  </div>
                  <div className="ai-insight-label">
                    {formatAmount(insightsData.dailyLimit.remaining)} remaining • {insightsData.dailyLimit.transaction_count_today || 0} transactions today
                  </div>
                  <div className="ai-insight-bar">
                    <div
                      className="ai-insight-bar-fill"
                      style={{
                        width: `${insightsData.dailyLimit.percentage_used || 0}%`,
                        background: (insightsData.dailyLimit.percentage_used || 0) > 80
                          ? "linear-gradient(90deg, var(--red), #FF5252)"
                          : "linear-gradient(90deg, var(--orange), #FF9100)"
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Quick Actions */}
              <div className="ai-insight-card">
                <div className="ai-insight-header">
                  <span className="ai-insight-icon">⚡</span>
                  <span className="ai-insight-title">Quick Analysis</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
                  {[
                    { label: "Full spending analysis", query: "Give me a detailed spending analysis for this month" },
                    { label: "Weekly comparison", query: "Compare my spending this week vs last week" },
                    { label: "Savings potential", query: "Based on my spending patterns, how much could I save?" },
                    { label: "Transaction patterns", query: "What patterns do you see in my transactions?" },
                  ].map((action, i) => (
                    <button
                      key={i}
                      className="ai-suggestion-chip"
                      style={{ textAlign: "left", width: "100%" }}
                      onClick={() => {
                        setActiveTab("chat");
                        setTimeout(() => sendMessage(action.query), 100);
                      }}
                    >
                      → {action.label}
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="ai-empty-state">
              <div className="empty-icon">🔍</div>
              <p>Unable to load insights. Make sure the AI Agent is running.</p>
              <button className="empty-btn" onClick={loadInsightsData}>Retry</button>
            </div>
          )}
          <div className="ai-bottom-pad" />
        </div>
      )}

      <BottomNav active="ai" navigate={() => {}} />
    </div>
  );
}
