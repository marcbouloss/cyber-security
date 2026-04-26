"""
preprocessing.py
----------------
Feature scaling, imputation, SMOTE oversampling, and label encoding.
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Tuple

from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
# imblearn is imported lazily inside apply_smote() — it is only needed at training time,
# and importing it at module level would force the inference API (which has to import this
# module to unpickle ClassLabelEncoder) to depend on it for no reason.

ROOT      = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "saved_models"
MODEL_DIR.mkdir(exist_ok=True)


class ClassLabelEncoder:
    def __init__(self):
        self._enc = LabelEncoder()

    def fit(self, y: pd.Series) -> "ClassLabelEncoder":
        self._enc.fit(y)
        return self

    def transform(self, y: pd.Series) -> np.ndarray:
        return self._enc.transform(y)

    def inverse_transform(self, y: np.ndarray) -> np.ndarray:
        return self._enc.inverse_transform(y)

    @property
    def classes_(self):
        return self._enc.classes_

    def save(self, path: Path):
        joblib.dump(self, path)

    @staticmethod
    def load(path: Path) -> "ClassLabelEncoder":
        return joblib.load(path)


def build_feature_pipeline() -> Pipeline:
    # Median imputation handles skewed network features better than mean
    # StandardScaler brings all features to the same scale — important for LR and MLP
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
    ])


def fit_and_transform(
    X_train: pd.DataFrame,
    X_val:   pd.DataFrame,
    X_test:  pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Pipeline]:
    # Fit only on training data to avoid leaking val/test stats into the model
    pipe = build_feature_pipeline()
    X_train_t = pipe.fit_transform(X_train)
    X_val_t   = pipe.transform(X_val)
    X_test_t  = pipe.transform(X_test)

    joblib.dump(pipe, MODEL_DIR / "feature_pipeline.pkl")
    print("[Preprocess] Feature pipeline fitted and saved.")
    print(f"  Input shape:  {X_train.shape}")
    print(f"  Output shape: {X_train_t.shape}")
    return X_train_t, X_val_t, X_test_t, pipe


def apply_smote(
    X: np.ndarray,
    y: np.ndarray,
    sampling_strategy: str = "not majority",
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    # SMOTE generates synthetic samples for minority classes
    # Only applied on training data — never on val or test
    from imblearn.over_sampling import SMOTE
    print(f"\n[SMOTE] Before: {dict(zip(*np.unique(y, return_counts=True)))}")
    smote = SMOTE(sampling_strategy=sampling_strategy, random_state=seed)
    X_res, y_res = smote.fit_resample(X, y)
    print(f"[SMOTE] After:  {dict(zip(*np.unique(y_res, return_counts=True)))}")
    return X_res, y_res


def load_splits(proc_dir: Path):
    from src.data_ingestion import FEATURE_COLS, LABEL_COL

    train = pd.read_parquet(proc_dir / "train.parquet")
    val   = pd.read_parquet(proc_dir / "val.parquet")
    test  = pd.read_parquet(proc_dir / "test.parquet")

    available = [c for c in FEATURE_COLS if c in train.columns]
    X_train, y_train = train[available], train[LABEL_COL]
    X_val,   y_val   = val[available],   val[LABEL_COL]
    X_test,  y_test  = test[available],  test[LABEL_COL]

    return X_train, y_train, X_val, y_val, X_test, y_test, available
