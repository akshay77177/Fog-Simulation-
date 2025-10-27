import logging
import hashlib
import random
import string

simulation_log = []


def generate_seed(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def derive_key(seed):
    return hashlib.sha256(seed.encode()).hexdigest()[:8]


class RekeyingManager:
    """Handles periodic rekeying of fog nodes."""
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def __call__(self, sim, **kwargs):
        seed = generate_seed()
        key = derive_key(seed)

        simulation_log.append({
            "time": sim.env.now,
            "type": "REKEY",
            "seed": seed,
            "key": key
        })

        self.logger.info(f"[RekeyingManager] TIME {sim.env.now:.2f} | New key derived: {key}")
