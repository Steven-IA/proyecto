import argparse
import hashlib
import math
import os
import sqlite3
import numpy as np
import pandas as pd

GENERATOR_VERSION = "v2.1.0"
ORIGINAL_PATH = os.path.join("data", "network_behavior.csv")
OUTPUT_DEFAULT = os.path.join("data", "network_behavior_expanded.csv")
QUARANTINE_DEFAULT = os.path.join("data", "network_behavior_quarantine.csv")
FEATURE_COLUMNS = ["conn_count", "conn_freq", "ports", "bytes_sent", "bytes_recv", "duration", "activity_var", "comm_freq"]
LABEL_COLUMN = "label"
METADATA_COLUMNS = ["data_source", "scenario", "generator_version", "seed"]


def _finite(value):
    try:
        return not (isinstance(value, float) and (math.isnan(value) or math.isinf(value)))
    except Exception:
        return False


def validate_network_row(row):
    try:
        for col in FEATURE_COLUMNS:
            value = row[col]
            if pd.isna(value) or not _finite(value):
                return False
            if float(value) < 0:
                return False
        if int(row[LABEL_COLUMN]) not in (0, 1):
            return False
        return True
    except Exception:
        return False


def _feature_hash(values):
    payload = "|".join(repr(float(v)) for v in values)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _init_hash_db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS hashes (h TEXT PRIMARY KEY)")
    conn.commit()
    return conn


def _rebuild_hash_db(output_path, hash_db_path, feature_cols):
    conn = _init_hash_db(hash_db_path)
    conn.execute("DELETE FROM hashes")
    conn.commit()
    if os.path.exists(output_path):
        for chunk in pd.read_csv(output_path, chunksize=50000):
            hashes = [_feature_hash(tuple(row)) for row in chunk[feature_cols + [LABEL_COLUMN]].itertuples(index=False, name=None)]
            conn.executemany("INSERT OR IGNORE INTO hashes (h) VALUES (?)", [(h,) for h in hashes])
            conn.commit()
    return conn


def _load_or_create_hash_db(output_path, hash_db_path, feature_cols):
    if os.path.exists(hash_db_path):
        return _init_hash_db(hash_db_path)
    return _rebuild_hash_db(output_path, hash_db_path, feature_cols)


