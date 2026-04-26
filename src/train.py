"""
train.py
--------
Training orchestrator — runs the full ML pipeline end to end.

Run:
    python -m src.train [--no-smote] [--models all|lr|rf|xgb|lgbm|mlp]
"""

import argparse
import json
import joblib
import numpy as np
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
PROC_DIR  = ROOT / "data" / "processed"
MODEL_DIR = ROOT / "saved_models"

from src.preprocessing import (
    ClassLabelEncoder,
    fit_and_transform,
    apply_smote,
    load_splits,
)
from src.models.baseline  import train_logistic_regression
from src.models.ensemble  import train_random_forest, train_xgboost, train_lightgbm
from src.models.mlp       import train_mlp, MLPWrapper, IDS_MLP
from src.evaluate import (
    evaluate_model,
    plot_confusion_matrix,
    plot_precision_recall,
    plot_feature_importance,
    compare_models,
    plot_calibration_curve,
)


def main(use_smote: bool = True, models: str = "all"):
    print("\n" + "=" * 60)
    print("  Streaming IoT IDS — Training Pipeline")
    print("=" * 60)

    # ── 1. Load splits ────────────────────────────────────────────────────────
    X_train, y_train_raw, X_val, y_val_raw, X_test, y_test_raw, feature_names = \
        load_splits(PROC_DIR)

    # ── 2. Encode labels ──────────────────────────────────────────────────────
    le = ClassLabelEncoder()
    le.fit(y_train_raw)
    y_train = le.transform(y_train_raw)
    y_val   = le.transform(y_val_raw)
    y_test  = le.transform(y_test_raw)
    class_names = list(le.classes_)
    n_classes   = len(class_names)

    print(f"\n[Train] Classes ({n_classes}): {class_names}")
    le.save(MODEL_DIR / "label_encoder.pkl")

    # ── 3. Feature preprocessing ──────────────────────────────────────────────
    X_train_t, X_val_t, X_test_t, pipe = fit_and_transform(X_train, X_val, X_test)

    # ── 4. SMOTE (on training set only) ───────────────────────────────────────
    if use_smote:
        X_train_t, y_train = apply_smote(X_train_t, y_train)

    # Save reference distribution for drift monitoring
    ref_sample = X_train_t[np.random.choice(len(X_train_t), min(5000, len(X_train_t)), replace=False)]
    np.save(MODEL_DIR / "reference_X.npy", ref_sample)
    joblib.dump(feature_names, MODEL_DIR / "feature_names.pkl")
    joblib.dump(class_names,   MODEL_DIR / "class_names.pkl")

    trained_models = {}
    results = []

    run_all = (models == "all")

    # ── 5. Logistic Regression baseline ──────────────────────────────────────
    if run_all or "lr" in models:
        lr_model = train_logistic_regression(X_train_t, y_train)
        trained_models["Logistic Regression"] = lr_model
        res = evaluate_model(lr_model, X_test_t, y_test, class_names, "Logistic Regression")
        results.append(res)
        plot_confusion_matrix(lr_model, X_test_t, y_test, class_names, "Logistic Regression")
        plot_precision_recall(lr_model, X_test_t, y_test, class_names, "Logistic Regression")

    # ── 6. Random Forest ──────────────────────────────────────────────────────
    if run_all or "rf" in models:
        rf_model = train_random_forest(X_train_t, y_train)
        trained_models["Random Forest"] = rf_model
        res = evaluate_model(rf_model, X_test_t, y_test, class_names, "Random Forest")
        results.append(res)
        plot_confusion_matrix(rf_model, X_test_t, y_test, class_names, "Random Forest")
        plot_precision_recall(rf_model, X_test_t, y_test, class_names, "Random Forest")
        plot_feature_importance(rf_model, X_test_t, y_test, feature_names, "Random Forest", n_repeats=5)

    # ── 7. XGBoost ────────────────────────────────────────────────────────────
    if run_all or "xgb" in models:
        xgb_model = train_xgboost(X_train_t, y_train, X_val_t, y_val)
        trained_models["XGBoost"] = xgb_model
        res = evaluate_model(xgb_model, X_test_t, y_test, class_names, "XGBoost")
        results.append(res)
        plot_confusion_matrix(xgb_model, X_test_t, y_test, class_names, "XGBoost")
        plot_precision_recall(xgb_model, X_test_t, y_test, class_names, "XGBoost")

    # ── 8. LightGBM ───────────────────────────────────────────────────────────
    if run_all or "lgbm" in models:
        lgbm_model = train_lightgbm(X_train_t, y_train, X_val_t, y_val)
        trained_models["LightGBM"] = lgbm_model
        res = evaluate_model(lgbm_model, X_test_t, y_test, class_names, "LightGBM")
        results.append(res)
        plot_confusion_matrix(lgbm_model, X_test_t, y_test, class_names, "LightGBM")

    # ── 9. MLP ────────────────────────────────────────────────────────────────
    if run_all or "mlp" in models:
        mlp_raw, history = train_mlp(
            X_train_t, y_train, X_val_t, y_val,
            n_classes=n_classes, epochs=50, batch_size=512,
        )
        mlp_model = MLPWrapper(mlp_raw)
        trained_models["MLP"] = mlp_model
        res = evaluate_model(mlp_model, X_test_t, y_test, class_names, "MLP")
        results.append(res)
        plot_confusion_matrix(mlp_model, X_test_t, y_test, class_names, "MLP")
        plot_precision_recall(mlp_model, X_test_t, y_test, class_names, "MLP")

        # Plot training history
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        axes[0].plot(history["train_loss"], label="Train")
        axes[0].plot(history["val_loss"],   label="Val")
        axes[0].set_title("Loss Curve")
        axes[0].set_xlabel("Epoch")
        axes[0].legend()
        axes[1].plot(history["val_acc"])
        axes[1].set_title("Validation Accuracy")
        axes[1].set_xlabel("Epoch")
        plt.tight_layout()
        plt.savefig(ROOT / "reports" / "mlp_training_history.png", dpi=150)
        plt.close()

    # ── 10. Comparison ────────────────────────────────────────────────────────
    if len(results) > 1:
        compare_models(results)
        plot_calibration_curve(trained_models, X_test_t, y_test, class_idx=0, class_name="Benign")

    print("\n[Train] Pipeline complete. All artifacts saved to saved_models/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-smote", action="store_true")
    parser.add_argument("--models", default="all", help="all | lr | rf | xgb | lgbm | mlp")
    args = parser.parse_args()
    main(use_smote=not args.no_smote, models=args.models)
