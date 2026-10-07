"""MQTT → Telomy bridge for machines that publish telemetry over MQTT (e.g. HBOT controllers on the clinic network).

Topic:   telomy/<centre_id>/<device_id>/telemetry
Payload: {"ts": "2026-10-06T08:00:05", "pressure_ata": 1.32, "o2_pct": 94.1, "status": "running"}  (one sample or {"samples": [...]})

  pip install paho-mqtt
  TELOMY_SERVER=https://api.telomy.example DEVICE_KEYS='{"HBO-1": "tdk_..."}' python -m tools.mqtt_bridge --broker 192.168.1.10

Samples are buffered per device and forwarded every 5 s (or 100 samples). If the server is unreachable the buffer is kept
and retried, so a chamber's run is never lost (same principle as the patch's flash buffer inside the HBOT Faraday cage).
"""
import argparse
import json
import os
import threading
import time
import urllib.request

BUF: dict[str, list] = {}
LOCK = threading.Lock()


def flush(server: str, keys: dict):
    with LOCK:
        items = {d: s for d, s in BUF.items() if s}
        for d in items:
            BUF[d] = []
    for dev, samples in items.items():
        req = urllib.request.Request(f"{server}/devices/{dev}/telemetry", data=json.dumps({"samples": samples}).encode(),
                                     headers={"Content-Type": "application/json", "X-Device-Key": keys.get(dev, "")}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:  # noqa: BLE001
            print(f"[{dev}] server unreachable ({e}); keeping {len(samples)} samples")
            with LOCK:
                BUF[dev] = samples + BUF.get(dev, [])


def main():
    import paho.mqtt.client as mqtt
    ap = argparse.ArgumentParser()
    ap.add_argument("--broker", required=True)
    ap.add_argument("--port", type=int, default=1883)
    a = ap.parse_args()
    server = os.environ.get("TELOMY_SERVER", "http://127.0.0.1:8787")
    keys = json.loads(os.environ.get("DEVICE_KEYS", "{}"))

    def on_message(_c, _u, msg):
        dev = msg.topic.split("/")[2]
        body = json.loads(msg.payload)
        with LOCK:
            BUF.setdefault(dev, []).extend(body["samples"] if "samples" in body else [body])

    c = mqtt.Client()
    c.on_message = on_message
    c.connect(a.broker, a.port)
    c.subscribe("telomy/+/+/telemetry")
    c.loop_start()
    while True:
        time.sleep(5)
        flush(server, keys)


if __name__ == "__main__":
    main()
