import random
import logging

simulation_log = []  # shared if imported elsewhere


class AI_Monitor:
    """Integrates with trained AI models for anomaly detection."""
    def __init__(self, ai_detector):
        self.ai_detector = ai_detector
        self.move_counts = {}

    def check_node_movement(self, node_id, time):
        """Collect movement data and get AI prediction."""
        if node_id not in self.move_counts:
            self.move_counts[node_id] = []
        self.move_counts[node_id].append(time)

        # Extract features for AI model (simple example)
        recent_moves = len([t for t in self.move_counts[node_id] if time - t < 300])
        features = [recent_moves, time % 100]  # arbitrary for demo

        result = self.ai_detector.predict("movement", features)
        logging.info(f"[AI_Monitor] Node {node_id} => {result}")
        return result


class MovementManager:
    """Manages mobile node movements in fog clusters."""
    def __init__(self, ai_monitor, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.ai_monitor = ai_monitor
        self.mobile_nodes = []
        self.cluster_nodes = []
        self.node_locations = {}
        self.initialized = False

    def initialize(self, sim):
        """Identify mobile and cluster nodes in topology."""
        for node_id, data in sim.topology.G.nodes(data=True):
            if data.get("type") == "MOBILE":
                self.mobile_nodes.append(node_id)
                for neighbor in sim.topology.G.neighbors(node_id):
                    if sim.topology.G.nodes[neighbor].get("type") == "CLUSTER":
                        self.node_locations[node_id] = neighbor
                        break
            elif data.get("type") == "CLUSTER":
                self.cluster_nodes.append(node_id)
        self.logger.info(f"[MovementManager] Mobile nodes: {self.mobile_nodes}")
        self.initialized = True

    def __call__(self, sim, routing, **kwargs):
        """Triggered periodically by YAFS monitor scheduler."""
        if not self.initialized:
            self.initialize(sim)

        if not self.mobile_nodes:
            return

        node_to_move = random.choice(self.mobile_nodes)
        current_location = self.node_locations.get(node_to_move)
        new_location = random.choice([c for c in self.cluster_nodes if c != current_location])

        # Detect anomaly
        status = self.ai_monitor.check_node_movement(node_to_move, sim.env.now)

        # Log event
        simulation_log.append({
            "time": sim.env.now,
            "type": "MOVE",
            "node": node_to_move,
            "from": current_location,
            "to": new_location,
            "status": status
        })

        # Modify topology
        if current_location and sim.topology.G.has_edge(node_to_move, current_location):
            sim.topology.G.remove_edge(node_to_move, current_location)
        sim.topology.G.add_edge(node_to_move, new_location, BW=5, PR=2)
        self.node_locations[node_to_move] = new_location
        routing.invalid_cache_value = True

        self.logger.info(
            f"TIME {sim.env.now:.2f} | Node {node_to_move} moved {current_location} → {new_location} | Status: {status}"
        )
