# Streaming IoT Intrusion Detection with Drift Monitoring

Multi-class ML system that classifies IoT network traffic as **Benign** or one of **8 attack types** in real-time, with live drift monitoring.

---

## If you just want to test it — 3 steps

> No dataset download needed. No training needed. Models are pre-trained and included.

**Requirements: Python 3.8 or newer**

**Step 1 — Get the project folder**

Copy the `cyber-security-main` folder to your machine, then open a terminal inside it:
```bash
cd cyber-security-main
```

**Step 2 — Install dependencies**
```bash
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

> The second line installs PyTorch (CPU-only, ~200 MB instead of 2 GB). If you already have PyTorch installed, skip it.

**Step 3 — Start the server**
```bash
python -m uvicorn src.api:app --port 8000
```

Open your browser at **http://localhost:8000/docs**

That's it. You will see an interactive page where you can send traffic and get predictions.

---

## Test it in the browser

Once the API is running, go to **http://localhost:8000/docs**

Click **POST /predict** → **Try it out** → paste this → **Execute**:

```json
{
  "features": {
    "syn_flag_number": 50,
    "Rate": 9999.0,
    "ack_flag_number": 0,
    "flow_duration": 100.0,
    "Header_Length": 20.0,
    "Protocol Type": 6.0
  }
}
```

You should get back:
```json
{
  "label": "DDoS",
  "confidence": 0.9997,
  "model_used": "LightGBM",
  "probabilities": { "Benign": 0.0, "DDoS": 0.9997, ... }
}
```

> **Why does the small "benign" example often classify as DDoS?**
> The model was fitted on 46 features. When you only supply 6, the other 40 are
> imputed with training-set medians — and the training set is heavily attack-
> weighted, so an under-specified flow looks attack-like. To see a Benign label,
> either supply more features or capture a real benign flow with the CICIoT2023
> tooling.

The 70% confidence floor (`IDS_THRESHOLD`) protects you in the other direction:
if the model is only mildly confident in an attack class, the API falls back to
`Benign` and surfaces what the model originally wanted in `original_label`.

---

## Run with Docker (even easier)

**Option A — pull the pre-built image from Docker Hub (recommended):**
```bash
docker run -p 8000:8000 marcboulos/iot-ids:latest
```

Open **http://localhost:8000/docs**

**Option B — build locally from source:**
```bash
docker-compose up --build
```

Open **http://localhost:8000/docs**

---

## Project Structure

```
cybersecurity/
├── src/
│   ├── api.py                  ← FastAPI server (start here)
│   ├── train.py                ← training pipeline
│   ├── evaluate.py             ← metrics and plots
│   ├── drift.py                ← drift monitoring
│   ├── data_ingestion.py       ← data loading and splitting
│   ├── preprocessing.py        ← scaling, SMOTE, encoding
│   └── models/
│       ├── baseline.py         ← Logistic Regression
│       ├── ensemble.py         ← Random Forest, XGBoost, LightGBM
│       └── mlp.py              ← PyTorch Neural Network
│
├── saved_models/               ← pre-trained models (ready to use)
├── reports/                    ← confusion matrices, PR curves, plots
├── notebooks/                  ← EDA and modeling notebooks
├── docs/
│   └── presentation.pptx       ← project slides
├── data/processed/             ← processed dataset splits
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/predict` | Classify a single traffic flow |
| POST | `/predict/batch` | Classify up to 1000 flows in one call |
| GET | `/drift/status` | Last 10 drift checks + total |
| GET | `/health` | Returns 200 only after artifacts load (503 otherwise) |
| GET | `/metrics` | Request counts, fallback count, latency p50/p95 |
| GET | `/classes` | List of class labels |
| GET | `/features` | Ordered list of expected feature names |
| GET | `/docs` | Interactive Swagger UI |

---

## Configuration

The API reads four optional environment variables on startup:

| Variable | Default | Purpose |
|----------|---------|---------|
| `IDS_API_KEY`        | *(unset)* | If set, every prediction/drift endpoint requires the matching `X-API-Key` header. Leave unset for local demo. |
| `IDS_THRESHOLD`      | `0.70`    | Minimum confidence to emit an attack label. Below this we fall back to `Benign` and report the model's original guess in `original_label`. Lower values catch more attacks but inflate false positives. |
| `IDS_CORS_ORIGINS`   | `*`       | Comma-separated list of allowed origins for CORS. Use a real allowlist in production. |
| `IDS_DRIFT_INTERVAL` | `500`     | Predictions between full drift checks (KS / PSI / Jensen-Shannon). Lower = more responsive, higher = cheaper. |

Example with auth and tighter CORS:
```bash
IDS_API_KEY=$(openssl rand -hex 16) IDS_CORS_ORIGINS="https://my.app" python -m uvicorn src.api:app --port 8000
```

---

## Models & Results

| Model | Macro-F1 | ROC-AUC | Benign FP% |
|-------|----------|---------|------------|
| Logistic Regression | 0.484 | 0.929 | 34.2% |
| Random Forest† | 0.808 | 0.994 | 9.5% |
| XGBoost | 0.815 | 0.996 | 8.9% |
| **LightGBM** ★ | **0.830** | **0.996** | **8.8%** |
| MLP (Neural Net) | 0.630 | 0.976 | 24.7% |

† `random_forest.pkl` is not included. To use Random Forest, retrain with `python -m src.train --models rf`.

**LightGBM is used for all predictions** (best Macro-F1).

We use **Macro-F1** as the primary metric because accuracy is misleading when classes are imbalanced — a model predicting "Benign" for everything scores 17% accuracy but misses every attack.

---

## Classes Detected

| Class | Description |
|-------|-------------|
| Benign | Normal traffic |
| DDoS | Distributed Denial of Service |
| DoS | Denial of Service |
| Mirai | Mirai botnet traffic |
| Spoofing | DNS/ARP spoofing |
| Recon | Port scans, OS fingerprinting |
| Recon-HostDiscovery | Host discovery scans |
| Web | SQL injection, XSS, command injection |
| DictionaryBruteForce | Password brute force |

---

## Tests

A pytest smoke suite exercises every endpoint in-process (no network listener
required) against the real saved artifacts.

```bash
pip install pytest pytest-asyncio httpx
pytest -v
```

The suite covers `/health`, `/classes`, `/features`, `/predict` (DDoS + Benign +
unknown feature warning), `/predict/batch` (correct + over-limit), `/drift/status`,
`/metrics`, the confidence threshold fallback, and API-key auth.

---

## If you want to retrain (optional)

Only needed if you have the CICIoT2023 dataset.

1. Download from: https://www.unb.ca/cic/datasets/iotdataset-2023.html
2. Place CSV files in `data/raw/`
3. Run ingestion: `python -m src.data_ingestion`
4. Run training: `python -m src.train`

---

## Dataset

**CICIoT2023** — University of New Brunswick  
https://www.unb.ca/cic/datasets/iotdataset-2023.html
