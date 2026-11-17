"""
Fig. 1 of the PrivAgent v2 paper: the v2 architecture (primary configuration).

Drawn with matplotlib only (no data inputs). Every component shown is described in Section IV and
in ledger rows S1 (pipeline, servers), S4 (precedence), S5 (handoff scoring, R1-R3, provenance),
S6 (RESTRICTED, approval binding, HKDF keys, hash-chained log), S7 (enforced provenance) and
S14 (decision record).

Outputs (this directory): v2_f0_architecture.png, .svg and .pdf, sized for a full-width
(two-column) IEEE figure, 7.16 in wide.

    python research_paper/v2/figures/make_architecture_v2.py
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "v2_f0_architecture")

INK, MUTED = "#1f2328", "#59636e"
BOX_FILL, BOX_EDGE = "#f6f8fa", "#59636e"
BAND_FILL, BAND_EDGE = "#eaf1fb", "#1f5fa8"
GATE_FILL = "#fdf1e3"     # approval gate (orange family, matches the paper's pair colour)
STOP_FILL = "#f2f2f2"
ACCENT = "#1f5fa8"

W, H = 7.16, 4.55
plt.rcParams.update({"font.family": "Arial", "font.size": 7.5, "svg.fonttype": "none",
                     "pdf.fonttype": 42})

fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")


def box(x0, y0, x1, y1, title, sub=None, fill=BOX_FILL, edge=BOX_EDGE, lw=0.8, tsize=8, ssize=6.8,
        title_dy=0.0, mono_sub=False):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=0.05",
                                fc=fill, ec=edge, lw=lw))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if sub:
        ax.text(cx, cy + 0.11 + title_dy, title, ha="center", va="center", fontsize=tsize,
                fontweight="bold", color=INK)
        ax.text(cx, cy - 0.04 + title_dy, sub, ha="center", va="top", fontsize=ssize, color=MUTED,
                linespacing=1.15, family="DejaVu Sans Mono" if mono_sub else None)
    else:
        ax.text(cx, cy, title, ha="center", va="center", fontsize=tsize, fontweight="bold", color=INK,
                linespacing=1.15)


def arrow(xy0, xy1, color=INK, ls="-", lw=0.9, label=None, lx=0.0, ly=0.07, lha="center",
          lsize=6.6, lcolor=None):
    ax.annotate("", xy=xy1, xytext=xy0,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, ls=ls, mutation_scale=7,
                                shrinkA=0, shrinkB=0))
    if label:
        mx, my = (xy0[0] + xy1[0]) / 2 + lx, (xy0[1] + xy1[1]) / 2 + ly
        ax.text(mx, my, label, ha=lha, va="bottom", fontsize=lsize, color=lcolor or color)


def line(points, color=INK, lw=0.9, ls="-"):
    xs, ys = zip(*points)
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, solid_capstyle="butt")


def group_label(x, y, text, color=MUTED):
    ax.text(x, y, text, ha="left", va="bottom", fontsize=7, color=color, fontweight="bold")


# ---------------------------------------------------------------- row A: agents
AY0, AY1 = 3.55, 4.20
group_label(0.15, 4.27, "LANGGRAPH PIPELINE (FOUR AGENTS)")
agents = [(0.15, 1.25, "Orchestrator", "plans the task"),
          (1.80, 2.90, "Retriever", "calls governed\nread tools"),
          (3.45, 4.55, "Analyst", "synthesises;\ndeclares\nsensitivity"),
          (5.10, 6.20, "Writer", "composes; may\ncall send_result")]
for x0, x1, t, s in agents:
    box(x0, AY0, x1, AY1, t, s, title_dy=0.07)
ym = (AY0 + AY1) / 2 + 0.08
arrow((1.25, ym), (1.80, ym), label="plan", ly=0.04)
arrow((2.90, ym), (3.45, ym), label="handoff 1", ly=0.04)
arrow((4.55, ym), (5.10, ym), label="handoff 2", ly=0.04)

# ---------------------------------------------------------------- row B: interception band
BY0, BY1 = 1.62, 3.12
ax.add_patch(FancyBboxPatch((0.15, BY0), 6.05, BY1 - BY0, boxstyle="round,pad=0,rounding_size=0.06",
                            fc=BAND_FILL, ec=BAND_EDGE, lw=1.1))
ax.text(0.27, BY1 - 0.08, "SINGLE INTERCEPTION POINT", ha="left", va="top", fontsize=7.2,
        fontweight="bold", color=ACCENT)
ax.text(0.27, BY1 - 0.24, "TrajectoryMonitor.evaluate(): every proposed call, before execution",
        ha="left", va="top", fontsize=6.8, color=INK, family="DejaVu Sans Mono")

# inputs into the band from the agents
for x, lab in [(2.35, "tool calls"), (5.65, "tool calls,\nsend_result")]:
    arrow((x, AY0), (x, BY1), label=lab, lx=0.05, ly=-0.06, lha="left")
for x in (3.175, 4.825):
    arrow((x, ym - 0.04), (x, BY1), color=ACCENT, ls=(0, (3, 2)))
ax.text(4.00, 3.30, "scored handoffs\n(pseudo-actions)", ha="center", va="center", fontsize=6.6,
        color=ACCENT)

IY0, IY1 = 1.78, 2.70
box(0.30, IY0, 1.45, IY1, "Enforced\nprovenance", "label = max(\nprovenance,\ndeclaration)", title_dy=0.13)
box(1.70, IY0, 2.60, IY1, "Features", "11, from the\nexecuted prefix", title_dy=0.07)
box(2.85, 2.30, 3.85, IY1, "Classifier", "gradient boosting", title_dy=-0.02, ssize=6.6)
box(2.85, IY0, 3.85, 2.18, "Rules R1–R3", None, tsize=7.8)
box(4.40, 2.26, 6.05, IY1, "Precedence", "max_severity_reviewable", title_dy=-0.01, ssize=6.4,
    mono_sub=True)
box(4.40, IY0, 6.05, 2.06, "Final decision", None, tsize=7.8, fill="#ffffff", edge=ACCENT, lw=1.0)

arrow((1.45, 2.24), (1.70, 2.24))
arrow((2.60, 2.50), (2.85, 2.50))
arrow((2.60, 1.98), (2.85, 1.98))
arrow((3.85, 2.50), (4.40, 2.50), label="model\ndecision", ly=0.03, lsize=5.8, lcolor=MUTED)
line([(3.85, 1.98), (4.15, 1.98), (4.15, 2.16)])
arrow((4.15, 2.16), (4.40, 2.38))
ax.text(3.89, 2.02, "fired\nrules", ha="left", va="bottom", fontsize=5.8, color=MUTED)
arrow((5.60, 2.26), (5.60, 2.06))

# ---------------------------------------------------------------- row C: outcomes
CY0, CY1 = 0.18, 1.18
# MCP servers
ax.add_patch(FancyBboxPatch((0.15, CY0), 3.70, CY1 - CY0, boxstyle="round,pad=0,rounding_size=0.05",
                            fc="#ffffff", ec=BOX_EDGE, lw=0.8))
ax.text(3.75, CY1 - 0.07, "FOUR FASTMCP SERVERS (STDIO)", ha="right", va="top", fontsize=7,
        fontweight="bold", color=MUTED)
srv = ["Document", "Database", "Web", "External"]
sx = 0.30
for name in srv:
    box(sx, 0.30, sx + 0.78, 0.78, name, None, tsize=7.6)
    sx += 0.88
# approval gate and blocked
box(4.30, CY0, 5.38, CY1, "Approval gate", "paused for review;\ndigest rechecked;\nexecution ledger",
    fill=GATE_FILL, edge="#b86a1d", title_dy=0.22)
box(5.55, 0.42, 6.20, 0.94, "Stop", "call refused", fill=STOP_FILL, title_dy=0.05)

# decision exits
dy = IY0
line([(4.55, dy), (4.55, 1.40), (1.95, 1.40)])
arrow((1.95, 1.40), (1.95, CY1))
ax.text(3.25, 1.43, "AUTONOMOUS / RESTRICTED: execute", ha="center", va="bottom", fontsize=6.6, color=INK)
arrow((4.90, dy), (4.90, CY1))
ax.text(4.95, 1.36, "HUMAN_\nAPPROVAL", ha="left", va="center", fontsize=6.2, color="#8a4b12")
arrow((5.85, dy), (5.85, 0.94))
ax.text(5.90, 1.36, "BLOCKED", ha="left", va="center", fontsize=6.2, color=INK)
arrow((4.30, 0.54), (3.72, 0.54), color="#b86a1d", label="approved", ly=0.04, lcolor="#8a4b12")

# provenance feedback from the servers
line([(0.55, 0.78), (0.55, 1.06)], color=ACCENT, ls=(0, (3, 2)))
arrow((0.55, 1.06), (0.55, IY0), color=ACCENT, ls=(0, (3, 2)))
ax.text(0.62, 1.30, "returned items get\nprovenance references", ha="left", va="center", fontsize=6.2,
        color=ACCENT)

# ---------------------------------------------------------------- audit log
box(6.40, CY0, 7.06, BY1, "Hash-\nchained\naudit\nlog", None, tsize=7.8)
ax.text(6.73, 1.05, "every\ndecision\nrecord:\nmodel\ndecision,\nfired rules,\nprecedence\nmode",
        ha="center", va="center", fontsize=6.0, color=MUTED, linespacing=1.1)
arrow((6.05, 1.92), (6.40, 1.92))

for ext in ("png", "svg", "pdf"):
    fig.savefig(f"{OUT}.{ext}", dpi=300)
print("wrote", OUT + ".{png,svg,pdf}")
