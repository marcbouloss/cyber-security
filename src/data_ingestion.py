"""
data_ingestion.py
-----------------
Loads and prepares the CICIoT2023 dataset for training.
Handles label mapping, sampling, and train/val/test splitting.
"""

import os
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple, Dict

warnings.filterwarnings("ignore")

ROOT       = Path(__file__).resolve().parent.parent
DATA_DIR   = ROOT / "data"
RAW_DIR    = DATA_DIR / "raw"
PROC_DIR   = DATA_DIR / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROC_DIR.mkdir(parents=True, exist_ok=True)

# We group the 33 original attack labels into 8 families
# to make the classification problem cleaner and more meaningful
LABEL_MAP = {
    "BenignTraffic": "Benign",
    "DDoS-RSTFINFlood": "DDoS",
    "DDoS-PSHACK_Flood": "DDoS",
    "DDoS-SYN_Flood": "DDoS",
    "DDoS-UDP_Flood": "DDoS",
    "DDoS-TCP_Flood": "DDoS",
    "DDoS-ICMP_Flood": "DDoS",
    "DDoS-SynonymousIP_Flood": "DDoS",
    "DDoS-ACK_Fragmentation": "DDoS",
    "DDoS-UDP_Fragmentation": "DDoS",
    "DDoS-ICMP_Fragmentation": "DDoS",
    "DDoS-SlowLoris": "DDoS",
    "DDoS-HTTP_Flood": "DDoS",
    "DoS-UDP_Flood": "DoS",
    "DoS-SYN_Flood": "DoS",
    "DoS-TCP_Flood": "DoS",
    "DoS-HTTP_Flood": "DoS",
    "Mirai-greeth_flood": "Mirai",
    "Mirai-greip_flood": "Mirai",
    "Mirai-udpplain": "Mirai",
    "Recon-OSScan": "Recon",
    "Recon-PortScan": "Recon",
    "Recon-xMasScan": "Recon",
    "Recon-PingSweep": "Recon",
    "VulnerabilityScan": "Recon",
    "Recon-HostDiscovery": "Recon-HostDiscovery",
    "DictionaryBruteForce": "DictionaryBruteForce",
    "DNS_Spoofing": "Spoofing",
    "MITM-ArpSpoofing": "Spoofing",
    "BrowserHijacking": "Web",
    "CommandInjection": "Web",
    "SqlInjection": "Web",
    "XSS": "Web",
    "Backdoor_Malware": "Web",
    "Uploading_Attack": "Web",
}

FEATURE_COLS = [
    "flow_duration", "Header_Length", "Protocol Type", "Duration",
    "Rate", "Srate", "Drate", "fin_flag_number", "syn_flag_number",
    "rst_flag_number", "psh_flag_number", "ack_flag_number", "ece_flag_number",
    "cwr_flag_number", "ack_count", "syn_count", "fin_count", "urg_count",
    "rst_count", "HTTP", "HTTPS", "DNS", "Telnet", "SMTP", "SSH", "IRC",
    "TCP", "UDP", "DHCP", "ARP", "ICMP", "IPv", "LLC",
    "Tot sum", "Min", "Max", "AVG", "Std", "Tot size", "IAT",
    "Number", "Magnitue", "Radius", "Covariance", "Variance", "Weight",
]
LABEL_COL = "label"


def detect_presplit_files(directory: Path):
    files = sorted(directory.glob("*.csv"))
    train_f = next((f for f in files if "train" in f.name.lower()), None)
    val_f   = next((f for f in files if "val"   in f.name.lower()), None)
    test_f  = next((f for f in files if "test"  in f.name.lower()), None)
    if train_f and val_f and test_f:
        return train_f, val_f, test_f
    return None


def load_csv(path: Path) -> pd.DataFrame:
    print(f"  Loading {path.name} ...")
    return pd.read_csv(path, low_memory=False)


