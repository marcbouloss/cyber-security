"""
ensemble.py
-----------
Random Forest, XGBoost, and LightGBM classifiers.
"""

import numpy as np
import joblib
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
import lightgbm as lgb

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "saved_models"


def build_random_forest(seed: int = 42) -> RandomForestClassifier:
    # 200 trees voting together — more stable than a single decision tree
    # oob_score gives a free validation estimate using out-of-bag samples
    return RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=10,
        min_samples_leaf=4,
        max_features="sqrt",
        class_weight="balanced_subsample",
        bootstrap=True,
        oob_score=True,
        random_state=seed,
        n_jobs=-1,
    )


def train_random_forest(X_train: np.ndarray, y_train: np.ndarray, seed: int = 42) -> RandomForestClassifier:
    print("\n[Ensemble] Training Random Forest ...")
    rf = build_random_forest(seed)
    rf.fit(X_train, y_train)
    print(f"[Ensemble] RF OOB score (free cross-val estimate): {rf.oob_score_:.4f}")
    joblib.dump(rf, MODEL_DIR / "random_forest.pkl")
    print("[Ensemble] Random Forest saved.")
    return rf


def build_xgboost(n_classes: int, seed: int = 42) -> xgb.XGBClassifier:
    # Gradient boosting — each tree corrects the errors of the previous ones
    return xgb.XGBClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective="multi:softprob",
        num_class=n_classes,
        eval_metric="mlogloss",
        random_state=seed,
        n_jobs=-1,
        verbosity=0,
    )


def train_xgboost(
    X_train: np.ndarray, y_train: np.ndarray,
    X_val: np.ndarray, y_val: np.ndarray,
    seed: int = 42,
) -> xgb.XGBClassifier:
    n_classes = len(np.unique(y_train))
    print(f"\n[Ensemble] Training XGBoost ({n_classes} classes) ...")
    xgb_model = build_xgboost(n_classes, seed)
    xgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    joblib.dump(xgb_model, MODEL_DIR / "xgboost.pkl")
    print("[Ensemble] XGBoost saved.")
    return xgb_model


def build_lightgbm(seed: int = 42) -> lgb.LGBMClassifier:
    # LightGBM is faster than XGBoost and handles large datasets well
    return lgb.LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=63,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
        verbose=-1,
    )


def train_lightgbm(
    X_train: np.ndarray, y_train: np.ndarray,
    X_val: np.ndarray, y_val: np.ndarray,
    seed: int = 42,
) -> lgb.LGBMClassifier:
    print("\n[Ensemble] Training LightGBM ...")
    lgbm = build_lightgbm(seed)
    lgbm.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(-1)],
    )
    print(f"[Ensemble] LightGBM best iteration: {lgbm.best_iteration_}")
    joblib.dump(lgbm, MODEL_DIR / "lightgbm.pkl")
    print("[Ensemble] LightGBM saved.")
    return lgbm


def get_feature_importance(model, feature_names: list, kind: str = "gain") -> dict:
    if hasattr(model, "feature_importances_"):
        imp = model.feature_importances_
    else:
        imp = model.booster_.feature_importance(importance_type=kind)
    return dict(sorted(zip(feature_names, imp), key=lambda x: -x[1]))
