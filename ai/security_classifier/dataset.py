import numpy as np
import pandas as pd
import os

def generate_dataset(n=3000, seed=7):
    rng = np.random.default_rng(seed)
    firewall = rng.integers(0, 2, size=n)
    antivirus = rng.integers(0, 2, size=n)
    pending_updates = rng.integers(0, 10, size=n)
    os_age = rng.integers(0, 120, size=n)
    outdated = rng.integers(0, 8, size=n)
    vuln_apps = rng.integers(0, 6, size=n)
    excessive = rng.integers(0, 2, size=n)
    unnecessary = rng.integers(0, 6, size=n)
    unverified = rng.integers(0, 5, size=n)
    X = np.column_stack([firewall, antivirus, pending_updates, os_age, outdated, vuln_apps, excessive, unnecessary, unverified]).astype("float32")
    # label logic
    score = (1-firewall)*2 + (1-antivirus)*2 + pending_updates*0.5 + os_age/20 + outdated + vuln_apps*1.5 + excessive*2 + unnecessary*0.5 + unverified
    low_thr = np.quantile(score, 0.33)
    high_thr = np.quantile(score, 0.66)
    y = np.where(score < low_thr, 0, np.where(score < high_thr, 1, 2)).astype("int64")
    df = pd.DataFrame(X, columns=["firewall","antivirus","pending_updates","os_age","outdated","vuln_apps","excessive","unnecessary","unverified"])
    df["label"] = y
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/security_features.csv", index=False)
    return X, y

if __name__ == "__main__":
    generate_dataset()
    print("Dataset generado: data/security_features.csv")