"""
Generates the 2 extra plots needed for the presentation:
  1. Class distribution (before SMOTE) — shows the imbalance problem
  2. Model comparison bar chart — shows the full journey
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ── Plot 1: Class Distribution ────────────────────────────────────────────────
classes = [
    "Benign", "DDoS", "DoS", "Mirai", "Spoofing",
    "Recon", "Recon-\nHostDisc.", "Web", "Dict.\nBruteForce"
]
counts = [60000, 60000, 60000, 60000, 44716, 31014, 22550, 4104, 2150]
colors_bar = [
    "#00D68F", "#FF4757", "#FFA500", "#1A56DB", "#9B59B6",
    "#E67E22", "#3498DB", "#1ABC9C", "#E74C3C"
]

fig, ax = plt.subplots(figsize=(12, 5))
fig.patch.set_facecolor("#0A1628")
ax.set_facecolor("#162236")

bars = ax.bar(classes, counts, color=colors_bar, edgecolor="none", width=0.6)

# Value labels on bars
for bar, count in zip(bars, counts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 500,
            f"{count:,}", ha="center", va="bottom", fontsize=10,
            color="white", fontweight="bold")

ax.set_title("Class Distribution — After Stratified Sampling\n(27.9x imbalance between largest and smallest class)",
             fontsize=14, color="white", pad=15)
ax.set_ylabel("Number of Samples", color="#C5D0DC", fontsize=12)
ax.tick_params(colors="white", labelsize=10)
ax.spines[:].set_visible(False)
ax.yaxis.grid(True, color="#2A3F5A", linewidth=0.7, linestyle="--")
ax.set_axisbelow(True)

# Highlight the imbalance
ax.annotate("27.9x\nmore samples", xy=(0, 60000), xytext=(5.5, 50000),
            fontsize=10, color="#FF4757", fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#FF4757"))

plt.tight_layout()
plt.savefig("reports/class_distribution.png", dpi=150,
            facecolor="#0A1628", bbox_inches="tight")
plt.close()
print("class_distribution.png saved")


# ── Plot 2: Model Comparison Bar Chart ────────────────────────────────────────
models    = ["Logistic\nRegression", "Random\nForest", "XGBoost", "LightGBM\n★ Best", "MLP\nNeural Net"]
macro_f1  = [0.484, 0.808, 0.815, 0.830, 0.630]
roc_auc   = [0.929, 0.994, 0.996, 0.996, 0.976]
benign_fp = [0.342, 0.095, 0.089, 0.088, 0.247]

x = np.arange(len(models))
width = 0.28

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.patch.set_facecolor("#0A1628")

bar_colors = ["#8899AA", "#1A56DB", "#FFA500", "#00D68F", "#9B59B6"]

for ax in axes:
    ax.set_facecolor("#162236")
    ax.spines[:].set_visible(False)
    ax.yaxis.grid(True, color="#2A3F5A", linewidth=0.7, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(colors="white")
    ax.set_xticks(x)
    ax.set_xticklabels(models, color="white", fontsize=9)

# Macro-F1
bars1 = axes[0].bar(x, macro_f1, color=bar_colors, width=0.55, edgecolor="none")
axes[0].set_title("Macro-F1  (higher = better)", color="white", fontsize=12, pad=10)
axes[0].set_ylim(0, 1.05)
axes[0].axhline(0.5, color="#FF4757", linewidth=1, linestyle="--", alpha=0.6)
for bar, val in zip(bars1, macro_f1):
    axes[0].text(bar.get_x() + bar.get_width()/2, val + 0.02,
                 f"{val:.3f}", ha="center", color="white", fontsize=10, fontweight="bold")
axes[0].tick_params(axis="y", colors="#C5D0DC")

# ROC-AUC
bars2 = axes[1].bar(x, roc_auc, color=bar_colors, width=0.55, edgecolor="none")
axes[1].set_title("ROC-AUC  (higher = better)", color="white", fontsize=12, pad=10)
axes[1].set_ylim(0.85, 1.01)
for bar, val in zip(bars2, roc_auc):
    axes[1].text(bar.get_x() + bar.get_width()/2, val + 0.002,
                 f"{val:.3f}", ha="center", color="white", fontsize=10, fontweight="bold")
axes[1].tick_params(axis="y", colors="#C5D0DC")

# Benign FP Rate
bars3 = axes[2].bar(x, [v*100 for v in benign_fp], color=bar_colors, width=0.55, edgecolor="none")
axes[2].set_title("Benign False Positive %  (lower = better)", color="white", fontsize=12, pad=10)
axes[2].set_ylabel("% of benign traffic falsely flagged", color="#C5D0DC", fontsize=9)
for bar, val in zip(bars3, benign_fp):
    axes[2].text(bar.get_x() + bar.get_width()/2, val*100 + 0.5,
                 f"{val*100:.1f}%", ha="center", color="white", fontsize=10, fontweight="bold")
axes[2].tick_params(axis="y", colors="#C5D0DC")

fig.suptitle("Model Comparison — All 5 Models on Test Set (102,167 samples)",
             fontsize=14, color="white", y=1.02)

plt.tight_layout()
plt.savefig("reports/model_comparison_chart.png", dpi=150,
            facecolor="#0A1628", bbox_inches="tight")
plt.close()
print("model_comparison_chart.png saved")


# ── Plot 3: SMOTE Before vs After ─────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.patch.set_facecolor("#0A1628")

classes_short = ["Benign", "DDoS", "Dict.\nBrute", "DoS", "Mirai", "Recon", "Recon-\nHost", "Spoofing", "Web"]
before = [20000, 20000, 1541, 20000, 20000, 20000, 15737, 20000, 2821]
after  = [20000, 20000, 20000, 20000, 20000, 20000, 20000, 20000, 20000]

for ax, data, title, col in zip(
    axes,
    [before, after],
    ["BEFORE SMOTE — Raw Class Counts", "AFTER SMOTE — Balanced Classes"],
    ["#FF4757", "#00D68F"]
):
    ax.set_facecolor("#162236")
    ax.spines[:].set_visible(False)
    ax.yaxis.grid(True, color="#2A3F5A", linewidth=0.7, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(colors="white", labelsize=9)
    bars = ax.bar(classes_short, data, color=col, alpha=0.85, edgecolor="none")
    ax.set_title(title, color="white", fontsize=13, pad=10)
    ax.set_ylim(0, 23000)
    ax.tick_params(axis="y", colors="#C5D0DC")
    for bar, val in zip(bars, data):
        ax.text(bar.get_x() + bar.get_width()/2, val + 200,
                f"{val:,}", ha="center", color="white", fontsize=8, fontweight="bold")

axes[0].annotate("Only 1,541 !", xy=(2, 1541), xytext=(4, 8000),
                 fontsize=10, color="#FF4757", fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color="#FF4757"))
axes[0].annotate("Only 2,821 !", xy=(8, 2821), xytext=(6, 10000),
                 fontsize=10, color="#FF4757", fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color="#FF4757"))

fig.suptitle("SMOTE Oversampling — Fixing Class Imbalance",
             fontsize=14, color="white", y=1.02)
plt.tight_layout()
plt.savefig("reports/smote_comparison.png", dpi=150,
            facecolor="#0A1628", bbox_inches="tight")
plt.close()
print("smote_comparison.png saved")
