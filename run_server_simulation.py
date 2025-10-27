# run_server_simulation.py
import threading
import time
import uuid
import os
import random
from queue import Queue, Empty
import logging
from threading import Event

# YAFS imports and your modules
from yafs.core import Sim
from yafs.topology import Topology
from yafs.population import Population
from yafs.distribution import uniformDistribution, deterministic_distribution
# import other yafs modules as needed...

from simulation_core.attack_scenarios import AttackScenarioController
from simulation_core.movement_manager import MovementManager
from simulation_core.rekey_manager import RekeyingManager
from ai_integration.ai_detector import AIDetector

# Controller API (FastAPI) runs in a thread
from controllers.api_controller import start_api_server  # we'll add this file below
from streaming.stream_processor import StreamProcessor      # streaming consumer

# Globals
COMMAND_QUEUE = Queue()         # commands from UI/API -> simulation
TELEMETRY_QUEUE = Queue()       # telemetry from sim -> feature extractor
STOP_EVENT = Event()            # to signal graceful stop
RUN_ID = uuid.uuid4().hex[:8]
LOG_DIR = os.path.join("runs", RUN_ID)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("server_sim")

# -------------------------
# Helper: small-step simulation runner
# -------------------------
def run_continuous_sim(sim, routing, step_sim_time=10.0, checkpoint_interval=60):
    """
    Run the YAFS simulation in continuous slices.
    step_sim_time: how many simulation time units to advance per loop iteration
    checkpoint_interval: wall clock seconds between saving telemetry snapshots
    """
    last_checkpoint = time.time()
    logger.info(f"Starting continuous simulation (run_id={RUN_ID})")
    while not STOP_EVENT.is_set():
        # 1) Advance the simulation by a short slice
        next_until = sim.env.now + step_sim_time
        try:
            # If your YAFS version supports sim.run(until=...), use it:
            sim.run(until=next_until)
        except Exception as e:
            logger.exception("Error while advancing simulation slice: %s", e)
            break

        # 2) Process pending commands (attack triggers) - non-blocking
        while True:
            try:
                cmd = COMMAND_QUEUE.get_nowait()  # e.g., ("inject", payload)
            except Empty:
                break
            try:
                process_command(sim, routing, cmd)
            except Exception:
                logger.exception("Failed to process command: %s", cmd)

        # 3) Collect telemetry snapshot and push to TELEMETRY_QUEUE
        telemetry = collect_telemetry_snapshot(sim)
        for rec in telemetry:
            TELEMETRY_QUEUE.put(rec)

        # 4) Periodically checkpoint logs to disk
        if time.time() - last_checkpoint > checkpoint_interval:
            save_checkpoint(sim, telemetry, RUN_ID, LOG_DIR)
            last_checkpoint = time.time()

    # final graceful wrap-up
    logger.info("STOP event set - finishing simulation and saving final checkpoint")
    final_telemetry = collect_telemetry_snapshot(sim)
    save_checkpoint(sim, final_telemetry, RUN_ID, LOG_DIR)
    logger.info("Simulation stopped cleanly.")


# -------------------------
# Process a command: call into AttackScenarioController or managers
# -------------------------
def process_command(sim, routing, cmd):
    """
    cmd: tuple like ("trigger", {"type":"movement","params":{...}})
    """
    action, payload = cmd
    logger.info(f"Processing command: {action}, {payload}")
    # AttackScenarioController is flexible — see its definition below
    if action == "trigger_attack":
        atype = payload.get("attack_type")
        attack_controller.trigger(atype, payload.get("params", {}))
    elif action == "stop":
        STOP_EVENT.set()
    else:
        logger.warning("Unknown command: %s", action)


