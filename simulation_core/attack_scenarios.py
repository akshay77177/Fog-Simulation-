import logging
import random

class AttackScenarioController:
    """Controls attack scenario triggers in the fog simulation."""

    def __init__(self, sim, ai_monitor):
        self.sim = sim
        self.ai_monitor = ai_monitor
        self.logger = logging.getLogger(__name__)

    # Scenario 1: Frequent movement
    def trigger_frequent_movement(self, sim=None):
        """Simulate nodes moving frequently between clusters."""
        self.logger.info("⚠️ Triggering Attack Scenario 1: Frequent Movement")
        mobile_nodes = [n for n, d in self.sim.topology.G.nodes(data=True) if d.get('type') == 'MOBILE']
        cluster_nodes = [n for n, d in self.sim.topology.G.nodes(data=True) if d.get('type') == 'CLUSTER']

        for _ in range(5):  # 5 quick moves per node
            node = random.choice(mobile_nodes)
            new_cluster = random.choice(cluster_nodes)
            if self.sim.topology.G.has_edge(node, new_cluster):
                continue
            # Reconnect
            for neighbor in list(self.sim.topology.G.neighbors(node)):
                self.sim.topology.G.remove_edge(node, neighbor)
            self.sim.topology.G.add_edge(node, new_cluster, BW=5, PR=2)
            self.ai_monitor.check_node_movement(node, self.sim.env.now)

        self.logger.info("✅ Frequent Movement Attack triggered successfully.")

    # Scenario 2: Resource abuse
    def trigger_resource_abuse(self):
        """Simulate one node suddenly using heavy resources."""
        self.logger.info("⚠️ Triggering Attack Scenario 2: Resource Abuse")
        cluster_nodes = [n for n, d in self.sim.topology.G.nodes(data=True) if d.get('type') == 'CLUSTER']
        target = random.choice(cluster_nodes)
        self.sim.topology.G.nodes[target]['IPT'] *= 3
        self.sim.topology.G.nodes[target]['RAM'] *= 2
        self.logger.warning(f"Cluster {target} resource usage increased abnormally.")
        self.logger.info("✅ Resource Abuse Attack triggered successfully.")

    # Scenario 3: Unknown injection
    def trigger_unknown_injection(self):
        """Inject an unknown attacker node."""
        self.logger.info("⚠️ Triggering Attack Scenario 3: Unknown Node Injection")
        attacker = f"attacker_{random.randint(100,999)}"
        self.sim.topology.G.add_node(attacker, type="UNKNOWN", IPT=2000, RAM=2000)
        target_cluster = random.choice([n for n, d in self.sim.topology.G.nodes(data=True) if d.get('type') == 'CLUSTER'])
        self.sim.topology.G.add_edge(attacker, target_cluster, BW=10, PR=1)
        self.logger.warning(f"Injected new attacker node: {attacker} -> {target_cluster}")
        self.logger.info("✅ Unknown Node Injection triggered successfully.")

    # Scenario 4: Network packet flooding
    def trigger_network_flooding(self):
        """Simulate DDoS or flooding behavior."""
        self.logger.info("⚠️ Triggering Attack Scenario 4: Network Flooding")
        cluster_nodes = [n for n, d in self.sim.topology.G.nodes(data=True) if d.get('type') == 'CLUSTER']
        for node in cluster_nodes:
            for neighbor in self.sim.topology.G.neighbors(node):
                if 'BW' in self.sim.topology.G[node][neighbor]:
                    self.sim.topology.G[node][neighbor]['BW'] *= 10
        self.logger.warning("Network flooding simulated: Bandwidth usage spiked.")
        self.logger.info("✅ Network Flooding Attack triggered successfully.")
