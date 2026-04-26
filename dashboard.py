"""
dashboard.py — Streamlit demo UI for the IoT IDS project
Run from cyber-security-main/:
    streamlit run dashboard.py
API must be running separately:
    python -m uvicorn src.api:app --port 8000
"""

import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE    = "http://localhost:8000"
REPORTS_DIR = Path("reports")
DATA_DIR    = Path("data/processed")

CLASS_COLORS = {
    "Benign":               "#22C55E",
    "DDoS":                 "#EF4444",
    "DoS":                  "#F97316",
    "Mirai":                "#A855F7",
    "Spoofing":             "#EAB308",
    "Recon":                "#3B82F6",
    "Recon-HostDiscovery":  "#06B6D4",
    "Web":                  "#EC4899",
    "DictionaryBruteForce": "#6366F1",
}

# Features to show in the compact "key features" panel
KEY_FEATURES = [
    "syn_flag_number", "Rate", "ack_flag_number",
    "flow_duration", "Header_Length", "Protocol Type",
    "Drate", "fin_flag_number", "rst_flag_number", "psh_flag_number",
]

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IoT Intrusion Detection System",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.result-box {
    border-radius: 14px;
    padding: 28px 20px;
    text-align: center;
    margin: 12px 0;
}
.result-attack { background: linear-gradient(135deg, #7f1d1d, #b91c1c); color: white; }
.result-benign { background: linear-gradient(135deg, #14532d, #15803d); color: white; }
.result-label  { font-size: 2.2rem; font-weight: 800; margin: 8px 0; }
.result-conf   { font-size: 1.3rem; opacity: 0.9; }
.result-model  { font-size: 0.8rem; opacity: 0.6; margin-top: 8px; }
</style>
""", unsafe_allow_html=True)


# ── Cached API helpers ────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def get_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


@st.cache_data(ttl=60)
def get_feature_names():
    try:
        r = requests.get(f"{API_BASE}/features", timeout=3)
        return r.json().get("features", [])
    except Exception:
        return KEY_FEATURES


@st.cache_data
def load_test_samples():
    """One representative row per class from the test set.
    DDoS uses a hardcoded example with a clear visual signature for demo purposes."""
    path = DATA_DIR / "test.parquet"
    if not path.exists():
        return {}
    df = pd.read_parquet(path)
    label_col = "label" if "label" in df.columns else df.columns[-1]
    out = {}
    for label in sorted(df[label_col].unique()):
        row = df[df[label_col] == label].sample(1, random_state=42).drop(columns=[label_col])
        out[label] = {k: float(v) for k, v in row.iloc[0].items() if pd.notna(v)}

    # For DDoS, pick the real test row with the highest Rate so the
    # key features look visually dramatic AND all 46 features are present
    ddos_df = df[df[label_col] == "DDoS"].drop(columns=[label_col])
    if "Rate" in ddos_df.columns:
        best = ddos_df.nlargest(1, "Rate")
    else:
        best = ddos_df.sample(1, random_state=0)
    out["DDoS"] = {k: float(v) for k, v in best.iloc[0].items() if pd.notna(v)}
    return out


def call_predict(features: dict, api_key: str = "") -> dict:
    headers = {"X-API-Key": api_key} if api_key else {}
    r = requests.post(f"{API_BASE}/predict", json={"features": features},
                      headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


def call_batch(flows: list, api_key: str = "") -> dict:
    headers = {"X-API-Key": api_key} if api_key else {}
    payload = {"flows": [{"features": f} for f in flows]}
    r = requests.post(f"{API_BASE}/predict/batch", json=payload,
                      headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🛡️ IoT IDS")
    st.caption("Real-time Intrusion Detection")
    st.divider()

    api_key = st.text_input("API Key (optional)", type="password",
                            placeholder="Leave blank if not set")

    st.divider()
    health = get_health()
    if health:
        st.success("● API Online", icon="✅")
        st.metric("Model",    health.get("model", "—"))
        st.metric("Features", health.get("n_features", "—"))
        st.metric("Classes",  health.get("n_classes", "—"))
        st.metric("Confidence threshold", f"{health.get('threshold', 0.70):.0%}")
    else:
        st.error("● API Offline", icon="🔴")
        st.code("python -m uvicorn src.api:app --port 8000", language="bash")

    st.divider()
    if st.button("↺ Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("Dataset: CICIoT2023 (UNB)\n344k flows · 46 features · 9 classes")


# ── Page header ───────────────────────────────────────────────────────────────
st.title("IoT Network Intrusion Detection System")
st.caption(
    "ML-powered classification of network traffic · 9 traffic classes · "
    "LightGBM primary model (Macro-F1: 0.830) · Real-time drift monitoring"
)

tab_predict, tab_batch, tab_reports, tab_monitor = st.tabs([
    "⚡ Live Classify", "📦 Batch Classify", "📊 Model Performance", "📡 Monitoring",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — LIVE CLASSIFY
# ═══════════════════════════════════════════════════════════════════════════════
with tab_predict:
    samples = load_test_samples()
    feature_names = get_feature_names()

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.subheader("Input Features")

        # Preset selector
        preset_opts = ["— custom —"] + sorted(samples.keys())
        preset = st.selectbox(
            "Load a real traffic scenario from the test set",
            preset_opts,
            index=2,  # default to second class (DDoS)
        )
        preset_vals = samples.get(preset, {}) if preset != "— custom —" else {}

        # Key feature inputs — preset name in key forces widget recreation on preset change
        features: dict = {}
        with st.expander("Key Features", expanded=True):
            key_shown = [f for f in KEY_FEATURES if f in feature_names] or KEY_FEATURES
            cols = st.columns(2)
            for i, feat in enumerate(key_shown):
                default = float(preset_vals.get(feat, 0.0))
                with cols[i % 2]:
                    features[feat] = st.number_input(
                        feat, value=default, format="%.4f", key=f"kf_{preset}_{feat}"
                    )

        # Advanced: remaining features
        with st.expander("All 46 Features (advanced)", expanded=False):
            remaining = [f for f in feature_names if f not in KEY_FEATURES]
            cols3 = st.columns(3)
            for i, feat in enumerate(remaining):
                default = float(preset_vals.get(feat, 0.0))
                with cols3[i % 3]:
                    features[feat] = st.number_input(
                        feat, value=default, format="%.4f", key=f"af_{preset}_{feat}"
                    )

        classify_btn = st.button(
            "🔍  Classify Flow", type="primary", use_container_width=True
        )

    with col_right:
        st.subheader("Prediction Result")

        if classify_btn:
            if not health:
                st.error("API is offline — start the server first.")
            else:
                with st.spinner("Classifying…"):
                    try:
                        result = call_predict(features, api_key)

                        label  = result["label"]
                        conf   = result["confidence"]
                        model  = result["model_used"]
                        probs  = result["probabilities"]

                        is_attack = label != "Benign"
                        icon      = "⚠️" if is_attack else "✅"
                        box_cls   = "result-attack" if is_attack else "result-benign"

                        st.markdown(f"""
                        <div class="result-box {box_cls}">
                            <div style="font-size:3rem">{icon}</div>
                            <div class="result-label">{label}</div>
                            <div class="result-conf">{conf:.1%} confidence</div>
                            <div class="result-model">Model: {model}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        if result.get("threshold_applied"):
                            st.warning(
                                f"Confidence below {health.get('threshold', 0.70):.0%} threshold — "
                                f"model originally predicted **{result['original_label']}**, "
                                f"returned **Benign**."
                            )

                        drift = result.get("drift_alert") or {}
                        if drift.get("drift_status") == "DRIFTED":
                            st.error("⚠️ Data drift detected on this window")
                        elif drift.get("drift_status") == "WARNING":
                            st.warning("⚠️ Moderate drift detected")

                        if result.get("unknown_features"):
                            st.warning(f"Unknown feature names: {result['unknown_features']}")

                        # Probability bar chart
                        prob_df = (
                            pd.DataFrame(probs.items(), columns=["Class", "Probability"])
                            .sort_values("Probability", ascending=True)
                        )
                        fig = px.bar(
                            prob_df, x="Probability", y="Class", orientation="h",
                            color="Class", color_discrete_map=CLASS_COLORS,
                            text=prob_df["Probability"].map(lambda p: f"{p:.2%}"),
                        )
                        fig.update_layout(
                            showlegend=False, height=340,
                            margin=dict(l=0, r=8, t=8, b=0),
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            xaxis=dict(range=[0, 1], gridcolor="#334155"),
                            font=dict(color="#e2e8f0"),
                        )
                        fig.update_traces(textposition="outside")
                        st.plotly_chart(fig, use_container_width=True)

                    except requests.HTTPError as e:
                        st.error(f"API error {e.response.status_code}: {e.response.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.info(
                "Select a preset from the dropdown to load a real traffic sample, "
                "then click **Classify Flow**."
            )
            st.markdown("**Traffic classes:**")
            cols = st.columns(3)
            for i, (cls, color) in enumerate(CLASS_COLORS.items()):
                with cols[i % 3]:
                    st.markdown(
                        f'<span style="color:{color}; font-size:1.1rem">●</span> {cls}',
                        unsafe_allow_html=True,
                    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — BATCH CLASSIFY
# ═══════════════════════════════════════════════════════════════════════════════
with tab_batch:
    st.subheader("Batch Classification")
    col1, col2 = st.columns([1, 2], gap="large")

    with col1:
        source = st.radio("Input source", ["Sample from test set", "Upload CSV"])

        if source == "Sample from test set":
            n_flows = st.slider("Number of flows to sample", 20, 500, 100)
            run_btn = st.button("▶  Run Batch", type="primary", use_container_width=True)
        else:
            uploaded = st.file_uploader("Upload CSV (feature columns only)", type=["csv"])
            run_btn = st.button("▶  Classify Uploaded CSV", type="primary",
                                use_container_width=True)

        st.caption(
            "Batch endpoint accepts up to 1000 flows per request. "
            "Every 500 flows triggers a drift check."
        )

    with col2:
        if run_btn:
            if not health:
                st.error("API is offline.")
            else:
                try:
                    if source == "Sample from test set":
                        df = pd.read_parquet(DATA_DIR / "test.parquet")
                        label_col = "label" if "label" in df.columns else df.columns[-1]
                        true_labels = df[label_col]
                        feat_df = df.drop(columns=[label_col])
                        idx = feat_df.sample(n_flows, random_state=int(time.time())).index
                        batch_df   = feat_df.loc[idx]
                        true_vals  = true_labels.loc[idx].values
                    else:
                        if uploaded is None:
                            st.warning("Upload a CSV file first.")
                            st.stop()
                        batch_df  = pd.read_csv(uploaded)
                        true_vals = None

                    flows = [
                        {k: float(v) for k, v in row.items() if pd.notna(v)}
                        for _, row in batch_df.iterrows()
                    ]

                    with st.spinner(f"Classifying {len(flows)} flows…"):
                        result = call_batch(flows, api_key)

                    preds  = result["predictions"]
                    labels = [p["label"] for p in preds]
                    confs  = [p["confidence"] for p in preds]

                    # Summary row
                    n_attack = sum(1 for l in labels if l != "Benign")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Total Flows",      len(labels))
                    m2.metric("Attacks Detected", n_attack,
                              delta=f"{n_attack/len(labels):.0%} of batch")
                    m3.metric("Benign",            len(labels) - n_attack)
                    m4.metric("Avg Confidence",   f"{sum(confs)/len(confs):.1%}")

                    # Accuracy line (if we have ground truth)
                    if true_vals is not None:
                        correct = sum(t == p for t, p in zip(true_vals, labels))
                        st.success(
                            f"Accuracy on this sample: **{correct/len(labels):.1%}** "
                            f"({correct}/{len(labels)} correct)"
                        )

                    # Pie chart
                    from collections import Counter
                    counts = Counter(labels)
                    pie_df = pd.DataFrame(counts.items(), columns=["Class", "Count"])
                    fig = px.pie(
                        pie_df, values="Count", names="Class",
                        color="Class", color_discrete_map=CLASS_COLORS,
                        title="Predicted Class Distribution",
                    )
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e2e8f0"),
                        legend=dict(orientation="h"),
                        margin=dict(t=40, b=0),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Results table
                    rows = {"Predicted": labels, "Confidence": [f"{c:.1%}" for c in confs]}
                    if true_vals is not None:
                        rows = {"True Label": list(true_vals), **rows}
                    results_df = pd.DataFrame(rows)
                    st.dataframe(results_df, use_container_width=True, height=260)

                    csv_bytes = results_df.to_csv(index=False).encode()
                    st.download_button(
                        "⬇  Download Results CSV", csv_bytes,
                        "batch_results.csv", "text/csv",
                    )

                    # Drift alert
                    ds = result.get("drift_status") or {}
                    status = ds.get("drift_status", "")
                    if status == "DRIFTED":
                        st.error(
                            f"⚠️ Data drift detected — mean PSI: {ds.get('psi_mean', '?'):.3f}. "
                            f"Top drifted features: {', '.join(ds.get('drifted_features', []))}"
                        )
                    elif status == "WARNING":
                        st.warning(f"⚠️ Moderate drift — mean PSI: {ds.get('psi_mean', '?'):.3f}")

                except Exception as e:
                    st.error(f"Batch failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — MODEL PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_reports:
    st.subheader("Model Performance Reports")

    comp = REPORTS_DIR / "model_comparison_chart.png"
    if comp.exists():
        st.image(str(comp), caption="Model Comparison — Macro-F1 Scores",
                 use_container_width=True)

    st.divider()

    rt1, rt2, rt3, rt4 = st.tabs([
        "Confusion Matrices", "PR Curves", "Feature Importance & Data", "MLP Training",
    ])

    with rt1:
        models_cm = [
            ("lightgbm",            "LightGBM ⭐ (best)"),
            ("xgboost",             "XGBoost"),
            ("random_forest",       "Random Forest"),
            ("mlp",                 "MLP (PyTorch)"),
            ("logistic_regression", "Logistic Regression"),
        ]
        cols = st.columns(2)
        for i, (slug, title) in enumerate(models_cm):
            p = REPORTS_DIR / f"confusion_matrix_{slug}.png"
            if p.exists():
                with cols[i % 2]:
                    st.image(str(p), caption=title, use_container_width=True)

    with rt2:
        models_pr = [
            ("xgboost",             "XGBoost"),
            ("random_forest",       "Random Forest"),
            ("mlp",                 "MLP"),
            ("logistic_regression", "Logistic Regression"),
        ]
        cols = st.columns(2)
        for i, (slug, title) in enumerate(models_pr):
            p = REPORTS_DIR / f"pr_curve_{slug}.png"
            if p.exists():
                with cols[i % 2]:
                    st.image(str(p), caption=f"PR Curve — {title}",
                             use_container_width=True)

    with rt3:
        col_a, col_b = st.columns(2)
        with col_a:
            p = REPORTS_DIR / "feature_importance_random_forest.png"
            if p.exists():
                st.image(str(p), caption="Feature Importance (Random Forest)",
                         use_container_width=True)
        with col_b:
            p = REPORTS_DIR / "class_distribution.png"
            if p.exists():
                st.image(str(p), caption="Class Distribution in Dataset",
                         use_container_width=True)
        p = REPORTS_DIR / "smote_comparison.png"
        if p.exists():
            st.image(str(p), caption="SMOTE Class Balancing Effect",
                     use_container_width=True)

    with rt4:
        p = REPORTS_DIR / "mlp_training_history.png"
        if p.exists():
            st.image(str(p), caption="MLP Training History (Loss & Accuracy)",
                     use_container_width=True)

    # Model performance table
    st.divider()
    st.markdown("**Model Performance Summary**")
    perf_df = pd.DataFrame([
        {"Model": "LightGBM ⭐",       "Macro-F1": 0.830, "Note": "Primary model used by API"},
        {"Model": "XGBoost",           "Macro-F1": 0.815, "Note": "API fallback"},
        {"Model": "Random Forest",     "Macro-F1": 0.808, "Note": "Training only (>100 MB)"},
        {"Model": "MLP (PyTorch)",     "Macro-F1": 0.630, "Note": "API fallback"},
        {"Model": "Logistic Regression","Macro-F1": 0.484, "Note": "Baseline / API fallback"},
    ])
    st.dataframe(perf_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MONITORING
# ═══════════════════════════════════════════════════════════════════════════════
with tab_monitor:
    st.subheader("Live Monitoring")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("#### API Metrics")
        try:
            r = requests.get(f"{API_BASE}/metrics", timeout=3)
            if r.status_code == 200:
                m = r.json()
                ma, mb = st.columns(2)
                ma.metric("Requests",          m.get("predict_count", 0))
                mb.metric("Flows Classified",  m.get("flows_predicted", 0))
                mc, md = st.columns(2)
                mc.metric("Batch Requests",    m.get("predict_batch_count", 0))
                md.metric("Threshold Fallbacks", m.get("fallbacks_to_benign", 0))

                lat = m.get("latency_ms")
                if lat:
                    st.markdown("**Latency (ms)**")
                    l1, l2, l3 = st.columns(3)
                    l1.metric("p50", f"{lat['p50']:.1f}")
                    l2.metric("p95", f"{lat['p95']:.1f}")
                    l3.metric("Max", f"{lat['max']:.1f}")

                    # Latency gauge bar
                    fig = px.bar(
                        x=["p50", "p95", "max"],
                        y=[lat["p50"], lat["p95"], lat["max"]],
                        labels={"x": "Percentile", "y": "ms"},
                        color=["p50", "p95", "max"],
                        color_discrete_sequence=["#22C55E", "#F59E0B", "#EF4444"],
                        title="Latency Distribution",
                    )
                    fig.update_layout(
                        showlegend=False, height=220,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e2e8f0"),
                        margin=dict(t=40, b=0, l=0, r=0),
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Could not fetch metrics")
        except Exception:
            st.warning("API offline — metrics unavailable")

    with col2:
        st.markdown("#### Drift Monitor")
        try:
            r = requests.get(f"{API_BASE}/drift/status", timeout=3)
            if r.status_code == 200:
                d = r.json()
                total  = d.get("total_checks", 0)
                log    = d.get("drift_log", [])
                latest = d.get("latest")

                st.metric("Total Drift Checks", total)
                st.caption(
                    f"A check runs every 500 predictions. "
                    f"{'No checks yet.' if total == 0 else f'Last {len(log)} entries shown.'}"
                )

                if latest:
                    ds = latest.get("drift_status", "UNKNOWN")
                    icons = {"OK": "🟢", "WARNING": "🟡", "DRIFTED": "🔴", "WARMING_UP": "🔵"}
                    icon  = icons.get(ds, "⚪")
                    st.markdown(f"**Latest status:** {icon} {ds}")
                    st.markdown(f"PSI mean: **{latest.get('psi_mean', '—')}**")

                    drifted = latest.get("drifted_features", [])
                    if drifted:
                        st.markdown("**Top drifted features:**")
                        for feat in drifted:
                            st.markdown(f"- `{feat}`")

                    alert = latest.get("alert_status", {})
                    if alert:
                        st.markdown(
                            f"Alert rate: **{alert.get('alert_rate', 0):.1%}** "
                            f"| Z-score: **{alert.get('z_score', 'N/A')}** "
                            f"| Status: **{alert.get('status', '—')}**"
                        )

                    # History chart if multiple entries
                    if len(log) > 1:
                        hist_df = pd.DataFrame(log)
                        fig = px.line(
                            hist_df, x=hist_df.index, y="psi_mean",
                            title="PSI Mean Over Drift Checks",
                            labels={"index": "Check #", "psi_mean": "Mean PSI"},
                            markers=True,
                        )
                        fig.add_hline(y=0.1, line_dash="dot", line_color="#F59E0B",
                                      annotation_text="WARNING (0.1)")
                        fig.add_hline(y=0.2, line_dash="dot", line_color="#EF4444",
                                      annotation_text="DRIFTED (0.2)")
                        fig.update_layout(
                            height=240,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#e2e8f0"),
                            margin=dict(t=40, b=0),
                        )
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(
                        "No drift checks yet. Send **500+ predictions** "
                        "(use Batch tab) to trigger the first check."
                    )
            else:
                st.warning("Could not fetch drift status")
        except Exception:
            st.warning("API offline — drift status unavailable")

    st.divider()
    if st.button("↺  Refresh Monitoring", use_container_width=True):
        st.rerun()
