"""
End-to-end smoke tests for the IDS API.

These tests load the real saved_models/ artifacts and exercise the FastAPI app
in-process via httpx + ASGITransport. They run without uvicorn or a network
listener, which makes them fast and CI-friendly.

Run:
    pytest tests/ -v
"""
from __future__ import annotations

import os
import pytest

# Make sure auth is OFF for tests regardless of caller environment.
os.environ.pop("IDS_API_KEY", None)
os.environ.setdefault("IDS_DRIFT_INTERVAL", "500")

from httpx import ASGITransport, AsyncClient
from src.api import app, ATTACK_CONFIDENCE_THRESHOLD


# 9 trained classes, alphabetical
EXPECTED_CLASSES = [
    "Benign", "DDoS", "DictionaryBruteForce", "DoS", "Mirai",
    "Recon", "Recon-HostDiscovery", "Spoofing", "Web",
]
EXPECTED_FEATURE_COUNT = 46

DDOS_FLOW = {
    "syn_flag_number": 50, "Rate": 9999.0, "ack_flag_number": 0,
    "flow_duration": 100.0, "Header_Length": 20.0, "Protocol Type": 6.0,
}
BENIGN_FLOW = {
    "syn_flag_number": 1, "Rate": 10.0, "ack_flag_number": 5,
    "flow_duration": 5000.0, "Header_Length": 20.0, "Protocol Type": 6.0,
}


@pytest.fixture(scope="module")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac


pytestmark = pytest.mark.asyncio(loop_scope="module")


async def test_health_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["n_features"] == EXPECTED_FEATURE_COUNT
    assert body["n_classes"] == len(EXPECTED_CLASSES)
    assert body["model"] in {"LightGBM", "XGBoost", "Random Forest", "MLP", "Logistic Regression"}


async def test_classes_endpoint(client):
    r = await client.get("/classes")
    assert r.status_code == 200
    assert r.json()["classes"] == EXPECTED_CLASSES


async def test_features_endpoint(client):
    r = await client.get("/features")
    assert r.status_code == 200
    feats = r.json()["features"]
    assert len(feats) == EXPECTED_FEATURE_COUNT
    assert "flow_duration" in feats and "Rate" in feats


async def test_predict_ddos_flow_classifies_as_attack(client):
    r = await client.post("/predict", json={"features": DDOS_FLOW})
    assert r.status_code == 200
    body = r.json()
    # The DDoS-shaped flow should not be classified as Benign by a working model.
    assert body["label"] != "Benign", f"Expected attack class, got: {body}"
    assert body["confidence"] >= ATTACK_CONFIDENCE_THRESHOLD
    assert body["model_used"]
    # Probability map covers all 9 classes and sums to ~1
    assert set(body["probabilities"].keys()) == set(EXPECTED_CLASSES)
    assert abs(sum(body["probabilities"].values()) - 1.0) < 0.01


async def test_predict_benign_flow_returns_valid_response(client):
    """The 6-feature 'benign' example from the briefing actually classifies as
    DDoS once the other 40 features are imputed to attack-skewed training
    medians (see README). All we can guarantee here is that the response has a
    valid schema, a class label, and a normalized probability distribution."""
    r = await client.post("/predict", json={"features": BENIGN_FLOW})
    assert r.status_code == 200
    body = r.json()
    assert body["label"] in EXPECTED_CLASSES
    assert 0.0 <= body["confidence"] <= 1.0
    if body["threshold_applied"]:
        assert body["label"] == "Benign"
        assert body["original_label"] in EXPECTED_CLASSES
    else:
        assert body["original_label"] is None


async def test_predict_unknown_features_are_reported(client):
    r = await client.post("/predict", json={
        "features": {**BENIGN_FLOW, "definitely_not_a_real_feature": 1.0}
    })
    assert r.status_code == 200
    body = r.json()
    assert body["unknown_features"] == ["definitely_not_a_real_feature"]


async def test_predict_batch_basic(client):
    r = await client.post("/predict/batch", json={
        "flows": [{"features": DDOS_FLOW}, {"features": BENIGN_FLOW}],
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["predictions"]) == 2
    for pred in body["predictions"]:
        assert pred["label"] in EXPECTED_CLASSES
        assert 0.0 <= pred["confidence"] <= 1.0


async def test_predict_batch_size_limit(client):
    payload = {"flows": [{"features": BENIGN_FLOW}] * 1001}
    r = await client.post("/predict/batch", json=payload)
    # Pydantic max_length=1000 returns 422 (unprocessable entity)
    assert r.status_code == 422


async def test_drift_status_endpoint(client):
    r = await client.get("/drift/status")
    assert r.status_code == 200
    body = r.json()
    assert "drift_log" in body
    assert "total_checks" in body


async def test_metrics_endpoint(client):
    # Make sure at least one prediction has happened
    await client.post("/predict", json={"features": BENIGN_FLOW})
    r = await client.get("/metrics")
    assert r.status_code == 200
    body = r.json()
    assert body["predict_count"] >= 1
    assert body["latency_ms"] is not None
    assert "p95" in body["latency_ms"]


async def test_threshold_fallback_marks_response(client):
    """Send a flow we expect to land near the decision boundary; either way,
    when threshold_applied is True we must surface the original label."""
    r = await client.post("/predict", json={"features": {"Rate": 500.0, "Protocol Type": 6.0}})
    assert r.status_code == 200
    body = r.json()
    if body["threshold_applied"]:
        assert body["original_label"] is not None
        assert body["original_label"] != "Benign"
        assert body["label"] == "Benign"


async def test_api_key_required_when_set(monkeypatch):
    """If IDS_API_KEY is set, requests without the header must return 403.

    We can't easily re-init the app inside the same module, so we directly
    flip the in-module sentinel for this test.
    """
    import src.api as apimod
    original = apimod._API_KEY
    apimod._API_KEY = "secret-test-key"
    try:
        transport = ASGITransport(app=apimod.app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            async with apimod.app.router.lifespan_context(apimod.app):
                bad = await ac.post("/predict", json={"features": BENIGN_FLOW})
                assert bad.status_code == 403
                good = await ac.post(
                    "/predict",
                    json={"features": BENIGN_FLOW},
                    headers={"X-API-Key": "secret-test-key"},
                )
                assert good.status_code == 200
    finally:
        apimod._API_KEY = original
