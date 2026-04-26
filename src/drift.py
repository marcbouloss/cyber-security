"""
drift.py
--------
Monitors whether incoming traffic starts looking different from what the model was trained on.
Uses KS test and PSI to detect feature drift, and a rolling alert rate for operational monitoring.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats
from typing import Dict, List, Optional
import json
# matplotlib is imported lazily inside plot_drift_report() — it is only needed when
# generating offline plots, and the inference API does not need it.

REPORTS_DIR    = Path(__file__).resolve().parent.parent / "reports"
DRIFT_LOG_PATH = REPORTS_DIR / "drift_log.json"
DRIFT_LOG_MAX  = 1000  # keep at most this many entries on disk to bound file growth
REPORTS_DIR.mkdir(exist_ok=True)


def ks_drift_test(
    reference: np.ndarray,
    production: np.ndarray,
    feature_names: List[str],
    alpha: float = 0.05,
) -> pd.DataFrame:
    # Kolmogorov-Smirnov test compares the distribution of each feature
    # between training data and new incoming data
    # p-value < 0.05 means the feature distribution has significantly shifted
    results = []
    for i, feat in enumerate(feature_names):
        ks_stat, p_value = stats.ks_2samp(reference[:, i], production[:, i])
        results.append({
            "feature":      feat,
            "ks_statistic": round(ks_stat, 4),
            "p_value":      round(p_value, 4),
            "drifted":      p_value < alpha,
        })
    df = pd.DataFrame(results).sort_values("ks_statistic", ascending=False)
    drifted = df[df["drifted"]]["feature"].tolist()
    print(f"\n[Drift/KS] Features with drift (alpha={alpha}): {len(drifted)}/{len(feature_names)}")
    if drifted:
        print(f"  Top drifted: {drifted[:5]}")
    return df


def population_stability_index(reference: np.ndarray, production: np.ndarray, n_bins: int = 10) -> float:
    # PSI measures how much a distribution has shifted
    # PSI < 0.1 = stable, 0.1-0.2 = moderate change, > 0.2 = significant drift
    eps = 1e-6
    breakpoints = np.unique(np.percentile(reference, np.linspace(0, 100, n_bins + 1)))
    # A constant feature collapses to <2 unique breakpoints — np.histogram needs at least 2.
    # In that case we cannot meaningfully compute PSI, so return 0 (no shift detected).
    if len(breakpoints) < 2:
        return 0.0
    ref_hist,  _ = np.histogram(reference,  bins=breakpoints)
    prod_hist, _ = np.histogram(production, bins=breakpoints)
    ref_pct  = (ref_hist  + eps) / (len(reference)  + eps * len(breakpoints))
    prod_pct = (prod_hist + eps) / (len(production) + eps * len(breakpoints))
    return float(np.sum((prod_pct - ref_pct) * np.log(prod_pct / ref_pct)))


def compute_psi_all_features(
    reference: np.ndarray,
    production: np.ndarray,
    feature_names: List[str],
) -> pd.DataFrame:
    results = []
    for i, feat in enumerate(feature_names):
        psi = population_stability_index(reference[:, i], production[:, i])
        status = "stable" if psi < 0.1 else ("moderate" if psi < 0.2 else "DRIFTED")
        results.append({"feature": feat, "PSI": round(psi, 4), "status": status})
    df = pd.DataFrame(results).sort_values("PSI", ascending=False)
    print(f"\n[Drift/PSI] Features with PSI >= 0.2: {(df['status'] == 'DRIFTED').sum()}")
    return df


class AlertRateMonitor:
    """
    Tracks the percentage of traffic being flagged as attacks.
    A sudden spike could mean a real attack or model drift.
    Uses 3-sigma rule to raise warnings.
    """

    # Class index 0 is reserved for "Benign" (alphabetical ordering of class_names).
    # Anything else is treated as an attack for alert-rate purposes.
    BENIGN_IDX = 0

    def __init__(self, window_size: int = 100, history_size: int = 1000):
        self.window_size  = window_size
        self.history_size = history_size
        self.predictions: List[int] = []

    def update(self, preds: np.ndarray) -> Dict:
        self.predictions.extend(int(p) for p in preds.tolist())
        if len(self.predictions) > self.history_size:
            self.predictions = self.predictions[-self.history_size:]

        recent = self.predictions[-self.window_size:]
        alert_rate = sum(p != self.BENIGN_IDX for p in recent) / len(recent)

        # We need at least two non-overlapping windows to estimate a baseline std.
        # Until we do, return WARMING_UP with a meaningful alert_rate but no z-score.
        full_windows = len(self.predictions) // self.window_size
        if full_windows < 2:
            return {
                "alert_rate":    round(alert_rate, 4),
                "baseline_mean": None,
                "z_score":       None,
                "status":        "WARMING_UP",
            }

        baseline_rates = [
            sum(p != self.BENIGN_IDX
                for p in self.predictions[i:i + self.window_size]) / self.window_size
            for i in range(0, full_windows * self.window_size, self.window_size)
        ]
        mu  = float(np.mean(baseline_rates))
        sig = float(np.std(baseline_rates))
        if sig < 1e-6:
            # No variance in baseline → z-score is meaningless. Compare alert_rate
            # directly to mu instead.
            status = "CRITICAL" if alert_rate > mu + 0.5 else (
                     "WARNING"  if alert_rate > mu + 0.2 else "OK")
            z_score = None
        else:
            z_score = (alert_rate - mu) / sig
            status  = "CRITICAL" if z_score > 3 else ("WARNING" if z_score > 2 else "OK")

        return {
            "alert_rate":    round(alert_rate, 4),
            "baseline_mean": round(mu, 4),
            "z_score":       round(z_score, 2) if z_score is not None else None,
            "status":        status,
        }


def class_distribution_drift(
    ref_preds: np.ndarray,
    prod_preds: np.ndarray,
    class_names: List[str],
) -> Dict:
    # Jensen-Shannon divergence compares two probability distributions
    # JSD = 0 means identical, JSD = 1 means completely different
    n = len(class_names)
    eps = 1e-8

    def dist(preds):
        counts = np.bincount(preds.astype(int), minlength=n).astype(float)
        return counts / (counts.sum() + eps)

    p = dist(ref_preds)
    q = dist(prod_preds)
    m = 0.5 * (p + q)

    def kl(a, b):
        mask = (a > eps) & (b > eps)
        return np.sum(a[mask] * np.log(a[mask] / b[mask]))

    jsd = 0.5 * kl(p, m) + 0.5 * kl(q, m)
    status = "OK" if jsd < 0.1 else ("WARNING" if jsd < 0.2 else "CONCEPT DRIFT DETECTED")

    print(f"\n[Drift/Prediction] Jensen-Shannon Divergence: {jsd:.4f} - {status}")
    for i, cls in enumerate(class_names):
        print(f"  {cls:<20} ref={p[i]:.3f}  prod={q[i]:.3f}  delta={q[i]-p[i]:+.3f}")

    return {"jsd": round(jsd, 4), "status": status, "ref_dist": p.tolist(), "prod_dist": q.tolist()}


def plot_drift_report(ks_df: pd.DataFrame, psi_df: pd.DataFrame, top_n: int = 15) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    top_ks = ks_df.head(top_n)
    colours = ["#d62728" if d else "#1f77b4" for d in top_ks["drifted"]]
    axes[0].barh(top_ks["feature"][::-1], top_ks["ks_statistic"][::-1], color=colours[::-1])
    axes[0].axvline(0.1, color="orange", linestyle="--", label="threshold")
    axes[0].set_title("KS Statistic per Feature", fontsize=13)
    axes[0].set_xlabel("KS Statistic")
    axes[0].legend()

    top_psi = psi_df.head(top_n)
    cmap = {"stable": "#1f77b4", "moderate": "#ff7f0e", "DRIFTED": "#d62728"}
    axes[1].barh(top_psi["feature"][::-1], top_psi["PSI"][::-1],
                 color=[cmap[s] for s in top_psi["status"]][::-1])
    axes[1].axvline(0.1, color="orange", linestyle="--", label="Moderate")
    axes[1].axvline(0.2, color="red",    linestyle="--", label="Significant")
    axes[1].set_title("PSI per Feature", fontsize=13)
    axes[1].set_xlabel("PSI")
    axes[1].legend()

    plt.suptitle("Feature Drift Report", fontsize=14, y=1.01)
    plt.tight_layout()
    path = REPORTS_DIR / "drift_report.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[Drift] Report saved -> {path}")


class DriftMonitor:
    """
    Stateful monitor used by the API.
    Accumulates production samples and runs drift checks every N predictions.
    """

    def __init__(self, reference_X, feature_names, class_names, check_interval=500):
        self.reference_X    = reference_X
        self.feature_names  = feature_names
        self.class_names    = class_names
        self.check_interval = check_interval
        self.production_X   = []
        self.production_preds = []
        self.n_calls        = 0
        self.alert_monitor  = AlertRateMonitor()
        # Load persisted log if it exists so history survives restarts
        if DRIFT_LOG_PATH.exists():
            try:
                with open(DRIFT_LOG_PATH) as f:
                    self.drift_log = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.drift_log = []
        else:
            self.drift_log = []

    def update(self, X_batch: np.ndarray, preds: np.ndarray) -> Optional[Dict]:
        self.production_X.append(X_batch)
        self.production_preds.extend(preds.tolist())
        self.n_calls += len(X_batch)

        alert_status = self.alert_monitor.update(preds)

        if self.n_calls >= self.check_interval:
            prod_X = np.vstack(self.production_X)
            ref_sample = self.reference_X[
                np.random.choice(len(self.reference_X), min(len(prod_X), 2000), replace=False)
            ]

            ks_df  = ks_drift_test(ref_sample, prod_X[:2000], self.feature_names)
            psi_df = compute_psi_all_features(ref_sample, prod_X[:2000], self.feature_names)
            psi_score = psi_df["PSI"].mean()
            drift_status = "OK" if psi_score < 0.1 else ("WARNING" if psi_score < 0.2 else "DRIFTED")

            entry = {
                "n_samples":        self.n_calls,
                "psi_mean":         round(psi_score, 4),
                "drifted_features": ks_df[ks_df["drifted"]]["feature"].tolist()[:5],
                "alert_status":     alert_status,
                "drift_status":     drift_status,
            }
            self.drift_log.append(entry)
            # Keep the on-disk log bounded so it cannot grow forever
            if len(self.drift_log) > DRIFT_LOG_MAX:
                self.drift_log = self.drift_log[-DRIFT_LOG_MAX:]
            try:
                with open(DRIFT_LOG_PATH, "w") as f:
                    json.dump(self.drift_log, f, indent=2)
            except OSError as e:
                print(f"[DriftMonitor] WARNING: could not write drift log: {e}")
            print(f"\n[DriftMonitor] {entry}")

            self.production_X     = []
            self.production_preds = []
            self.n_calls          = 0
            return entry
        return {"alert_status": alert_status}
