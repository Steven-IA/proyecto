import argparse
import os
import sys
import numpy as np
import pandas as pd

NETWORK_FEATURES = ["conn_count", "conn_freq", "ports", "bytes_sent", "bytes_recv", "duration", "activity_var", "comm_freq"]
SECURITY_FEATURES = ["firewall", "antivirus", "pending_updates", "os_age", "outdated", "vuln_apps", "excessive", "unnecessary", "unverified"]

def validate(path, feature_cols, label_col="label"):
    df = pd.read_csv(path)
    print("Archivo:", path)
    print("Shape:", df.shape)
    print("Columnas:", list(df.columns))
    missing = [c for c in feature_cols + [label_col, "data_source", "scenario", "generator_version", "seed"] if c not in df.columns]
    print("Columnas faltantes:", missing)
    print("Nulos:", int(df.isna().sum().sum()))
    print("Duplicados exactos:", int(df.duplicated().sum()))
    print("Distribución de etiquetas:", df[label_col].value_counts().to_dict())
    # non-negative checks for network
    if "conn_count" in df.columns:
        for c in NETWORK_FEATURES:
            bad = int((df[c] < 0).sum())
            if bad:
                print(f"Valores negativos en {c}: {bad}")
    print("Muestra:", df.head(3).to_dict(orient="records"))
    print("-" * 60)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", type=str, default=None)
    parser.add_argument("--security", type=str, default=None)
    args = parser.parse_args()
    if args.network:
        validate(args.network, NETWORK_FEATURES)
    if args.security:
        validate(args.security, SECURITY_FEATURES)

if __name__ == "__main__":
    main()