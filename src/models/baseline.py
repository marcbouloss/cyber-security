"""
baseline.py
-----------
Logistic Regression baseline — our starting point before trying stronger models.
"""

import numpy as np
import joblib
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "saved_models"


def build_logistic_regression(C: float = 1.0, seed: int = 42) -> LogisticRegression:
    # C controls regularization strength — smaller C = more regularization.
    # class_weight balanced helps with imbalanced classes.
    # multi_class is no longer specified — sklearn picks "multinomial" automatically
    # for >2 classes and the explicit kwarg is deprecated since sklearn 1.5.
    return LogisticRegression(
        C=C,
        penalty="l2",
        solver="saga",
        class_weight="balanced",
        max_iter=1000,
        random_state=seed,
        n_jobs=-1,
    )


def train_logistic_regression(
    X_train: np.ndarray,
    y_train: np.ndarray,
    C: float = 1.0,
    seed: int = 42,
) -> LogisticRegression:
    print("\n[Baseline] Training Logistic Regression ...")
    lr = build_logistic_regression(C=C, seed=seed)
    lr.fit(X_train, y_train)

    # Calibrate probabilities so confidence scores are more reliable.
    # cv="prefit" was deprecated in sklearn 1.6 and removed in 1.8 — wrap the fitted
    # estimator in FrozenEstimator (1.6+) when available, otherwise fall back to a
    # 5-fold internal calibration which works on any sklearn version.
    try:
        from sklearn.frozen import FrozenEstimator
        calibrated = CalibratedClassifierCV(FrozenEstimator(lr), method="isotonic")
    except ImportError:
        calibrated = CalibratedClassifierCV(lr, method="isotonic", cv=5)
    calibrated.fit(X_train, y_train)

    joblib.dump(calibrated, MODEL_DIR / "logistic_regression.pkl")
    print("[Baseline] Logistic Regression saved.")
    return calibrated


def get_feature_importance(model: LogisticRegression, feature_names: list) -> dict:
    base = model.estimator if hasattr(model, "estimator") else model
    coefs = np.abs(base.coef_).mean(axis=0)
    return dict(sorted(zip(feature_names, coefs), key=lambda x: -x[1]))
