"""Generate AtomPay high-level design diagram as PNG."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ---- palette ----
BG       = "#0f172a"
NODE     = "#064e3b"; NODE_E   = "#10b981"
PY       = "#312e81"; PY_E     = "#818cf8"
STORE    = "#1f2937"; STORE_E  = "#f59e0b"
FE       = "#0c4a6e"; FE_E     = "#38bdf8"
LB       = "#3f3f46"; LB_E     = "#a1a1aa"
GROUP    = "#111827"; GROUP_E  = "#334155"
TXT      = "#f8fafc"; SUB      = "#cbd5e1"

fig, ax = plt.subplots(figsize=(15, 11))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 100); ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, fc, ec, title, lines=None, ts=12, ls=8.5, r=0.025, lw=2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.3,rounding_size={r*100}",
                                fc=fc, ec=ec, lw=lw, mutation_aspect=0.6, zorder=3))
    cy = y + h - 4.2 if lines else y + h / 2
    ax.text(x + w / 2, cy, title, ha="center", va="center",
            color=TXT, fontsize=ts, fontweight="bold", zorder=4)
    if lines:
        ax.text(x + w / 2, cy - 2.0, "\n".join(lines), ha="center", va="top",
                color=SUB, fontsize=ls, linespacing=1.4, zorder=4)


def group(x, y, w, h, label, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.5",
                                fc=GROUP, ec=ec, lw=1.4, ls=(0, (6, 4)), alpha=0.55, zorder=1))
    ax.text(x + 1.5, y + h - 1.6, label, ha="left", va="top",
            color=ec, fontsize=11, fontweight="bold", zorder=2)


def arrow(p1, p2, color=SUB, style="-", label=None, lw=2.0, rad=0.0, lpos=0.5, loff=(0, 0)):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=18,
                                 color=color, lw=lw, ls=style,
                                 connectionstyle=f"arc3,rad={rad}", zorder=2,
                                 shrinkA=2, shrinkB=2))
    if label:
        mx = p1[0] + (p2[0] - p1[0]) * lpos + loff[0]
        my = p1[1] + (p2[1] - p1[1]) * lpos + loff[1]
        ax.text(mx, my, label, ha="center", va="center", color=color, fontsize=7.8,
                fontweight="bold", zorder=5,
                bbox=dict(boxstyle="round,pad=0.25", fc=BG, ec="none", alpha=0.85))


# ---- title ----
ax.text(50, 97.5, "AtomPay — High-Level Design", ha="center", color=TXT,
        fontsize=22, fontweight="bold")
ax.text(50, 94.2, "Distributed digital wallet · Node.js + Python AI + React", ha="center",
        color=SUB, fontsize=12)

# ---- Client ----
group(33, 83, 34, 9.5, "CLIENT LAYER", FE_E)
box(36, 83.8, 28, 6, FE, FE_E, "React + Vite Frontend",
    ["Auth · Dashboard · QR scan & pay", "generates Idempotency-Key"], ts=12, ls=8.5)

# ---- Load balancer ----
box(40.5, 76.5, 19, 4.2, LB, LB_E, "Load Balancer", None, ts=12)

# ---- Backend (gatekeeper) ----
group(8, 50, 84, 22, "NODE.js + EXPRESS BACKEND   ·   trust boundary / gatekeeper", NODE_E)
box(12, 53.5, 38, 15, NODE, NODE_E, "API Instances (N)",
    ["JWT access(15m) + refresh(7d)", "Zod validation",
     "rate-limit + idempotency check", "transfer orchestration (ACID)"], ts=13, ls=9.5)
box(54, 53.5, 34, 15, NODE, NODE_E, "BullMQ Worker",
    ["(separate process)", "transaction emails", "audit logs", "retries + backoff"], ts=13, ls=9.5)

# ---- AI service ----
group(58, 31, 30, 14, "PYTHON AI SERVICE — isolated", PY_E)
box(60, 32, 26, 9.5, PY, PY_E, "FastAPI + LangGraph",
    ["DeepSeek deepseek-chat", "analyze / summarize spend", "*** READ-ONLY ***"], ts=12, ls=9)

# ---- Data layer ----
group(8, 6, 84, 22, "DATA & INFRA", STORE_E)
box(11, 9, 24, 16, STORE, STORE_E, "MongoDB",
    ["multi-doc ACID txns", "double-balance check", "connection pool"], ts=13, ls=9.5)
box(38, 9, 24, 16, STORE, STORE_E, "Redis  (fail-open)",
    ["SETNX idempotency", "sorted-set rate limit", "read-through cache", "BullMQ queues"], ts=13, ls=9.5)
box(65, 9, 24, 16, STORE, STORE_E, "NodeMailer",
    ["sync OTP (2FA)", "async notifications"], ts=13, ls=9.5)

# ---- arrows ----
arrow((50, 85), (50, 80.7), color=FE_E, label="HTTPS", lpos=0.5, loff=(-4, 0))
arrow((50, 76.5), (50, 72), color=FE_E)

# AI chat (dashed proxy)
arrow((48, 53.5), (68, 41.5), color=PY_E, style=(0, (5, 3)),
      label="authorize + proxy\n(read-only)", rad=-0.2, lpos=0.45, loff=(-2, 4))
arrow((80, 41.5), (60, 53.5), color=PY_E, style=(0, (5, 3)),
      label="read-only queries", rad=-0.2, lpos=0.5, loff=(12, 1))

# API -> Mongo
arrow((22, 53.5), (20, 25), color=STORE_E, label="ACID transaction", lpos=0.45, loff=(-8, 0))
# API -> Redis
arrow((34, 53.5), (45, 25), color=STORE_E, label="SETNX · rate-limit\ncache · enqueue",
      rad=0.05, lpos=0.4, loff=(-9, 0))
# API -> Mailer (sync OTP)
arrow((46, 53.5), (70, 25), color=STORE_E, label="sync OTP", rad=-0.12, lpos=0.78, loff=(-4, 2))

# Worker -> Redis (consume)
arrow((62, 53.5), (52, 25), color=STORE_E, label="consume jobs", rad=0.05, lpos=0.18, loff=(-7, 0))
# Worker -> Mailer
arrow((81, 53.5), (88, 25), color=STORE_E, label="async emails", lpos=0.85, loff=(7, 0))

# ---- legend ----
legend = [
    ("Node.js backend", NODE_E),
    ("Python AI (read-only)", PY_E),
    ("Data / infra store", STORE_E),
    ("Frontend", FE_E),
]
for i, (lab, c) in enumerate(legend):
    lx = 10 + i * 21
    ax.add_patch(plt.Rectangle((lx, 1.5), 1.6, 1.6, fc=c, ec="none"))
    ax.text(lx + 2.2, 2.3, lab, color=SUB, fontsize=9, va="center")

plt.tight_layout()
out = "docs/atompay_hld.png"
plt.savefig(out, dpi=200, facecolor=BG, bbox_inches="tight")
print("saved", out)
