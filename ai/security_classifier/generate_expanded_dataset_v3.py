import argparse
import hashlib
import math
import os
import sqlite3
import numpy as np
import pandas as pd

GENERATOR_VERSION = "v3.2.0"
ORIGINAL_PATH = os.path.join("data", "security_features.csv")
OUTPUT_DEFAULT = os.path.join("data", "security_features_v3.csv")
FEATURE_COLUMNS = ["firewall", "antivirus", "pending_updates", "os_age", "outdated", "vuln_apps", "excessive", "unnecessary", "unverified"]
LABEL_COLUMN = "label"
METADATA_COLUMNS = ["data_source", "scenario", "generator_version", "seed", "family_id"]

SCENARIOS = ["secure", "balanced", "risky", "mixed"]

SCENARIO_OFFSETS = {
    "secure": np.array([0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=float),
    "balanced": np.array([0, 0, 2, 20, 1, 1, 0, 1, 1], dtype=float),
    "risky": np.array([0, 0, 4, 50, 3, 2, 0, 2, 2], dtype=float),
    "mixed": np.array([0, 0, 1, 10, 0, 0, 0, 0, 0], dtype=float),
}


def _finite(value):
    try:
        return not (isinstance(value, float) and (math.isnan(value) or math.isinf(value)))
    except Exception:
        return False


def validate_security_row(row):
    try:
        if int(row["firewall"]) not in (0, 1):
            return False
        if int(row["antivirus"]) not in (0, 1):
            return False
        if int(row["excessive"]) not in (0, 1):
            return False
        for col in ("pending_updates", "os_age", "outdated", "vuln_apps", "unnecessary", "unverified"):
            value = row[col]
            if pd.isna(value) or not _finite(value):
                return False
            if float(value) < 0:
                return False
        if int(row[LABEL_COLUMN]) not in (0, 1, 2):
            return False
        return True
    except Exception:
        return False


def _feature_hash(values):
    payload = "|".join(repr(x) for x in values)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _init_hash_db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS hashes (h TEXT PRIMARY KEY)")
    conn.commit()
    return conn


def _rebuild_hash_db(output_path, hash_db_path):
    conn = _init_hash_db(hash_db_path)
    conn.execute("DELETE FROM hashes")
    conn.commit()
    if os.path.exists(output_path):
        for chunk in pd.read_csv(output_path, chunksize=50000):
            hashes = [_feature_hash(tuple(row)) for row in chunk[FEATURE_COLUMNS + [LABEL_COLUMN]].itertuples(index=False, name=None)]
            conn.executemany("INSERT OR IGNORE INTO hashes (h) VALUES (?)", [(h,) for h in hashes])
            conn.commit()
    return conn


def _load_or_create_hash_db(output_path, hash_db_path):
    if os.path.exists(hash_db_path):
        return _init_hash_db(hash_db_path)
    return _rebuild_hash_db(output_path, hash_db_path)


def generate_security_batch(n: int, seed: int, family_prefix: str) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    family_index = 0
    base_rng = np.random.default_rng(seed + 999)
    while len(rows) < n:
        base = np.array([
            base_rng.choice([0, 1]),
            base_rng.choice([0, 1]),
            base_rng.integers(0, 10),
            base_rng.integers(0, 120),
            base_rng.integers(0, 8),
            base_rng.integers(0, 6),
            base_rng.choice([0, 1]),
            base_rng.integers(0, 6),
            base_rng.integers(0, 5),
        ], dtype=float)
        family_id = f"{family_prefix}_{family_index}"
        family_index += 1
        for scenario in SCENARIOS:
            if len(rows) >= n:
                break
            # Scenario-specific offsets
            if scenario == "secure":
                offset = np.array([0, 0, -2, -30, -2, -1, 0, -1, -1], dtype=float)
            elif scenario == "balanced":
                offset = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=float)
            elif scenario == "risky":
                offset = np.array([0, 0, 3, 40, 2, 2, 0, 2, 2], dtype=float)
            else:
                offset = np.array([0, 0, 1, 10, 0, 0, 0, 0, 0], dtype=float)
            values = base + offset + rng.normal(0, 0.5, size=9)
            values[0] = 1 if values[0] >= 0.5 else 0
            values[1] = 1 if values[1] >= 0.5 else 0
            values[2] = int(np.clip(round(values[2]), 0, 9))
            values[3] = int(np.clip(round(values[3]), 0, 119))
            values[4] = int(np.clip(round(values[4]), 0, 7))
            values[5] = int(np.clip(round(values[5]), 0, 5))
            values[6] = 1 if values[6] >= 0.5 else 0
            values[7] = int(np.clip(round(values[7]), 0, 5))
            values[8] = int(np.clip(round(values[8]), 0, 4))

            firewall, antivirus, pending_updates, os_age, outdated, vuln_apps, excessive, unnecessary, unverified = values

            score = (
                (1 - firewall) * (1 + unverified)
                + (1 - antivirus) * (1 + vuln_apps)
                + pending_updates * 0.7
                + os_age / 25.0
                + outdated * 1.2
                + vuln_apps * 1.8
                + excessive * 2.5
                + unnecessary * 0.6
                + unverified * 1.1
            )
            score = score + rng.normal(0, 2.5, 1)[0]
            rows.append({
                "firewall": int(firewall),
                "antivirus": int(antivirus),
                "pending_updates": int(pending_updates),
                "os_age": int(os_age),
                "outdated": int(outdated),
                "vuln_apps": int(vuln_apps),
                "excessive": int(excessive),
                "unnecessary": int(unnecessary),
                "unverified": int(unverified),
                "score": score,
                "scenario": scenario,
                "family_id": family_id,
            })

    batch = pd.DataFrame(rows[:n])
    # Deterministic labels based on fixed thresholds derived from the original dataset.
    # score < 16.65 -> low (0), 16.65 <= score < 20.8 -> medium (1), score >= 20.8 -> high (2).
    score = batch["score"].to_numpy()
    labels = np.where(score < 16.65, 0, np.where(score < 20.8, 1, 2)).astype(int)
    batch["label"] = labels
    batch = batch.drop(columns=["score"])
    batch["data_source"] = "synthetic_v3"
    batch["generator_version"] = GENERATOR_VERSION
    batch["seed"] = seed
    batch = batch[FEATURE_COLUMNS + [LABEL_COLUMN] + METADATA_COLUMNS]
    batch = batch.sample(frac=1, random_state=seed).reset_index(drop=True)

    mask = batch.apply(validate_security_row, axis=1)
    rejected = int((~mask).sum())
    batch = batch[mask].reset_index(drop=True)
    batch = batch.drop_duplicates(subset=FEATURE_COLUMNS + [LABEL_COLUMN]).reset_index(drop=True)
    if rejected:
        print(f"Lote {seed}: {rejected} registros rechazados por validación", flush=True)
    return batch


def generate_expanded_dataset(output_path: str, original_path: str, n_new: int, batch_size: int = 50000, seed: int = 4026, resume: bool = False, family_size: int = 4):
    hash_db_path = output_path + ".hashes.sqlite"
    original_quarantine_path = original_path.replace(".csv", "_v3_quarantine.csv")

    if not os.path.exists(output_path) or not resume:
        original = pd.read_csv(original_path)
        valid_mask = original.apply(validate_security_row, axis=1)
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
        batch = generate_security_batch(n, current_seed, f"sec_family_{current_seed}")
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
    parser.add_argument("--seed", type=int, default=4026)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--family-size", type=int, default=4)
    args = parser.parse_args()
    generate_expanded_dataset(args.output, args.original, args.rows, args.batch_size, args.seed, args.resume, args.family_size)


if __name__ == "__main__":
    main()