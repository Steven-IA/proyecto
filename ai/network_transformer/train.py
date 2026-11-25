import os, sys, json
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, confusion_matrix

sys.path.insert(0, os.path.dirname(__file__))
from model import NetworkTransformer
from dataset import generate_dataset

def main():
    X, y = generate_dataset()
    X_train, X_tmp, y_train, y_tmp = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_tmp, y_tmp, test_size=0.5, random_state=42, stratify=y_tmp)
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    X_test = scaler.transform(X_test)

    def to_tensor(a): return torch.tensor(a, dtype=torch.float32)
    train_ds = TensorDataset(to_tensor(X_train), torch.tensor(y_train))
    val_ds = TensorDataset(to_tensor(X_val), torch.tensor(y_val))
    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=64)

    model = NetworkTransformer(input_dim=8)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    best_val = 0
    for epoch in range(20):
        model.train()
        for xb, yb in train_loader:
            optimizer.zero_grad()
            out = model(xb)
            loss = criterion(out, yb)
            loss.backward()
            optimizer.step()
        # val
        model.eval()
        preds = []
        with torch.no_grad():
            for xb, yb in val_loader:
                out = model(xb)
                preds.extend(out.argmax(1).tolist())
        acc = accuracy_score(y_val, preds)
        if acc > best_val:
            best_val = acc

    # test
    model.eval()
    with torch.no_grad():
        test_out = model(to_tensor(X_test))
        test_preds = test_out.argmax(1).tolist()
    test_acc = accuracy_score(y_test, test_preds)
    cm = confusion_matrix(y_test, test_preds).tolist()

    os.makedirs("models", exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist()}, "models/network_transformer.pth")
    metrics = {"accuracy": float(test_acc), "val_accuracy": float(best_val), "confusion_matrix": cm, "dataset": "synthetic (laboratorio)", "split": "70/15/15 train/val/test, scaler ajustado solo en train", "limitation": "Datos sintéticos; no evidencia de detección real de amenazas."}
    with open("models/network_transformer_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    main()