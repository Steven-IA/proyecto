import argparse
import hashlib
import math
import os
import sqlite3
import numpy as np
import pandas as pd

GENERATOR_VERSION = "v2.1.0"
ORIGINAL_PATH = os.path.join("data", "security_features.csv")
OUTPUT_DEFAULT = os.path.join("data", "security_features_expanded.csv")
FEATURE_COLUMNS = ["firewall", "antivirus", "pending_updates", "os_age", "outdated", "vuln_apps", "excessive", "unnecessary", "unverified"]
LABEL_COLUMN = "label"
METADATA_COLUMNS = ["data_source", "scenario", "generator_version", "seed"]


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


def generate_security_batch(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    scenarios = rng.choice(["secure", "medium", "risky"], size=n, p=[0.4, 0.35, 0.25])
    parts = []
    for scenario in ("secure", "medium", "risky"):
        mask = scenarios == scenario
        count = int(mask.sum())
        if count == 0:
            continue
        if scenario == "secure":
            firewall = rng.choice([0, 1], size=count, p=[0.1, 0.9])
            antivirus = rng.choice([0, 1], size=count, p=[0.1, 0.9])
            pending_updates = rng.integers(0, 3, size=count)
            os_age = rng.integers(0, 36, size=count)
            outdated = rng.integers(0, 2, size=count)
            vuln_apps = rng.integers(0, 2, size=count)
            excessive = rng.choice([0, 1], size=count, p=[0.9, 0.1])
            unnecessary = rng.integers(0, 2, size=count)
            unverified = rng.integers(0, 2, size=count)
        elif scenario == "medium":
            firewall = rng.choice([0, 1], size=count, p=[0.35, 0.65])
            antivirus = rng.choice([0, 1], size=count, p=[0.35, 0.65])
            pending_updates = rng.integers(0, 6, size=count)
            os_age = rng.integers(24, 72, size=count)
            outdated = rng.integers(1, 4, size=count)
            vuln_apps = rng.integers(1, 4, size=count)
            excessive = rng.choice([0, 1], size=count, p=[0.7, 0.3])
            unnecessary = rng.integers(1, 4, size=count)
            unverified = rng.integers(1, 3, size=count)
        else:
            firewall = rng.choice([0, 1], size=count, p=[0.75, 0.25])
            antivirus = rng.choice([0, 1], size=count, p=[0.75, 0.25])
            pending_updates = rng.integers(4, 10, size=count)
            os_age = rng.integers(60, 120, size=count)
            outdated = rng.integers(3, 8, size=count)
            vuln_apps = rng.integers(2, 6, size=count)
            excessive = rng.choice([0, 1], size=count, p=[0.35, 0.65])
            unnecessary = rng.integers(2, 6, size=count)
            unverified = rng.integers(2, 5, size=count)

        score = (
            (1 - firewall) * 2
            + (1 - antivirus) * 2
            + pending_updates * 0.5
            + os_age / 20.0
            + outdated
            + vuln_apps * 1.5
            + excessive * 2
            + unnecessary * 0.5
            + unverified
        )
        score = score + rng.normal(0, 1.5, count)
        low_thr = np.quantile(score, 0.33)
        high_thr = np.quantile(score, 0.66)
        labels = np.where(score < low_thr, 0, np.where(score < high_thr, 1, 2)).astype(int)

        part = pd.DataFrame({
            "firewall": firewall.astype(int),
            "antivirus": antivirus.astype(int),
            "pending_updates": pending_updates.astype(int),
            "os_age": os_age.astype(int),
            "outdated": outdated.astype(int),
            "vuln_apps": vuln_apps.astype(int),
            "excessive": excessive.astype(int),
            "unnecessary": unnecessary.astype(int),
            "unverified": unverified.astype(int),
            "label": labels,
            "data_source": "synthetic_v2",
            "scenario": scenario,
            "generator_version": GENERATOR_VERSION,
            "seed": seed,
        })
        parts.append(part)

    batch = pd.concat(parts, ignore_index=True)
    batch = batch.sample(frac=1, random_state=seed).reset_index(drop=True)

    mask = batch.apply(validate_security_row, axis=1)
    rejected = int((~mask).sum())
    batch = batch[mask].reset_index(drop=True)
    batch = batch.drop_duplicates(subset=FEATURE_COLUMNS + [LABEL_COLUMN]).reset_index(drop=True)
    if rejected:
        print(f"Lote {seed}: {rejected} registros rechazados por validación", flush=True)
    return batch


def generate_expanded_dataset(output_path: str, original_path: str, n_new: int, batch_size: int = 50000, seed: int = 2026, resume: bool = False):
    hash_db_path = output_path + ".hashes.sqlite"
    original_quarantine_path = original_path.replace(".csv", "_quarantine.csv")

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
        valid_original.to_csv(output_path, index=False, mode="w")
        print(f"Registros originales válidos conservados: {len(valid_original)}", flush=True)

        conn = _init_hash_db(hash_db_path)
        conn.execute("DELETE FROM hashes")
        conn.commit()
        hashes = [_feature_hash(tuple(row)) for row in valid_original[FEATURE_COLUMNS + [LABEL_COLUMN]].itertuples(index=False, name=None)]
        conn.executemany("INSERT OR IGNORE INTO hashes (h) VALUES (?)", [(h,) for h in hashes])
        conn.commit()
    else:
        conn = _load_or_create_hash_db(output_path, hash_db_path)

    seen = set(row[0] for row in conn.execute("SELECT h FROM hashes").fetchall())
    total_accepted = 0
    duplicates = 0
    current_seed = seed
    max_attempts = n_new * 3 + 1000
    attempts = 0
    while total_accepted < n_new and attempts < max_attempts:
        attempts += 1
        n = min(batch_size, n_new - total_accepted + 100)
        batch = generate_security_batch(n, current_seed)
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
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    generate_expanded_dataset(args.output, args.original, args.rows, args.batch_size, args.seed, args.resume)


if __name__ == "__main__":
    main()