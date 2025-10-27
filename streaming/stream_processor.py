# streaming/stream_processor.py
import time
import logging
from queue import Empty

class StreamProcessor:
    def __init__(self, telemetry_queue, ai_detector, alert_path="runs/alerts.json"):
        self.telemetry_queue = telemetry_queue
        self.ai_detector = ai_detector
        self.running = True
        self.logger = logging.getLogger("StreamProcessor")
        self.alert_path = alert_path

    def run(self):
        buffer = {}
        while True:
            try:
                rec = self.telemetry_queue.get(timeout=1)
            except Empty:
                if not buffer and not self.running:
                    break
                continue

            # accumulate per-node short history
            node = rec["node_id"]
            hist = buffer.setdefault(node, [])
            hist.append(rec)
            # keep short window
            if len(hist) > 20:
                hist.pop(0)

            # compute simple features (replace with feature_extractor)
            cpu_vals = [r["cpu"] for r in hist]
            mem_vals = [r["mem"] for r in hist]
            features = [sum(cpu_vals)/len(cpu_vals), max(cpu_vals), sum(mem_vals)/len(mem_vals)]

            # detect using movement or resource model heuristics
            # Example call: self.ai_detector.predict("resource", features)
            try:
                pred = self.ai_detector.predict("resource", features)
            except Exception as e:
                self.logger.exception("AI detection failed: %s", e)
                pred = None

            if pred in (1, "ATTACK", "ATTACKER"):
                alert = {"time": rec["timestamp"], "node": node, "type": "resource", "score": None}
                self.logger.warning("ALERT: %s", alert)
                # store alert
                with open(self.alert_path, "a") as f:
                    f.write(str(alert) + "\n")
