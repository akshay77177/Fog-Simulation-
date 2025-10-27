import joblib
import numpy as np
import logging

class AIDetector:
    def __init__(self, model_paths):
        """
        model_paths: dict with keys = attack types, values = file paths
        Example:
            {
                "movement": "models/movement_model.pkl",
                "resource": "models/resource_abuse_model.pkl",
                "injection": "models/injection_model.pkl"
            }
        """
        self.models = {}
        for name, path in model_paths.items():
            try:
                self.models[name] = joblib.load(path)
                logging.info(f"[AIDetector] Loaded {name} model from {path}")
            except Exception as e:
                logging.warning(f"[AIDetector] Could not load {name} model: {e}")

    def predict(self, attack_type, features):
        """
        attack_type: 'movement', 'resource', 'injection', etc.
        features: list or numpy array of input features for model
        """
        model = self.models.get(attack_type)
        if model is None:
            logging.warning(f"[AIDetector] No model for attack type: {attack_type}")
            return "UNKNOWN"

        try:
            features = np.array(features).reshape(1, -1)
            prediction = model.predict(features)
            return prediction[0]
        except Exception as e:
            logging.error(f"[AIDetector] Prediction error: {e}")
            return "ERROR"
