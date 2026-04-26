"""
mlp.py
------
Neural network (MLP) classifier using PyTorch.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
from typing import Optional, Tuple
import joblib

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "saved_models"


class IDS_MLP(nn.Module):
    """
    4-layer MLP for traffic classification.
    Uses BatchNorm to stabilize training and Dropout to prevent overfitting.
    """

    def __init__(self, n_features: int, n_classes: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(p=0.3),

            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(p=0.3),

            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(p=0.2),

            nn.Linear(64, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def compute_class_weights(y: np.ndarray, n_classes: int) -> torch.Tensor:
    # Give more weight to rare attack classes during training
    counts = np.bincount(y, minlength=n_classes).astype(float)
    weights = len(y) / (n_classes * np.maximum(counts, 1))
    return torch.tensor(weights, dtype=torch.float32)


def train_mlp(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val:   np.ndarray,
    y_val:   np.ndarray,
    n_classes: int,
    epochs: int = 50,
    batch_size: int = 512,
    lr: float = 1e-3,
    patience: int = 8,
    seed: int = 42,
    device: Optional[str] = None,
) -> Tuple[IDS_MLP, dict]:

    torch.manual_seed(seed)
    np.random.seed(seed)

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n[MLP] Training on {device}")

    def make_loader(X, y, shuffle):
        Xt = torch.tensor(X, dtype=torch.float32)
        yt = torch.tensor(y, dtype=torch.long)
        return DataLoader(TensorDataset(Xt, yt), batch_size=batch_size, shuffle=shuffle)

    train_loader = make_loader(X_train, y_train, shuffle=True)
    val_loader   = make_loader(X_val,   y_val,   shuffle=False)

    n_features = X_train.shape[1]
    model = IDS_MLP(n_features, n_classes).to(device)

    class_weights = compute_class_weights(y_train, n_classes).to(device)
    criterion  = nn.CrossEntropyLoss(weight=class_weights)
    optimizer  = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler  = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=3)

    history = {"train_loss": [], "val_loss": [], "val_acc": []}
    best_val_loss = float("inf")
    no_improve = 0
    best_state = None

    print(f"{'Epoch':>6} {'Train Loss':>12} {'Val Loss':>10} {'Val Acc':>9} {'LR':>10}")
    print("-" * 55)

    for epoch in range(1, epochs + 1):
        model.train()
        train_losses = []
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            loss = criterion(model(X_batch), y_batch)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            train_losses.append(loss.item())

        model.eval()
        val_losses, correct, total = [], 0, 0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                logits = model(X_batch)
                val_losses.append(criterion(logits, y_batch).item())
                correct += (logits.argmax(dim=1) == y_batch).sum().item()
                total   += len(y_batch)

        t_loss = np.mean(train_losses)
        v_loss = np.mean(val_losses)
        v_acc  = correct / total
        current_lr = optimizer.param_groups[0]["lr"]

        history["train_loss"].append(t_loss)
        history["val_loss"].append(v_loss)
        history["val_acc"].append(v_acc)

        scheduler.step(v_loss)

        if epoch % 5 == 0 or epoch == 1:
            print(f"{epoch:>6} {t_loss:>12.4f} {v_loss:>10.4f} {v_acc:>8.2%} {current_lr:>10.2e}")

        if v_loss < best_val_loss - 1e-4:
            best_val_loss = v_loss
            no_improve    = 0
            best_state    = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            no_improve += 1
            if no_improve >= patience:
                print(f"\n[MLP] Early stopping at epoch {epoch}")
                break

    if best_state:
        model.load_state_dict(best_state)

    torch.save(model.state_dict(), MODEL_DIR / "mlp_weights.pt")
    joblib.dump({"n_features": n_features, "n_classes": n_classes}, MODEL_DIR / "mlp_config.pkl")
    print(f"[MLP] Model saved. Best val loss: {best_val_loss:.4f}")

    return model, history


class MLPWrapper:
    def __init__(self, model: IDS_MLP, device: str = "cpu"):
        self.model  = model.to(device)
        self.device = device

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        self.model.eval()
        with torch.no_grad():
            Xt    = torch.tensor(X, dtype=torch.float32).to(self.device)
            probs = torch.softmax(self.model(Xt), dim=1)
        return probs.cpu().numpy()

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.predict_proba(X).argmax(axis=1)

    @staticmethod
    def load(model_dir: Path, device: str = "cpu") -> "MLPWrapper":
        cfg   = joblib.load(model_dir / "mlp_config.pkl")
        model = IDS_MLP(cfg["n_features"], cfg["n_classes"])
        # weights_only=True is the secure default starting with PyTorch 2.6 — it
        # restricts unpickling to plain tensors (no arbitrary code execution).
        model.load_state_dict(torch.load(model_dir / "mlp_weights.pt", map_location=device, weights_only=True))
        model.eval()
        return MLPWrapper(model, device)
