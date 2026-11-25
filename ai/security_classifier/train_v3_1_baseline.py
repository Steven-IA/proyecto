import os, sys, json, time, hashlib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, balanced_accuracy_score

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend", "app"))
from ai_models import SecurityClassifier  # noqa: may fail if not on path

# Fallback import
try:
    from ai_models import SecurityClassifier
except Exception:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    # define minimal if needed
    import torch.nn as nn
    class SecurityClassifier(nn.Module):
        def __init__(self, input_dim=9, hidden=32, num_classes=3):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, hidden), nn.ReLU(), nn.Dropout(0.2),
                nn.Linear(hidden, 16), nn.ReLU(), nn.Linear(16, num_classes))
        def forward(self, x): return self.net(x)

FEATURES = ["firewall","antivirus","pending_updates","os_age","outdated","vuln_apps","excessive","unnecessary","unverified"]
LABEL = "label"

def profile_signature(row):
    return hashlib.sha256("|".join(str(row[c]) for c in FEATURES).encode()).hexdigest()

def main():
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(base, "data", "security_features_v3_1_corrected.csv")
    model_dir = os.path.join(base, "models")
    os.makedirs(model_dir, exist_ok=True)

    print("Cargando dataset...")
    df = pd.read_csv(data_path)
    print("Registros:", len(df))

    # Build connected components by family_id and profile signature
    print("Construyendo componentes conectados...")
    df["_profile"] = df[FEATURES].apply(lambda r: profile_signature(r), axis=1)

    # Union-Find
    parent = list(range(len(df)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Union by family_id
    family_groups = df.groupby("family_id").indices
    for fam, idxs in family_groups.items():
        idxs = list(idxs)
        for i in range(1, len(idxs)):
            union(idxs[0], idxs[i])

    # Union by profile signature
    profile_groups = df.groupby("_profile").indices
    for prof, idxs in profile_groups.items():
        idxs = list(idxs)
        for i in range(1, len(idxs)):
            union(idxs[0], idxs[i])

    # Assign component id
    comp = np.array([find(i) for i in range(len(df))])
    df["_component"] = comp
    n_components = len(set(comp))
    print("Componentes conectados:", n_components)

    # Split by component
    groups = df["_component"].values
    y = df[LABEL].values
    gss = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=42)
    train_val_idx, test_idx = next(gss.split(df, y, groups))
    train_val_df = df.iloc[train_val_idx].copy()
    test_df = df.iloc[test_idx].copy()

    groups_tv = train_val_df["_component"].values
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.15/0.70, random_state=43)
    train_idx, val_idx = next(gss2.split(train_val_df, train_val_df[LABEL].values, groups_tv))
    train_df = train_val_df.iloc[train_idx].copy()
    val_df = train_val_df.iloc[val_idx].copy()

    # Verify leakage
    train_fam = set(train_df["family_id"])
    val_fam = set(val_df["family_id"])
    test_fam = set(test_df["family_id"])
    train_prof = set(train_df["_profile"])
    val_prof = set(val_df["_profile"])
    test_prof = set(test_df["_profile"])

    print("Leakage families:", len(train_fam & val_fam), len(train_fam & test_fam), len(val_fam & test_fam))
    print("Leakage profiles:", len(train_prof & val_prof), len(train_prof & test_prof), len(val_prof & test_prof))

    if len(train_fam & val_fam) > 0 or len(train_fam & test_fam) > 0 or len(val_fam & test_fam) > 0:
        print("ERROR: Family leakage detected. Aborting.")
        return
    if len(train_prof & val_prof) > 0 or len(train_prof & test_prof) > 0 or len(val_prof & test_prof) > 0:
        print("ERROR: Profile leakage detected. Aborting.")
        return

    # Distributions
    print("Train classes:", train_df[LABEL].value_counts().to_dict())
    print("Val classes:", val_df[LABEL].value_counts().to_dict())
    print("Test classes:", test_df[LABEL].value_counts().to_dict())

    # Features
    X_train = train_df[FEATURES].to_numpy(dtype="float32")
    y_train = train_df[LABEL].to_numpy()
    X_val = val_df[FEATURES].to_numpy(dtype="float32")
    y_val = val_df[LABEL].to_numpy()
    X_test = test_df[FEATURES].to_numpy(dtype="float32")
    y_test = test_df[LABEL].to_numpy()

    # Scaler
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)

    # Model
    model = SecurityClassifier(input_dim=9, hidden=32, num_classes=3)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    train_ds = TensorDataset(torch.tensor(X_train_s, dtype=torch.float32), torch.tensor(y_train))
    val_ds = TensorDataset(torch.tensor(X_val_s, dtype=torch.float32), torch.tensor(y_val))
    train_loader = DataLoader(train_ds, batch_size=256, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=256)

    best_val_acc = 0
    best_state = None
    patience = 5
    no_improve = 0
    train_losses = []
    val_losses = []
    start_time = time.time()

    for epoch in range(50):
        model.train()
        epoch_loss = 0
        for xb, yb in train_loader:
            optimizer.zero_grad()
            out = model(xb)
            loss = criterion(out, yb)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * xb.size(0)
        epoch_loss /= len(train_ds)
        train_losses.append(epoch_loss)

        model.eval()
        val_loss = 0
        val_preds = []
        with torch.no_grad():
            for xb, yb in val_loader:
                out = model(xb)
                loss = criterion(out, yb)
                val_loss += loss.item() * xb.size(0)
                val_preds.extend(out.argmax(1).tolist())
        val_loss /= len(val_ds)
        val_losses.append(val_loss)
        val_acc = accuracy_score(y_val, val_preds)
        print(f"Epoch {epoch+1}: train_loss={epoch_loss:.4f}, val_loss={val_loss:.4f}, val_acc={val_acc:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience:
                print("Early stopping")
                break

    # Load best
    if best_state:
        model.load_state_dict(best_state)
    model.eval()

    # Test evaluation
    with torch.no_grad():
        test_out = model(torch.tensor(X_test_s, dtype=torch.float32))
        test_preds = test_out.argmax(1).tolist()
    test_acc = accuracy_score(y_test, test_preds)
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, test_preds, average=None, labels=[0,1,2])
    macro_f1 = precision_recall_fscore_support(y_test, test_preds, average="macro")[2]
    weighted_f1 = precision_recall_fscore_support(y_test, test_preds, average="weighted")[2]
    bal_acc = balanced_accuracy_score(y_test, test_preds)
    cm = confusion_matrix(y_test, test_preds, labels=[0,1,2]).tolist()

    print("\n=== RESULTADOS TEST ===")
    print("Accuracy:", test_acc)
    print("Precision por clase:", prec.tolist())
    print("Recall por clase:", rec.tolist())
    print("F1 por clase:", f1.tolist())
    print("Macro-F1:", macro_f1)
    print("Weighted-F1:", weighted_f1)
    print("Balanced Accuracy:", bal_acc)
    print("Confusion Matrix:", cm)

    # Save model
    model_path = os.path.join(model_dir, "security_classifier_v3_1_baseline.pth")
    torch.save({"state_dict": model.state_dict(), "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist()}, model_path)
    print("Modelo guardado en:", model_path)

    # Save metrics
    metrics = {
        "accuracy": float(test_acc),
        "precision": [float(x) for x in prec],
        "recall": [float(x) for x in rec],
        "f1": [float(x) for x in f1],
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1),
        "balanced_accuracy": float(bal_acc),
        "confusion_matrix": cm,
        "train_classes": train_df[LABEL].value_counts().to_dict(),
        "val_classes": val_df[LABEL].value_counts().to_dict(),
        "test_classes": test_df[LABEL].value_counts().to_dict(),
        "epochs": len(train_losses),
        "best_val_acc": float(best_val_acc),
        "train_losses": train_losses,
        "val_losses": val_losses,
        "training_time_seconds": time.time() - start_time,
        "seed": 42,
        "dataset": "security_features_v3_1_corrected.csv",
        "limitation": "Datos sintéticos; no evidencia de detección real de amenazas.",
    }
    metrics_path = os.path.join(model_dir, "security_classifier_v3_1_baseline_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print("Métricas guardadas en:", metrics_path)

if __name__ == "__main__":
    main()