def generate_network_batch(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    scenarios = rng.choice(["normal", "suspicious", "anomalous"], size=n, p=[0.45, 0.35, 0.20])
    parts = []
    for scenario in ("normal", "suspicious", "anomalous"):
        mask = scenarios == scenario
        count = int(mask.sum())
        if count == 0:
            continue
        if scenario == "normal":
            conn_count = rng.normal(45, 15, count)
            conn_freq = rng.normal(5, 3, count)
            ports = rng.normal(4, 2, count)
            bytes_sent = rng.normal(900, 300, count)
            bytes_recv = rng.normal(700, 250, count)
            duration = rng.normal(10, 5, count)
            activity_var = rng.normal(3, 2, count)
            comm_freq = rng.normal(5, 3, count)
        elif scenario == "suspicious":
            conn_count = rng.normal(110, 40, count)
            conn_freq = rng.normal(18, 8, count)
            ports = rng.normal(10, 5, count)
            bytes_sent = rng.normal(3200, 1000, count)
            bytes_recv = rng.normal(2600, 900, count)
            duration = rng.normal(30, 12, count)
            activity_var = rng.normal(10, 4, count)
            comm_freq = rng.normal(18, 8, count)
        else:
            conn_count = rng.normal(200, 60, count)
            conn_freq = rng.normal(45, 15, count)
            ports = rng.normal(18, 8, count)
            bytes_sent = rng.normal(6500, 1800, count)
            bytes_recv = rng.normal(5200, 1500, count)
            duration = rng.normal(65, 20, count)
            activity_var = rng.normal(22, 8, count)
            comm_freq = rng.normal(40, 12, count)

        conn_count = np.clip(conn_count, 0, None)
        conn_freq = np.clip(conn_freq, 0, None)
        ports = np.clip(ports, 0, None)
        bytes_sent = np.clip(bytes_sent, 0, None)
        bytes_recv = np.clip(bytes_recv, 0, None)
        duration = np.clip(duration, 0, None)
        activity_var = np.clip(activity_var, 0, None)
        comm_freq = np.clip(comm_freq, 0, None)

        # Latent score with overlap to avoid trivial single-feature separation.
        score = (
            conn_count / 120.0
            + conn_freq / 25.0
            + ports / 12.0
            + bytes_sent / 3500.0
            + bytes_recv / 2800.0
            + duration / 35.0
            + activity_var / 12.0
            + comm_freq / 25.0
        )
        prob = 1 / (1 + np.exp(-(score - 3.0)))
        prob = np.clip(prob + rng.normal(0, 0.12, count), 0, 1)
        labels = (rng.random(count) < prob).astype(int)

        part = pd.DataFrame({
            "conn_count": conn_count,
            "conn_freq": conn_freq,
            "ports": ports,
            "bytes_sent": bytes_sent,
            "bytes_recv": bytes_recv,
            "duration": duration,
            "activity_var": activity_var,
            "comm_freq": comm_freq,
            "label": labels,
            "data_source": "synthetic_v2",
            "scenario": scenario,
            "generator_version": GENERATOR_VERSION,
            "seed": seed,
        })
        parts.append(part)

    batch = pd.concat(parts, ignore_index=True)
    batch = batch.sample(frac=1, random_state=seed).reset_index(drop=True)

    # Validate rows.
    mask = batch.apply(validate_network_row, axis=1)
    rejected = int((~mask).sum())
    batch = batch[mask].reset_index(drop=True)
    batch = batch.drop_duplicates(subset=FEATURE_COLUMNS + [LABEL_COLUMN]).reset_index(drop=True)
    if rejected:
        print(f"Lote {seed}: {rejected} registros rechazados por validación", flush=True)
    return batch


def generate_expanded_dataset(output_path: str, original_path: str, n_new: int, batch_size: int = 50000, seed: int = 2025, resume: bool = False):
    hash_db_path = output_path + ".hashes.sqlite"
    original_quarantine_path = original_path.replace(".csv", "_quarantine.csv")

    if not os.path.exists(output_path) or not resume:
        # Separate original valid/invalid rows.
        original = pd.read_csv(original_path)
        valid_mask = original.apply(validate_network_row, axis=1)
        valid_original = original[valid_mask].copy()
        invalid_original = original[~valid_mask].copy()

        if not invalid_original.empty:
            invalid_original.to_csv(original_quarantine_path, index=False, mode="w")
            print(f"Registros originales en cuarentena: {len(invalid_original)}", flush=True)

        valid_original = valid_original.copy()
        valid_original["data_source"] = "original"
        valid_original["scenario"] = "original"
        valid_original["generator_version"] = "original"
        valid_original["seed"] = 42
        valid_original.to_csv(output_path, index=False, mode="w")
        print(f"Registros originales válidos conservados: {len(valid_original)}", flush=True)

        conn = _init_hash_db(hash_db_path)
        conn.execute("DELETE FROM hashes")
        conn.commit()
        hashes = [_feature_hash(tuple(row)) for row in valid_original[FEATURE_COLUMNS + [LABEL_COLUMN]].itertuples(index=False, name=None)]
        conn.executemany("INSERT OR IGNORE INTO hashes (h) VALUES (?)", [(h,) for h in hashes])
        conn.commit()
    else:
        conn = _load_or_create_hash_db(output_path, hash_db_path, FEATURE_COLUMNS)

    seen = set(row[0] for row in conn.execute("SELECT h FROM hashes").fetchall())
    total_accepted = 0
    duplicates = 0
    current_seed = seed
    max_attempts = n_new * 3 + 1000
    attempts = 0
    while total_accepted < n_new and attempts < max_attempts:
        attempts += 1
        n = min(batch_size, n_new - total_accepted + 100)
        batch = generate_network_batch(n, current_seed)
        current_seed += 1
        accepted_rows = []
        for row in batch.itertuples(index=False, name=None):
            values = list(row[:len(FEATURE_COLUMNS) + 1])
            h = _feature_hash(values)
            if h in seen:
                duplicates += 1
                continue
            seen.add(h)
            accepted_rows.append(row)
            if total_accepted + len(accepted_rows) >= n_new:
                break

        if accepted_rows:
            out_df = pd.DataFrame(accepted_rows, columns=FEATURE_COLUMNS + [LABEL_COLUMN] + METADATA_COLUMNS)
            out_df.to_csv(output_path, index=False, mode="a", header=False)
            conn.executemany("INSERT OR IGNORE INTO hashes (h) VALUES (?)", [( _feature_hash(list(r[:len(FEATURE_COLUMNS)+1])) ,) for r in accepted_rows])
            conn.commit()
            total_accepted += len(accepted_rows)
            print(f"Generados {total_accepted}/{n_new} registros nuevos (duplicados descartados: {duplicates})", flush=True)

    conn.close()
    print(f"Dataset ampliado guardado en {output_path}")
    print(f"Registros nuevos aceptados: {total_accepted}")
    print(f"Duplicados descartados: {duplicates}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=1000000)
    parser.add_argument("--output", type=str, default=OUTPUT_DEFAULT)
    parser.add_argument("--original", type=str, default=ORIGINAL_PATH)
    parser.add_argument("--batch-size", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=2025)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    generate_expanded_dataset(args.output, args.original, args.rows, args.batch_size, args.seed, args.resume)


if __name__ == "__main__":
    main()