def load_csvs_from_dir(directory: Path) -> pd.DataFrame:
    files = sorted(directory.glob("*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No CSV files found in {directory}.\n"
            "Download CICIoT2023 from:\n"
            "  https://www.unb.ca/cic/datasets/iotdataset-2023.html\n"
            "and place the CSV files inside data/raw/"
        )
    print(f"[Ingest] Found {len(files)} CSV file(s)")
    chunks = []
    for f in files:
        df = pd.read_csv(f, low_memory=False)
        chunks.append(df)
    return pd.concat(chunks, ignore_index=True)


def validate_schema(df: pd.DataFrame) -> None:
    label_candidates = [c for c in df.columns if "label" in c.lower() or "class" in c.lower()]
    if not label_candidates:
        raise ValueError("No label column found.")
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        print(f"[Validate] WARNING - {len(missing)} feature columns missing: {missing[:5]}")
    else:
        print("[Validate] All 46 feature columns present.")


def inspect_class_balance(df: pd.DataFrame, label_col: str = LABEL_COL) -> None:
    counts = df[label_col].value_counts()
    total  = len(df)
    print("\n[Class Balance]")
    print(f"{'Class':<25} {'Count':>10} {'%':>8}")
    print("-" * 45)
    for cls, cnt in counts.items():
        print(f"{cls:<25} {cnt:>10,} {100*cnt/total:>7.2f}%")
    imbalance_ratio = counts.max() / counts.min()
    print(f"\n  Imbalance ratio: {imbalance_ratio:.1f}x")
    if imbalance_ratio > 10:
        print("  High imbalance - using class_weight=balanced and macro-F1.")


def preprocess_labels(df: pd.DataFrame) -> pd.DataFrame:
    label_candidates = [c for c in df.columns if "label" in c.lower() or "class" in c.lower()]
    raw_label_col = label_candidates[0]
    df = df.rename(columns={raw_label_col: "raw_label"})
    df[LABEL_COL] = df["raw_label"].map(LABEL_MAP)
    unknown = df[LABEL_COL].isna().sum()
    if unknown > 0:
        top_unknown = df.loc[df[LABEL_COL].isna(), "raw_label"].value_counts().head(5).to_dict()
        print(f"[Labels] {unknown:,} unmapped rows (keeping as-is): {top_unknown}")
        df.loc[df[LABEL_COL].isna(), LABEL_COL] = df.loc[df[LABEL_COL].isna(), "raw_label"]
    return df


def stratified_subset(df: pd.DataFrame, n_per_class: int = 20_000, seed: int = 42) -> pd.DataFrame:
    # Sample equally from each class so no single class dominates training
    groups = []
    for cls, grp in df.groupby(LABEL_COL):
        n = min(len(grp), n_per_class)
        groups.append(grp.sample(n=n, random_state=seed))
    subset = pd.concat(groups, ignore_index=True).sample(frac=1, random_state=seed)
    print(f"\n[Subset] {len(subset):,} rows across {subset[LABEL_COL].nunique()} classes.")
    return subset


def temporal_split(df: pd.DataFrame, val_frac: float = 0.15, test_frac: float = 0.15, seed: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Split by order rather than randomly to avoid leakage between similar flows
    n = len(df)
    train_end = int(n * (1 - val_frac - test_frac))
    val_end   = int(n * (1 - test_frac))
    train_df = df.iloc[:train_end].copy()
    val_df   = df.iloc[train_end:val_end].copy()
    test_df  = df.iloc[val_end:].copy()
    print(f"\n[Split] Train: {len(train_df):,}  Val: {len(val_df):,}  Test: {len(test_df):,}")
    return train_df, val_df, test_df


def check_data_quality(df: pd.DataFrame) -> Dict:
    numeric = df.select_dtypes(include=[np.number])
    report = {
        "total_rows": len(df),
        "total_cols": len(df.columns),
        "missing_cells": int(df.isnull().sum().sum()),
        "inf_cells": int(np.isinf(numeric.values).sum()),
        "constant_cols": [c for c in numeric.columns if numeric[c].nunique() <= 1],
        "duplicate_rows": int(df.duplicated().sum()),
    }
    print("\n[Data Quality]")
    for k, v in report.items():
        print(f"  {k}: {v}")
    if report["inf_cells"] > 0:
        print("  Infinite values found - replacing with NaN.")
    if report["constant_cols"]:
        print(f"  Constant columns (no useful info): {report['constant_cols']}")
    return report


def process_df(df: pd.DataFrame, n_per_class: int) -> pd.DataFrame:
    validate_schema(df)
    check_data_quality(df)
    df = preprocess_labels(df)
    available_features = [c for c in FEATURE_COLS if c in df.columns]
    df = df[available_features + [LABEL_COL]].copy()
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    return stratified_subset(df, n_per_class=n_per_class)


def run_ingestion(n_per_class: int = 20_000) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    print("=" * 60)
    print("  CICIoT2023 — Data Ingestion")
    print("=" * 60)

    presplit = detect_presplit_files(RAW_DIR)

    if presplit:
        train_file, val_file, test_file = presplit
        print(f"[Ingest] Using pre-split files:")
        print(f"  Train : {train_file.name}")
        print(f"  Val   : {val_file.name}")
        print(f"  Test  : {test_file.name}\n")

        train_df = process_df(load_csv(train_file), n_per_class)
        val_df   = process_df(load_csv(val_file),   n_per_class)
        test_df  = process_df(load_csv(test_file),  n_per_class)

        print("\n[Class Balance - full dataset]")
        inspect_class_balance(pd.concat([train_df, val_df, test_df]))
        print(f"\n[Split] Train: {len(train_df):,}  Val: {len(val_df):,}  Test: {len(test_df):,}")
    else:
        print("[Ingest] No pre-split files found - splitting manually.")
        df = load_csvs_from_dir(RAW_DIR)
        df = process_df(df, n_per_class)
        inspect_class_balance(df)
        train_df, val_df, test_df = temporal_split(df)

    train_df.to_parquet(PROC_DIR / "train.parquet", index=False)
    val_df.to_parquet(PROC_DIR / "val.parquet",     index=False)
    test_df.to_parquet(PROC_DIR / "test.parquet",   index=False)
    print(f"\n[Ingest] Done. Splits saved to {PROC_DIR}")

    return train_df, val_df, test_df


if __name__ == "__main__":
    run_ingestion()
