"""
api.py
------
FastAPI inference + drift monitoring service.

Endpoints:
  POST /predict       — classify a single traffic flow
  POST /predict/batch — classify multiple flows
  GET  /drift/status  — current drift monitoring status
  GET  /health        — health check (returns 503 until artifacts are loaded)
  GET  /metrics       — request count and latency stats
  GET  /classes       — list of known classes
  GET  /features      — list of expected input features

Environment variables:
  IDS_API_KEY            If set, every prediction/drift endpoint requires header X-API-Key.
  IDS_CORS_ORIGINS       Comma-separated origins (default "*").
  IDS_THRESHOLD          Min confidence to emit an attack label (default 0.70).
  IDS_DRIFT_INTERVAL     Predictions between full drift checks (default 500).

Run locally:
    uvicorn src.api:app --reload --port 8000
"""

from __future__ import annotations

import os
import time
import logging
import threading
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field

from src.drift import DriftMonitor
from src.models.mlp import MLPWrapper

logger = logging.getLogger("ids.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

ROOT      = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "saved_models"

# ── Configuration via environment ────────────────────────────────────────────
_API_KEY        = os.getenv("IDS_API_KEY", "")
_CORS_ORIGINS   = [o.strip() for o in os.getenv("IDS_CORS_ORIGINS", "*").split(",") if o.strip()]
ATTACK_CONFIDENCE_THRESHOLD = float(os.getenv("IDS_THRESHOLD", "0.70"))
DRIFT_CHECK_INTERVAL        = int(os.getenv("IDS_DRIFT_INTERVAL", "500"))


# ── API key authentication (optional) ────────────────────────────────────────
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _verify_api_key(key: Optional[str] = Security(_api_key_header)) -> None:
    if _API_KEY and key != _API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key.")


# ── Startup — load all artifacts ─────────────────────────────────────────────
def load_best_model():
    """Load the best available model (prefer LightGBM > XGBoost > MLP > LR).

    Random Forest is not in the chain because random_forest.pkl is intentionally
    excluded from the repo (>100 MB). Retrain with `python -m src.train --models rf`
    if you need it locally.
    """
    preference = [
        ("lightgbm.pkl",            "LightGBM"),
        ("xgboost.pkl",             "XGBoost"),
        ("random_forest.pkl",       "Random Forest"),
        ("mlp_weights.pt",          "MLP"),
        ("logistic_regression.pkl", "Logistic Regression"),
    ]
    for fname, name in preference:
        path = MODEL_DIR / fname
        if path.exists():
            if fname == "mlp_weights.pt":
                model = MLPWrapper.load(MODEL_DIR)
            else:
                model = joblib.load(path)
            logger.info("Loaded model: %s", name)
            return model, name
    raise RuntimeError("No trained model found. Run src/train.py first.")


# ── Global state and metrics ─────────────────────────────────────────────────
STATE: Dict[str, Any] = {"ready": False, "load_error": None}

_metrics_lock = threading.Lock()
_metrics: Dict[str, Any] = {
    "predict_count":       0,
    "predict_batch_count": 0,
    "flows_predicted":     0,
    "fallbacks_to_benign": 0,
    "latency_ms":          deque(maxlen=1000),  # rolling window of single-prediction latencies
}


def _record_latency(ms: float) -> None:
    with _metrics_lock:
        _metrics["latency_ms"].append(ms)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading artifacts from %s ...", MODEL_DIR)
    try:
        STATE["model"], STATE["model_name"] = load_best_model()
        STATE["pipeline"]      = joblib.load(MODEL_DIR / "feature_pipeline.pkl")
        STATE["label_encoder"] = joblib.load(MODEL_DIR / "label_encoder.pkl")
        STATE["feature_names"] = joblib.load(MODEL_DIR / "feature_names.pkl")
        STATE["class_names"]   = list(joblib.load(MODEL_DIR / "class_names.pkl"))
        STATE["benign_idx"]    = STATE["class_names"].index("Benign") if "Benign" in STATE["class_names"] else 0
        STATE["feature_set"]   = set(STATE["feature_names"])
        reference_X            = np.load(MODEL_DIR / "reference_X.npy")
        STATE["drift_monitor"] = DriftMonitor(
            reference_X    = reference_X,
            feature_names  = STATE["feature_names"],
            class_names    = STATE["class_names"],
            check_interval = DRIFT_CHECK_INTERVAL,
        )
        STATE["ready"] = True
        logger.info(
            "Ready — model=%s features=%d classes=%s",
            STATE["model_name"], len(STATE["feature_names"]), STATE["class_names"],
        )
    except Exception as e:
        STATE["load_error"] = repr(e)
        logger.exception("Failed to load artifacts: %s", e)
    yield


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="IoT IDS — Intrusion Detection API",
    description=(
        "Streaming IoT Intrusion Detection System.\n\n"
        "Classifies network traffic flows as Benign or one of 8 attack families "
        "(DDoS, DoS, Mirai, Recon, Recon-HostDiscovery, Spoofing, Web, "
        "DictionaryBruteForce) using a trained ML model.\n\n"
        "Includes real-time drift monitoring using KS-test, PSI, and "
        "Jensen-Shannon divergence."
    ),
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic schemas ─────────────────────────────────────────────────────────
class TrafficFlow(BaseModel):
    """A single network flow feature vector.

    Field names must match CICIoT2023 feature columns. Missing fields are
    imputed with the training-set median by the pipeline. Unknown field names
    are silently ignored at inference time, but `/predict` will warn about
    them in the response (`unknown_features`).
    """
    features: Dict[str, float] = Field(
        ...,
        json_schema_extra={"example": {
            "flow_duration":   1234.5,
            "Header_Length":   20.0,
            "Protocol Type":   6.0,
            "Rate":            100.0,
            "syn_flag_number": 1.0,
            "ack_flag_number": 1.0,
        }},
    )


class BatchRequest(BaseModel):
    flows: List[TrafficFlow] = Field(..., max_length=1000)


class PredictionResponse(BaseModel):
    label:           str
    confidence:      float
    probabilities:   Dict[str, float]
    model_used:      str
    # When the threshold falls back to Benign, the model's original top class is
    # exposed here so callers can still see what the model wanted to predict.
    original_label:  Optional[str]   = None
    threshold_applied: bool          = False
    drift_alert:     Optional[Dict]  = None
    unknown_features: Optional[List[str]] = None


class BatchResponse(BaseModel):
    predictions:  List[PredictionResponse]
    drift_status: Optional[Dict] = None


# ── Helpers ──────────────────────────────────────────────────────────────────
def _require_ready() -> None:
    if not STATE.get("ready"):
        detail = STATE.get("load_error") or "Artifacts still loading."
        raise HTTPException(status_code=503, detail=f"API not ready: {detail}")


def _flow_to_frame(flow_dict: Dict[str, float]) -> pd.DataFrame:
    """Build a 1-row DataFrame using the trained feature names so the pipeline
    and downstream model see the same columns they were fitted with (avoids
    the 'X does not have valid feature names' warning)."""
    feature_names = STATE["feature_names"]
    return pd.DataFrame([[flow_dict.get(f, np.nan) for f in feature_names]],
                        columns=feature_names, dtype=np.float64)


def _flows_to_frame(flows) -> pd.DataFrame:
    feature_names = STATE["feature_names"]
    rows = [[flow.features.get(f, np.nan) for f in feature_names] for flow in flows]
    return pd.DataFrame(rows, columns=feature_names, dtype=np.float64)


def _unknown_features(flow_dict: Dict[str, float]) -> List[str]:
    feature_set = STATE["feature_set"]
    return sorted(k for k in flow_dict if k not in feature_set)


def _apply_threshold(idx: int, conf: float) -> tuple[int, bool]:
    """Returns (final_idx, threshold_applied)."""
    benign_idx = STATE["benign_idx"]
    if idx != benign_idx and conf < ATTACK_CONFIDENCE_THRESHOLD:
        with _metrics_lock:
            _metrics["fallbacks_to_benign"] += 1
        return benign_idx, True
    return idx, False


def _build_prob_map(probs_row: np.ndarray) -> Dict[str, float]:
    return {cls: round(float(p), 4) for cls, p in zip(STATE["class_names"], probs_row)}


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    if not STATE.get("ready"):
        raise HTTPException(
            status_code=503,
            detail=STATE.get("load_error") or "API still loading.",
        )
    return {
        "status":     "ok",
        "model":      STATE["model_name"],
        "n_features": len(STATE["feature_names"]),
        "n_classes":  len(STATE["class_names"]),
        "threshold":  ATTACK_CONFIDENCE_THRESHOLD,
    }


@app.get("/classes")
def get_classes():
    _require_ready()
    return {"classes": STATE["class_names"]}


@app.get("/features")
def get_features():
    _require_ready()
    return {"features": STATE["feature_names"]}


@app.get("/metrics")
def get_metrics():
    """Lightweight metrics — rolling average and p95 latency, request counters."""
    _require_ready()
    with _metrics_lock:
        latencies = list(_metrics["latency_ms"])
        snapshot  = {
            "predict_count":       _metrics["predict_count"],
            "predict_batch_count": _metrics["predict_batch_count"],
            "flows_predicted":     _metrics["flows_predicted"],
            "fallbacks_to_benign": _metrics["fallbacks_to_benign"],
        }
    if latencies:
        arr = np.array(latencies)
        snapshot["latency_ms"] = {
            "count": len(arr),
            "mean":  round(float(arr.mean()), 3),
            "p50":   round(float(np.percentile(arr, 50)), 3),
            "p95":   round(float(np.percentile(arr, 95)), 3),
            "max":   round(float(arr.max()), 3),
        }
    else:
        snapshot["latency_ms"] = None
    return snapshot


@app.post("/predict", response_model=PredictionResponse, dependencies=[Depends(_verify_api_key)])
def predict(flow: TrafficFlow):
    """Classify a single network traffic flow.

    Missing features are imputed with the training-set median. Unknown feature
    names (typos) are returned in `unknown_features` so callers can fix them.
    """
    _require_ready()
    t0 = time.perf_counter()

    unknown = _unknown_features(flow.features)
    X_raw   = _flow_to_frame(flow.features)
    X_t     = STATE["pipeline"].transform(X_raw)
    probs   = STATE["model"].predict_proba(X_t)[0]
    raw_idx = int(probs.argmax())
    raw_conf = float(probs[raw_idx])

    final_idx, threshold_applied = _apply_threshold(raw_idx, raw_conf)
    drift_info = STATE["drift_monitor"].update(X_t, np.array([final_idx]))

    with _metrics_lock:
        _metrics["predict_count"]   += 1
        _metrics["flows_predicted"] += 1
    _record_latency((time.perf_counter() - t0) * 1000.0)

    return PredictionResponse(
        label             = STATE["class_names"][final_idx],
        confidence        = round(float(probs[final_idx]), 4),
        probabilities     = _build_prob_map(probs),
        model_used        = STATE["model_name"],
        original_label    = STATE["class_names"][raw_idx] if threshold_applied else None,
        threshold_applied = threshold_applied,
        drift_alert       = drift_info,
        unknown_features  = unknown or None,
    )


@app.post("/predict/batch", response_model=BatchResponse, dependencies=[Depends(_verify_api_key)])
def predict_batch(request: BatchRequest):
    """Classify multiple flows in a single request and run drift monitoring on the batch."""
    _require_ready()
    t0 = time.perf_counter()

    X_raw = _flows_to_frame(request.flows)
    X_t   = STATE["pipeline"].transform(X_raw)
    probs = STATE["model"].predict_proba(X_t)
    raw_idxs = probs.argmax(axis=1)

    predictions: List[PredictionResponse] = []
    final_idxs = np.empty_like(raw_idxs)
    for i, flow in enumerate(request.flows):
        raw_idx  = int(raw_idxs[i])
        raw_conf = float(probs[i, raw_idx])
        final_idx, threshold_applied = _apply_threshold(raw_idx, raw_conf)
        final_idxs[i] = final_idx

        predictions.append(PredictionResponse(
            label             = STATE["class_names"][final_idx],
            confidence        = round(float(probs[i, final_idx]), 4),
            probabilities     = _build_prob_map(probs[i]),
            model_used        = STATE["model_name"],
            original_label    = STATE["class_names"][raw_idx] if threshold_applied else None,
            threshold_applied = threshold_applied,
            unknown_features  = _unknown_features(flow.features) or None,
        ))

    drift_status = STATE["drift_monitor"].update(X_t, final_idxs)

    with _metrics_lock:
        _metrics["predict_batch_count"] += 1
        _metrics["flows_predicted"]     += len(request.flows)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    if request.flows:
        per_flow = elapsed_ms / len(request.flows)
        _record_latency(per_flow)

    return BatchResponse(predictions=predictions, drift_status=drift_status)


@app.get("/drift/status", dependencies=[Depends(_verify_api_key)])
def drift_status():
    """Return the latest drift monitoring report."""
    _require_ready()
    log = STATE["drift_monitor"].drift_log
    return {
        "drift_log":    log[-10:] if log else [],
        "total_checks": len(log),
        "latest":       log[-1] if log else None,
    }
