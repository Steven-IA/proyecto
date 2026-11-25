import argparse
import hashlib
import math
import os
import sqlite3
import numpy as np
import pandas as pd

GENERATOR_VERSION = "v3.2.0"
ORIGINAL_PATH = os.path.join("data", "network_behavior.csv")
OUTPUT_DEFAULT = os.path.join("data", "network_behavior_v3.csv")
QUARANTINE_DEFAULT = os.path.join("data", "network_behavior_v3_quarantine.csv")
FEATURE_COLUMNS = ["conn_count", "conn_freq", "ports", "bytes_sent", "bytes_recv", "duration", "activity_var", "comm_freq"]
LABEL_COLUMN = "label"
METADATA_COLUMNS = ["data_source", "scenario", "generator_version", "seed", "family_id"]

SCENARIOS = ["baseline", "burst", "steady", "sparse"]

SCENARIO_OFFSETS = {
    "baseline": np.array([0, 0, 0, 0, 0, 0, 0, 0], dtype=float),
    "burst": np.array([40, 15, 6, 1500, 1200, 15, 6, 12], dtype=float),
    "steady": np.array([20, 6, 3, 800, 600, 8, 3, 6], dtype=float),
    "sparse": np.array([-25, -4, -3, -600, -500, -8, -3, -4], dtype=float),
}


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


def generate_network_batch(n: int, seed: int, family_prefix: str) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    family_index = 0
    base_rng = np.random.default_rng(seed + 999)
    while len(rows) < n:
        # Base behavior profile.
        base = np.array([
            base_rng.normal(80, 40),
            base_rng.normal(12, 8),
            base_rng.normal(8, 5),
            base_rng.normal(2500, 1200),
            base_rng.normal(2000, 1000),
            base_rng.normal(25, 14),
            base_rng.normal(8, 5),
            base_rng.normal(12, 8),
        ], dtype=float)
        base = np.clip(base, 0, None)
        family_id = f"{family_prefix}_{family_index}"
        family_index += 1
        for scenario in SCENARIOS:
            if len(rows) >= n:
                break
            noise = rng.normal(0, 1, size=8)
            values = base + SCENARIO_OFFSETS[scenario] + noise
            values = np.clip(values, 0, None)
            # Latent score with overlap.
            score = (
                values[0] / 100.0
                + values[1] / 20.0
                + values[2] / 10.0
                + values[3] / 3000.0
                + values[4] / 2500.0
                + values[5] / 30.0
                + values[6] / 10.0
                + values[7] / 20.0
            )
            rows.append({
                "conn_count": values[0],
                "conn_freq": values[1],
                "ports": values[2],
                "bytes_sent": values[3],
                "bytes_recv": values[4],
                "duration": values[5],
                "activity_var": values[6],
                "comm_freq": values[7],
                "score": score,
                "scenario": scenario,
                "family_id": family_id,
            })

    batch = pd.DataFrame(rows[:n])
    # Scenario-relative + global noise for label assignment.
    score = batch["score"].to_numpy()
    prob = 1 / (1 + np.exp(-(score - np.median(score))))
    prob = np.clip(prob + np.random.default_rng(seed).normal(0, 0.35, len(batch)), 0, 1)
    labels = (np.random.default_rng(seed + 1).random(len(batch)) < prob).astype(int)
    batch["label"] = labels
    batch = batch.drop(columns=["score"])
    batch["data_source"] = "synthetic_v3"
    batch["generator_version"] = GENERATOR_VERSION
    batch["seed"] = seed
    # Reorder columns for consistent hashing and output.
    batch = batch[FEATURE_COLUMNS + [LABEL_COLUMN] + METADATA_COLUMNS]
    batch = batch.sample(frac=1, random_state=seed).reset_index(drop=True)

    mask = batch.apply(validate_network_row, axis=1)
    rejected = int((~mask).sum())
    batch = batch[mask].reset_index(drop=True)
    batch = batch.drop_duplicates(subset=FEATURE_COLUMNS + [LABEL_COLUMN]).reset_index(drop=True)
    if rejected:
        print(f"Lote {seed}: {rejected} registros rechazados por validación", flush=True)
    return batch


def generate_expanded_dataset(output_path: str, original_path: str, n_new: int, batch_size: int = 50000, seed: int = 3025, resume: bool = False, family_size: int = 4):
    hash_db_path = output_path + ".hashes.sqlite"
    original_quarantine_path = original_path.replace(".csv", "_v3_quarantine.csv")

    if not os.path.exists(output_path) or not resume:
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
        valid_original["family_id"] = [f"original_{i}" for i in range(len(valid_original))]
        valid_original.to_csv(output_path, index=False, mode="w")
        print(f"Registros originales válidos conservados: {len(valid_original)}", flush=True)

        conn = sqlite3.connect(hash_db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS hashes (h TEXT PRIMARY KEY)")
        conn.execute("DELETE FROM hashes")
        conn.commit()
        hashes = [_feature_hash(tuple(row)) for row in valid_original[FEATURE_COLUMNS + [LABEL_COLUMN]].itertuples(index=False, name=None)]
        conn.executemany("INSERT OR IGNORE INTO hashes (h) VALUES (?)", [(h,) for h in hashes])
        conn.commit()
    else:
        conn = sqlite3.connect(hash_db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS hashes (h TEXT PRIMARY KEY)")
        conn.commit()

    seen = set(row[0] for row in conn.execute("SELECT h FROM hashes").fetchall())
    total_accepted = 0
    duplicates = 0
    current_seed = seed
    max_attempts = n_new * 3 + 1000
    attempts = 0
    while total_accepted < n_new and attempts < max_attempts:
        attempts += 1
        n = min(batch_size, n_new - total_accepted + 100)
        # Generate in families of family_size
        n_families = (n + family_size - 1) // family_size
        family_rows = n_families * family_size
        batch = generate_network_batch(family_rows, current_seed, f"net_family_{current_seed}")
        current_seed += 1
        # Trim to n
        batch = batch.head(n).reset_index(drop=True)
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
            conn.executemany("INSERT OR IGNORE INTO hashes (h) VALUES (?)", [(_feature_hash(list(r[:len(FEATURE_COLUMNS)+1])),) for r in accepted_rows])
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
    parser.add_argument("--seed", type=int, default=3025)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--family-size", type=int, default=4)
    args = parser.parse_args()
    generate_expanded_dataset(args.output, args.original, args.rows, args.batch_size, args.seed, args.resume, args.family_size)


if __name__ == "__main__":
    main()