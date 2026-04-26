"""
evaluate.py
-----------
Model evaluation — metrics, plots, and model comparison.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Optional
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
    precision_recall_curve,
    average_precision_score,
)
from sklearn.inspection import permutation_importance
from sklearn.calibration import calibration_curve

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def evaluate_model(model, X, y_true, class_names, model_name="Model") -> dict:
    y_pred = model.predict(X)
    y_prob = model.predict_proba(X) if hasattr(model, "predict_proba") else None

    macro_f1    = f1_score(y_true, y_pred, average="macro")
    micro_f1    = f1_score(y_true, y_pred, average="micro")
    weighted_f1 = f1_score(y_true, y_pred, average="weighted")
    report      = classification_report(y_true, y_pred, target_names=class_names, output_dict=True)

    print(f"\n{'='*60}")
    print(f"  {model_name} — Evaluation Report")
    print(f"{'='*60}")
    print(classification_report(y_true, y_pred, target_names=class_names))
    print(f"  Macro-F1    : {macro_f1:.4f}   <- primary metric")
    print(f"  Micro-F1    : {micro_f1:.4f}")
    print(f"  Weighted-F1 : {weighted_f1:.4f}")

    roc_auc = None
    if y_prob is not None:
        try:
            roc_auc = roc_auc_score(y_true, y_prob, multi_class="ovr", average="macro")
            print(f"  ROC-AUC     : {roc_auc:.4f}")
        except Exception:
            pass

    if "Benign" in class_names:
        benign_idx = list(class_names).index("Benign")
        benign_mask = y_true == benign_idx
        benign_fp_rate = (y_pred[benign_mask] != benign_idx).mean()
        print(f"  Benign FP rate: {benign_fp_rate:.4f}  ({benign_fp_rate*100:.2f}% of benign traffic falsely flagged)")

    return {
        "model": model_name, "macro_f1": macro_f1,
        "micro_f1": micro_f1, "weighted_f1": weighted_f1,
        "roc_auc": roc_auc, "report": report,
    }


def plot_confusion_matrix(model, X, y_true, class_names, model_name="Model") -> None:
    y_pred = model.predict(X)
    cm = confusion_matrix(y_true, y_pred, normalize="true")

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt=".2f", cmap="Blues",
                xticklabels=class_names, yticklabels=class_names, ax=ax)
    ax.set_xlabel("Predicted", fontsize=12)
    ax.set_ylabel("True", fontsize=12)
    ax.set_title(f"{model_name} — Confusion Matrix", fontsize=14)
    plt.tight_layout()
    path = REPORTS_DIR / f"confusion_matrix_{model_name.lower().replace(' ', '_')}.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"[Evaluate] Confusion matrix saved -> {path}")


def plot_precision_recall(model, X, y_true, class_names, model_name="Model") -> None:
    if not hasattr(model, "predict_proba"):
        return
    y_prob = model.predict_proba(X)

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, cls in enumerate(class_names):
        y_bin = (y_true == i).astype(int)
        if y_bin.sum() == 0:
            continue
        prec, rec, _ = precision_recall_curve(y_bin, y_prob[:, i])
        ap = average_precision_score(y_bin, y_prob[:, i])
        ax.plot(rec, prec, label=f"{cls} (AP={ap:.2f})")

    ax.set_xlabel("Recall", fontsize=12)
    ax.set_ylabel("Precision", fontsize=12)
    ax.set_title(f"{model_name} — Precision-Recall Curves", fontsize=14)
    ax.legend(loc="lower left", fontsize=8)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    path = REPORTS_DIR / f"pr_curve_{model_name.lower().replace(' ', '_')}.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"[Evaluate] PR curves saved -> {path}")


def plot_feature_importance(model, X, y, feature_names, model_name="Model", n_repeats=10) -> None:
    print(f"\n[Evaluate] Computing permutation importance for {model_name} ...")
    result = permutation_importance(
        model, X, y, n_repeats=n_repeats, random_state=42, scoring="f1_macro", n_jobs=-1
    )
    idx    = np.argsort(result.importances_mean)[::-1][:20]
    names  = [feature_names[i] for i in idx]
    values = result.importances_mean[idx]
    errors = result.importances_std[idx]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(names[::-1], values[::-1], xerr=errors[::-1], color="steelblue", alpha=0.8)
    ax.set_xlabel("Mean decrease in Macro-F1", fontsize=12)
    ax.set_title(f"{model_name} — Feature Importance (top 20)", fontsize=14)
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    path = REPORTS_DIR / f"feature_importance_{model_name.lower().replace(' ', '_')}.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"[Evaluate] Feature importance saved -> {path}")


def compare_models(results: list) -> pd.DataFrame:
    df = pd.DataFrame([{
        "Model":       r["model"],
        "Macro-F1":    round(r["macro_f1"], 4),
        "Micro-F1":    round(r["micro_f1"], 4),
        "Weighted-F1": round(r["weighted_f1"], 4),
        "ROC-AUC":     round(r["roc_auc"], 4) if r["roc_auc"] else "N/A",
    } for r in results])

    print("\n[Compare] Model Comparison")
    print(df.to_string(index=False))
    df.to_csv(REPORTS_DIR / "model_comparison.csv", index=False)
    return df


def plot_calibration_curve(models: dict, X, y, class_idx=0, class_name="Benign") -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot([0, 1], [0, 1], "k--", label="Perfect calibration")

    for name, model in models.items():
        if not hasattr(model, "predict_proba"):
            continue
        prob  = model.predict_proba(X)[:, class_idx]
        y_bin = (y == class_idx).astype(int)
        frac_pos, mean_pred = calibration_curve(y_bin, prob, n_bins=10)
        ax.plot(mean_pred, frac_pos, marker="o", label=name)

    ax.set_xlabel("Mean predicted probability", fontsize=12)
    ax.set_ylabel("Fraction of positives", fontsize=12)
    ax.set_title(f"Calibration Curve — {class_name}", fontsize=14)
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    path = REPORTS_DIR / f"calibration_{class_name.lower()}.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"[Evaluate] Calibration curve saved -> {path}")
