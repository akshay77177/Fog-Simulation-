import json
import math
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as patches
import random

# --- Load Simulation Data ---
try:
    with open("simulation_log.json", "r") as f:
        events = json.load(f) #4️⃣
except FileNotFoundError as e:
    print(f"Error: simulation_log.json not found. Details: {e}")
    print("Please run 'secure_fog_simulation.py' first to generate the log file.")
    exit()
except json.JSONDecodeError as e:
    print("Error: simulation_log.json not found.")
    print("Please run 'secure_fog_simulation.py' first to generate the log file.")
    exit()

# --- Visualization Configuration ---
CLUSTER_RADIUS = 0.28
clusters = ["cluster_1", "cluster_2", "cluster_3"]
mobile_nodes = list(set(e['node'] for e in events if e['type'] in ['INITIAL', 'MOVE'])) # 1️⃣

# --- Visualization Setup ---
fig, ax = plt.subplots(figsize=(12, 9))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

# Positions for fixed nodes
positions = {
    "area_leader": (0.5, 0.9),
    "cluster_1": (0.25, 0.5),
    "cluster_2": (0.75, 0.5),
    "cluster_3": (0.5, 0.15),
}

# --- Create Artists ---

# Title that updates with simulation time
title = ax.text(0.5, 0.97, "", ha="center", fontsize=16, weight='bold')

# Circles for cluster areas
for c_name in clusters:
    pos = positions[c_name]
    circle = patches.Circle(pos, CLUSTER_RADIUS, color='skyblue', alpha=0.2, zorder=0)
    ax.add_patch(circle)

# Text objects for fixed nodes (Leaders)
node_texts = {}
for node, pos in positions.items():
    node_texts[node] = ax.text(pos[0], pos[1], node.replace('_', ' ').title(),
                               fontsize=12, ha="center", va="center",
                               bbox=dict(boxstyle="round,pad=0.4", fc="lightblue", ec="black", lw=1.5),
                               zorder=10)

# Text objects for mobile nodes
member_node_texts = {
    node: ax.text(0, 0, node.replace('_', ' ').title(), fontsize=9, ha="center", va="center",
                  bbox=dict(boxstyle="circle,pad=0.3", fc="lightyellow", ec="gray"), zorder=5)
    for node in mobile_nodes
}

# Text for seed and keys
seed_text = ax.text(0.02, 0.95, "", ha="left", fontsize=11, color="purple")
key_text = ax.text(0.02, 0.92, "", ha="left", fontsize=11, color="darkgreen")
status_text = ax.text(0.5, -0.02, "", ha="center", fontsize=12, color="darkred")

# --- Helper Functions ---

def get_random_point_in_circle(cluster_center, radius):
    """Calculates a random (x, y) position inside a circle."""
    r = radius * math.sqrt(random.random()) * 0.8
    theta = random.random() * 2 * math.pi
    x = cluster_center[0] + r * math.cos(theta)
    y = cluster_center[1] + r * math.sin(theta)
    return (x, y)

# Store current assignments and positions
member_node_assignments = {}
member_node_positions = {}

# --- Animation Function ---

def update(frame):
    event = events[frame]
    time = event['time']

    title.set_text(f"Fog Security Dashboard | Simulation Time: {time:.2f}s")
    status_text.set_text("") # Clear status text each frame

    # Reset colors from previous frame
    node_texts["area_leader"].get_bbox_patch().set_facecolor('lightblue')
    for c in clusters:
        node_texts[c].get_bbox_patch().set_facecolor('lightblue')
    for m in mobile_nodes:
        if member_node_assignments.get(m, {}).get("status") != "ATTACKER":
             member_node_texts[m].get_bbox_patch().set_facecolor('lightyellow')


    # Process the event for the current frame
    if event['type'] == 'INITIAL':
        node = event['node']
        location = event['location']
        member_node_assignments[node] = {"location": location, "status": "NORMAL"}
        cluster_pos = positions[location]
        pos = get_random_point_in_circle(cluster_pos, CLUSTER_RADIUS)
        member_node_positions[node] = pos
        member_node_texts[node].set_position(pos)

    elif event['type'] == 'REKEY':
        node_texts["area_leader"].get_bbox_patch().set_facecolor('orange')
        for c in clusters:
            node_texts[c].get_bbox_patch().set_facecolor('lightgreen')
        seed_text.set_text(f"New Seed: {event['seed']}")
        key_text.set_text(f"Derived Key: {event['key']}")

    elif event['type'] == 'MOVE':
        node = event['node']
        new_location = event['to']
        status = event['status']

        member_node_assignments[node] = {"location": new_location, "status": status}
        cluster_pos = positions[new_location]
        new_pos = get_random_point_in_circle(cluster_pos, CLUSTER_RADIUS)
        member_node_positions[node] = new_pos
        member_node_texts[node].set_position(new_pos)

        if status == 'ATTACKER':
            member_node_texts[node].get_bbox_patch().set_facecolor('lightcoral')
            status_text.set_text(f"ALERT: Suspicious movement detected for {node.replace('_', ' ').title()}!") # 2️⃣
        else:
            member_node_texts[node].get_bbox_patch().set_facecolor('khaki') # Highlight normal move

    # Return all artists that could have been changed
    all_artists = list(node_texts.values()) + list(member_node_texts.values())
    all_artists.extend([title, seed_text, key_text, status_text])
    return all_artists

# --- Run Animation ---
# 3️⃣
ani = animation.FuncAnimation(
    fig,
    update,
    frames=len(events),
    interval=200,  # Milliseconds between frames
    blit=False,
    repeat=True # 5️⃣
)

plt.tight_layout(pad=2.0)
plt.show()
