"""
Simulates the hardware layer (sensors -> STM8 -> LoRa -> ... -> MQTT) that we
aren't building physically. Every few seconds it invents a plausible reading
for each fake node and sends it to the Backend exactly the way the real
Database & MQTT module would after receiving it off the MQTT broker.

Run this while the backend is running:
    python simulate_nodes.py

Two modes:
  --mode api   (default) posts to POST /telemetry/ingest on the backend — no broker needed
  --mode mqtt  publishes real MQTT messages to a broker (requires Mosquitto running)
"""

import argparse
import hashlib
import hmac
import random
import time
from datetime import datetime, timezone

import requests

API_BASE = "http://localhost:8000"
JWT_SECRET = "change-this-in-production"  # must match backend/.env JWT_SECRET

NODE_IDS = ["node-01", "node-02", "node-03"]


def compute_checksum(node_id: str, timestamp: str, battery: int) -> str:
    payload = f"{node_id}:{timestamp}:{battery}".encode()
    return hmac.new(JWT_SECRET.encode(), payload, hashlib.sha256).hexdigest()[:16]


def fake_reading(node_id: str) -> dict:
    # Occasionally simulate an "intrusion-like" event so you can see alerts fire
    dramatic = random.random() < 0.12
    motion = dramatic or random.random() < 0.2
    vibration = dramatic or random.random() < 0.1
    sound = round(random.uniform(70, 95) if dramatic else random.uniform(20, 55), 1)
    battery = random.randint(5, 100)
    timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "node_id": node_id,
        "motion": motion,
        "vibration": vibration,
        "temperature": round(random.uniform(18, 32), 1),
        "sound_level": sound,
        "battery": battery,
        "timestamp": timestamp,
        "checksum": compute_checksum(node_id, timestamp, battery),
    }


def run_api_mode(interval: float):
    print(f"Publishing fake telemetry to {API_BASE}/telemetry/ingest every {interval}s. Ctrl+C to stop.")
    while True:
        for node_id in NODE_IDS:
            packet = fake_reading(node_id)
            try:
                resp = requests.post(f"{API_BASE}/telemetry/ingest", json=packet, timeout=5)
                print(f"[{node_id}] {resp.status_code} motion={packet['motion']} "
                      f"vibration={packet['vibration']} sound={packet['sound_level']} "
                      f"battery={packet['battery']}")
            except requests.RequestException as e:
                print(f"[{node_id}] failed to reach backend: {e}")
        time.sleep(interval)


def run_mqtt_mode(interval: float):
    import json
    import paho.mqtt.client as mqtt

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.connect("localhost", 1883, 60)
    print(f"Publishing fake telemetry over MQTT every {interval}s. Ctrl+C to stop.")
    while True:
        for node_id in NODE_IDS:
            packet = fake_reading(node_id)
            topic = f"nodonomy/nodes/{node_id}/data"
            client.publish(topic, json.dumps(packet))
            print(f"[{node_id}] published to {topic}")
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["api", "mqtt"], default="api")
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()

    if args.mode == "api":
        run_api_mode(args.interval)
    else:
        run_mqtt_mode(args.interval)
