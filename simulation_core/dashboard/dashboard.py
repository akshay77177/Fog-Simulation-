import os
import json

# BASE_DIR = folder that contains simulation_log.json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # this is already simulation_core

LOG_PATH = os.path.join(BASE_DIR, "simulation_log.json")  # no extra 'simulation_core'

# Load the simulation log safely
if not os.path.exists(LOG_PATH):
    raise FileNotFoundError(f"Simulation log not found at {LOG_PATH}")

with open(LOG_PATH, "r") as f:
    simulation_log = json.load(f)

print(f"✅ Loaded {len(simulation_log)} events from simulation_log.json")
