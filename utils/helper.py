import os
import json
import datetime
import random
import numpy as np

# ==============================
# 🔹 Logger Utility
# ==============================
def log_event(message, level="INFO"):
    """Logs events with timestamps and severity levels."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)

    # Optional: Save logs to file
    with open("simulation_log.txt", "a") as log_file:
        log_file.write(log_line + "\n")


# ==============================
# 🔹 File Operations
# ==============================
def save_json(data, filename):
    """Saves Python dict/list as a JSON file."""
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        log_event(f"Saved JSON data to {filename}")
    except Exception as e:
        log_event(f"Failed to save JSON {filename}: {str(e)}", level="ERROR")


def load_json(filename):
    """Loads data from a JSON file."""
    if not os.path.exists(filename):
        log_event(f"File not found: {filename}", level="ERROR")
        return None

    try:
        with open(filename, "r") as f:
            return json.load(f)
    except Exception as e:
        log_event(f"Failed to load JSON {filename}: {str(e)}", level="ERROR")
        return None


# ==============================
# 🔹 Metric Utilities
# ==============================
def calculate_average(values):
    """Returns average from a list of values."""
    if not values:
        return 0
    return sum(values) / len(values)


def calculate_stddev(values):
    """Returns standard deviation."""
    if not values:
        return 0
    return float(np.std(values))


# ==============================
# 🔹 Random Event Simulation
# ==============================
def generate_random_latency(min_ms=10, max_ms=150):
    """Simulate random latency (ms) for fog communication."""
    return random.uniform(min_ms, max_ms)


def generate_node_load(cpu_min=10, cpu_max=90, mem_min=100, mem_max=500):
    """Simulate random CPU and memory usage for a fog node."""
    return {
        "cpu_usage": random.uniform(cpu_min, cpu_max),
        "mem_usage": random.uniform(mem_min, mem_max)
    }


# ==============================
# 🔹 Attack Scenario Helpers
# ==============================
def inject_attack_node(cluster_id, node_id):
    """Simulate injection of a new attacker node into the cluster."""
    attack_node = {
        "node_id": node_id,
        "cluster_id": cluster_id,
        "status": "attacker",
        "cpu_usage": random.uniform(90, 100),
        "mem_usage": random.uniform(400, 600),
        "latency": random.uniform(200, 500)
    }
    log_event(f"Injected attacker node {node_id} in cluster {cluster_id}", level="WARNING")
    return attack_node


def is_suspicious_node(node_data, cpu_threshold=85, mem_threshold=450):
    """Detect suspicious behavior based on resource consumption."""
    return (
        node_data["cpu_usage"] > cpu_threshold or
        node_data["mem_usage"] > mem_threshold
    )
