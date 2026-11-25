import os, json, requests
from ..config import settings

CACHE_DIR = os.path.join(settings.data_dir, "vuln_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def cache_path(key):
    return os.path.join(CACHE_DIR, f"{key}.json")

def lookup_nvd(keyword):
    cache = cache_path("nvd_" + keyword.replace(" ", "_"))
    if os.path.exists(cache):
        with open(cache) as f:
            return json.load(f)
    try:
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={keyword}"
        r = requests.get(url, timeout=10)
        data = r.json() if r.status_code == 200 else {}
        with open(cache, "w") as f:
            json.dump(data, f)
        return data
    except Exception:
        return {}

def scan_software(device_id, software, version):
    # Simple matching: query NVD and mark potential
    data = lookup_nvd(software)
    vulns = []
    for item in data.get("vulnerabilities", [])[:5]:
        cve = item.get("cve", {}).get("id", "CVE-?")
        desc = item.get("cve", {}).get("descriptions", [{}])[0].get("value", "")
        vulns.append({"cve_id": cve, "software": software, "version": version,
                      "severity": "potential", "description": desc,
                      "recommendation": "Verificar y actualizar", "fixed_version": "No disponible",
                      "verification_level": "potential"})
    return vulns