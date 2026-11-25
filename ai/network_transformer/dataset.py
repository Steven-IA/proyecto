import numpy as np
import pandas as pd
import os

def generate_dataset(n=2000, seed=42):
    rng = np.random.default_rng(seed)
    # normal samples
    normal = rng.normal(loc=[50, 5, 3, 1000, 800, 10, 2, 5],
                        scale=[10, 2, 1, 200, 200, 3, 1, 2], size=(n//2, 8))
    # anomalous samples
    anom = rng.normal(loc=[200, 50, 20, 5000, 100, 60, 20, 40],
                      scale=[30, 10, 5, 500, 100, 10, 5, 8], size=(n//2, 8))
    X = np.vstack([normal, anom]).astype("float32")
    y = np.array([0]*(n//2) + [1]*(n//2), dtype="int64")
    df = pd.DataFrame(X, columns=["conn_count","conn_freq","ports","bytes_sent","bytes_recv","duration","activity_var","comm_freq"])
    df["label"] = y
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/network_behavior.csv", index=False)
    return X, y

if __name__ == "__main__":
    generate_dataset()
    print("Dataset generado: data/network_behavior.csv")