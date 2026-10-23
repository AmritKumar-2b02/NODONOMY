"""
Loads simulator/sample_dataset.json into the running Backend, one packet at a
time, using each packet's offset_seconds so timestamps land in a believable
order. Unlike simulate_nodes.py (random, infinite), this is fixed and finite —
good for reliable demos and screenshots.

Run this while the backend is running:
    python load_sample_data.py
"""

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

API_BASE = "http://localhost:8000"
JWT_SECRET = "myrandomsecretkey12345"  # must match backend/.env JWT_SECRET


def compute_checksum(node_id: str, timestamp: str, battery: int) -> str:
    payload = f"{node_id}:{timestamp}:{battery}".encode()
    return hmac.new(JWT_SECRET.encode(), payload, hashlib.sha256).hexdigest()[:16]


def main():
    dataset_path = Path(__file__).parent / "sample_dataset.json"
    dataset = json.loads(dataset_path.read_text())

    base_time = datetime.now(timezone.utc) - timedelta(seconds=110)  # so the last packet is "recent"
    packets = sorted(dataset["packets"], key=lambda p: p["offset_seconds"])

    print(f"Loading {len(packets)} sample packets across nodes: {', '.join(dataset['nodes'])}\n")

    for p in packets:
        timestamp = (base_time + timedelta(seconds=p["offset_seconds"])).isoformat()
        packet = {
            "node_id": p["node_id"],
            "motion": p["motion"],
            "vibration": p["vibration"],
            "temperature": p["temperature"],
            "sound_level": p["sound_level"],
            "battery": p["battery"],
            "timestamp": timestamp,
            "checksum": compute_checksum(p["node_id"], timestamp, p["battery"]),
        }
        try:
            resp = requests.post(f"{API_BASE}/telemetry/ingest", json=packet, timeout=5)
            status = "OK " if resp.status_code == 200 else f"FAIL({resp.status_code})"
        except requests.RequestException as e:
            status = f"FAIL({e})"

        print(f"[{status}] {p['node_id']:10s} — {p['note']}")
        time.sleep(0.3)  # small pause so the dashboard's live refresh is visibly incremental

    print("\nDone. Open the dashboard and refresh — you should see 3 nodes, "
          "a HIGH intrusion alert, a low-battery alert, and two low-priority events.")


if __name__ == "__main__":
    main()