# -------------------------
# Telemetry collection - adapt to your topology & metrics
# -------------------------
def collect_telemetry_snapshot(sim):
    """
    Collect per-node metrics at current sim.env.now.
    Return list of dicts: {timestamp, node_id, cluster, cpu, mem, tx, rx, ...}
    Replace placeholder code with actual YAFS counters if available.
    """
    now = sim.env.now
    records = []
    for node_id, data in sim.topology.G.nodes(data=True):
        # Example simulated counters (you should replace with actual counters)
        cpu = data.get("IPT", 0) * 0.001 * (1 + 0.1 * random.random()) # pyright: ignore[reportUndefinedVariable]
        mem = data.get("RAM", 0) * (0.2 + 0.6 * random.random())
        rec = {
            "timestamp": now,
            "node_id": node_id,
            "type": data.get("type"),
            "cpu": cpu,
            "mem": mem,
            # add other simulated metrics or read from YAFS monitors
        }
        records.append(rec)
    return records


# -------------------------
# Checkpoint saver
# -------------------------
import json
def save_checkpoint(sim, telemetry, run_id, outdir):
    fname = f"checkpoint_{int(time.time())}.json"
    path = os.path.join(outdir, fname)
    try:
        with open(path, "w") as f:
            json.dump({
                "run_id": run_id,
                "time": sim.env.now,
                "telemetry_sample": telemetry[:200]  # avoid huge files
            }, f, indent=2)
        logger.info(f"Saved checkpoint to {path}")
    except Exception:
        logger.exception("Failed saving checkpoint")


# -------------------------
# Entrypoint
# -------------------------
if __name__ == "__main__":
    # Build topology & sim (adapt from your run_simulation)
    topo = Topology()
    # ... (build nodes / edges like before) ...
    # For brevity, assume you have a function create_topology() that returns topo
    from secure_fog_simulation import create_topology_and_app_and_placement  # you will add this
    topo, app, placement = create_topology_and_app_and_placement()

    # routing and sim
    class BroadcastShortestPath:  # lightweight placeholder, or import your class
        pass

    routing = None  # set appropriate routing object you used previously
    sim = Sim(topo)
    sim.deploy_app(app, placement, Population("EmptyPopulation"), routing)

    # load AI detector and managers
    ai_detector = AIDetector({
        "movement": "ai_integration/models/movement_model.pkl",
        "resource": "ai_integration/models/resource_abuse_model.pkl",
        "injection": "ai_integration/models/injection_model.pkl",
        "unknown": "ai_integration/models/unknown_scenario_model.pkl"
    })
    ai_monitor = MovementManager.AI_Monitor if False else None
    # you should instantiate your AI_Monitor wrapper that uses AIDetector
    from simulation_core.movement_manager import MovementManager, AI_Monitor as LocalAIMonitor
    ai_monitor = LocalAIMonitor(ai_detector)
    movement_manager = MovementManager(ai_monitor)
    sim.deploy_monitor("MovementManager", movement_manager, uniformDistribution(name="MoveDist", min=30, max=60), routing=routing)

    rekeying_manager = RekeyingManager()
    sim.deploy_monitor("RekeyingManager", rekeying_manager, deterministic_distribution(name="RekeyDist", time=120))

    # Attack controller
    attack_controller = AttackScenarioController(sim, ai_monitor, command_queue=COMMAND_QUEUE)  # ensure class accepts queue

    # Start API server (in background thread)
    api_thread = threading.Thread(target=start_api_server, args=(COMMAND_QUEUE,), daemon=True)
    api_thread.start()

    # Start StreamProcessor thread
    stream_proc = StreamProcessor(TELEMETRY_QUEUE, ai_detector)   # implement to accept queue and detector
    sp_thread = threading.Thread(target=stream_proc.run, daemon=True)
    sp_thread.start()

    # Run continuous sim
    try:
        run_continuous_sim(sim, routing, step_sim_time=5.0, checkpoint_interval=30)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, stopping simulation...")
        STOP_EVENT.set()
    finally:
        logger.info("Waiting for background threads to finish...")
        sp_thread.join(timeout=2)
        logger.info("Done.")
