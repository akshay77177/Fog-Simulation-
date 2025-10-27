import logging.config
import random
import json
import hashlib
import networkx as nx
import string

from yafs.core import Sim
from yafs.application import Application, Message
from yafs.topology import Topology
from yafs.placement import JSONPlacement
from yafs.selection import First_ShortestPath
from yafs.distribution import deterministic_distribution, uniformDistribution
from yafs.population import Population
from simulation_core.attack_scenarios import AttackScenarioController
from ai_integration.ai_detector import AIDetector
from simulation_core.movement_manager import MovementManager, AI_Monitor
from simulation_core.rekey_manager import RekeyingManager
from ai_integration.ai_detector import AIDetector


# --- Security & Helper Functions ---

def generate_seed(length=8):
    """Generates a random alphanumeric seed."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def derive_key(seed):
    """Derives a short key from a seed using SHA256."""
    return hashlib.sha256(seed.encode()).hexdigest()[:8]

# This list will store all simulation events for the dashboard
simulation_log = []

# --- Custom Mobility and AI Monitoring ---

class AI_Monitor:
    """A placeholder for the AI monitoring model."""
    def __init__(self):
        # In a real scenario, you would load a trained model here.
        # This simple rule flags a node as suspicious if it moves too often.
        self.move_counts = {}
        self.suspicion_threshold = 3 # Moves within a short time

    def check_node_movement(self, node_id, time):
        """Checks if a node's movement is suspicious."""
        if node_id not in self.move_counts:
            self.move_counts[node_id] = []

        self.move_counts[node_id].append(time)

        # Check for more than `suspicion_threshold` moves in the last 300 time units
        self.move_counts[node_id] = [t for t in self.move_counts[node_id] if time - t < 300]
        if len(self.move_counts[node_id]) > self.suspicion_threshold:
            logging.warning(f"TIME: {time} - AI_Monitor: Node {node_id} movement is SUSPICIOUS.")
            return "ATTACKER"
        else:
            logging.info(f"TIME: {time} - AI_Monitor: Node {node_id} movement is NORMAL.")
            return "NORMAL"


class MovementManager:
    """Manages the movement of mobile nodes between clusters."""
    def __init__(self, ai_monitor, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.ai_monitor = ai_monitor
        self.mobile_nodes = []
        self.cluster_nodes = []
        self.initialized = False
        self.node_locations = {}  # track locations: {mobile_node: cluster_node}

    def initialize(self, sim):
        """Identifies mobile and cluster nodes from the topology."""
        for node_id, data in sim.topology.G.nodes(data=True):
            if data.get('type') == 'MOBILE':
                self.mobile_nodes.append(node_id)
                # Find initial location by checking neighbors
                for neighbor in sim.topology.G.neighbors(node_id):
                    if sim.topology.G.nodes[neighbor].get('type') == 'CLUSTER':
                        self.node_locations[node_id] = neighbor
                        break
            elif data.get('type') == 'CLUSTER':
                self.cluster_nodes.append(node_id)
        self.logger.info(f"MovementManager initialized with mobile nodes: {self.mobile_nodes}")
        self.initialized = True

    def __call__(self, sim, routing, **kwargs):
        """This method is called periodically by the simulator to trigger a move."""
        if not self.initialized:
            self.initialize(sim)

        if not self.mobile_nodes:
            return

        # Pick a random node to move
        node_to_move = random.choice(self.mobile_nodes)
        current_location_id = self.node_locations.get(node_to_move)

        # Find a new cluster to move to
        possible_new_locations = [c for c in self.cluster_nodes if c != current_location_id]
        if not possible_new_locations:
            return
        new_location_id = random.choice(possible_new_locations)

        # Ask the AI monitor to classify the movement
        status = self.ai_monitor.check_node_movement(node_to_move, sim.env.now)

        # Log the movement event for the dashboard
        simulation_log.append({
            "time": sim.env.now,
            "type": "MOVE",
            "node": node_to_move,
            "from": current_location_id,
            "to": new_location_id,
            "status": status
        })

        # Execute the move in the simulation by changing topology links
        if current_location_id and sim.topology.G.has_edge(node_to_move, current_location_id):
            sim.topology.G.remove_edge(node_to_move, current_location_id)
        sim.topology.G.add_edge(node_to_move, new_location_id, BW=5, PR=2)
        self.node_locations[node_to_move] = new_location_id

        # Invalidate routing cache since topology changed
        routing.invalid_cache_value = True

        self.logger.info(
            f"TIME: {sim.env.now:.2f} - Node {node_to_move} moved from {current_location_id} to {new_location_id}"
        )

class RekeyingManager:
    """A custom monitor to handle the rekeying process."""
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def __call__(self, sim, **kwargs):
        """This method is called periodically by the simulator."""
        seed = generate_seed()
        derived = derive_key(seed)
        self.logger.info(f"TIME: {sim.env.now:.2f} - RekeyingManager: New seed: {seed} -> key: {derived}")

        simulation_log.append({
            "time": sim.env.now,
            "type": "REKEY",
            "seed": seed,
            "key": derived
        })

        # The message is sent automatically by the application definition.
        # This monitor just handles the logic/logging part of the event.
        self.logger.info(f"TIME: {sim.env.now:.2f} - Rekeying process initiated.")


def create_topology_and_app_and_placement():
    """Creates and returns the topology, application, and placement objects."""
    # 1. Create the Fog Topology
    topo = Topology()
    
    # Add nodes with types and resources for easier identification
    topo.G.add_node("area_leader", type="LEADER", IPT=5000, RAM=4000)
    for i in range(1, 4):
        cluster_name = f"cluster_{i}"
        topo.G.add_node(cluster_name, type="CLUSTER", RAM=10000, IPT=2000)
        topo.G.add_edge("area_leader", cluster_name, BW=10, PR=1)

    mobile_node_names = [f"iot_{i}" for i in range(5)]
    cluster_names = [f"cluster_{i}" for i in range(1, 4)]
    for name in mobile_node_names:
        # Each mobile node starts at a random cluster
        start_cluster = random.choice(cluster_names)
        topo.G.add_node(name, type="MOBILE", IPT=1000, RAM=1000)
        topo.G.add_edge(name, start_cluster, BW=5, PR=2)
        # Log initial position
        simulation_log.append({"time": 0, "type": "INITIAL", "node": name, "location": start_cluster})


    # 2. Define the Application in a YAFS-idiomatic way
    app = Application(name="SecureApp")
    
    # Define modules
    app.set_modules([
        {"AreaLeader": {"Type": "MODULE"}},
        {"ClusterLeader": {"Type": "MODULE"}}
    ])

    # Define message for rekeying
    rekey_msg = Message("RekeyingMessage", src="AreaLeader", dst="ClusterLeader", instructions=50, bytes=64)
    
    # AreaLeader module will broadcast the rekeying message periodically
    app.add_service_source("AreaLeader", message=rekey_msg, distribution=deterministic_distribution(name="RekeyingDistribution", time=120))

    # ClusterLeader module consumes the message (it's a sink for this message)
    app.add_service_module("ClusterLeader", message_in=rekey_msg)

    # 3. Define Placement
    placement = JSONPlacement(name="Placement", json={
        "initialAllocation": [
            {"app": "SecureApp", "module_name": "AreaLeader", "id_resource": "area_leader"},
            {"app": "SecureApp", "module_name": "ClusterLeader", "id_resource": "cluster_1"},
            {"app": "SecureApp", "module_name": "ClusterLeader", "id_resource": "cluster_2"},
            {"app": "SecureApp", "module_name": "ClusterLeader", "id_resource": "cluster_3"}
        ]
    })

    return topo, app, placement


# --- Main Simulation Setup ---

def run_simulation():
    # Setup Python's logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    topo, app, placement = create_topology_and_app_and_placement()

    # 4. Define Population (required by YAFS, even if empty)
    population = Population("EmptyPopulation")

    # 5. Define Routing and Simulation
    class BroadcastShortestPath(First_ShortestPath):
        def get_path(self, sim, app_name, message, topology_src, alloc_DES, alloc_module, traffic, from_des):
            paths, dst_idDES = [], []
            node_src = topology_src
            # This gets all DES processes for the destination module, e.g., all "ClusterLeader" instances
            DES_dst_list = alloc_module[app_name][message.dst]

            for des in DES_dst_list:
                dst_node = alloc_DES[des]
                try:
                    path = list(nx.shortest_path(sim.topology.G, source=node_src, target=dst_node))
                    paths.append(path)
                    dst_idDES.append(des)
                except nx.NetworkXNoPath:
                    self.logger.warning(f"No path from {node_src} to {dst_node}")
            return paths, dst_idDES

    routing = BroadcastShortestPath()
    sim = Sim(topo)

    # Deploy the applications
    sim.deploy_app(app, placement, population, routing)

    # 6. Setup and run the custom monitors
    ai_monitor = AI_Monitor()
    movement_manager = MovementManager(ai_monitor)
    move_dist = uniformDistribution(name="MoveDist", min=30, max=60)
    sim.deploy_monitor("MovementManager", movement_manager, move_dist, routing=routing)

    rekeying_manager = RekeyingManager()
    rekey_dist = deterministic_distribution(name="RekeyDist", time=120)
    sim.deploy_monitor("RekeyingManager", rekeying_manager, rekey_dist)

    # Initialize AttackScenarioController
    attack_controller = AttackScenarioController(sim,ai_monitor)

    # Trigger scenario manually or programmatically
   # Schedule attacks dynamically
    for time in range(200, 1000, 200):
        sim.deploy_monitor(f"Attack_{time}", attack_controller.trigger_frequent_movement, deterministic_distribution(name=f"AttackDist_{time}", time=time))

    # You can later switch to GUI/Dashboard button to trigger any scenario dynamically.

    # 7. Run the simulation
    simulation_duration = 1000  # Run for 1000 time units
    logging.info(f"Running simulation for {simulation_duration} seconds...")
    sim.run(until=simulation_duration)

    # 8. Save the event log to a file
    with open("simulation_log.json", "w") as f:
        json.dump(simulation_log, f, indent=4)
    logging.info("Simulation finished. Event log saved to simulation_log.json")



if __name__ == '__main__':
    run_simulation()