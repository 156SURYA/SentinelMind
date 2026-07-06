# mlops/federated_aggregator.py
import flwr as fl
import numpy as np
from typing import List, Tuple, Dict
from collections import OrderedDict
import torch
import torch.nn as nn


class FederatedAggregator:
    """
    Central aggregation server for federated learning across honeypot nodes.
    Each node trains locally on its sessions.
    Only model weight deltas are sent here — never raw session data.
    """

    def __init__(self, global_model: nn.Module):
        self.global_model = global_model
        self.round_number = 0

    def get_global_weights(self) -> List[np.ndarray]:
        return [
            val.cpu().numpy()
            for _, val in self.global_model.state_dict().items()
        ]

    def aggregate(self, client_updates: List[Tuple[List[np.ndarray], int]]) -> List[np.ndarray]:
        """
        Federated Averaging (FedAvg):
        Weighted average of client weight updates by number of local samples.
        """
        total_samples = sum(n for _, n in client_updates)
        averaged_weights = [
            np.zeros_like(w) for w in client_updates[0][0]
        ]

        for weights, n_samples in client_updates:
            weight = n_samples / total_samples
            for i, w in enumerate(weights):
                averaged_weights[i] += weight * w

        self._update_global_model(averaged_weights)
        self.round_number += 1
        print(f"[Federated] Round {self.round_number} complete. "
              f"Aggregated {len(client_updates)} nodes, "
              f"{total_samples} total samples.")

        return averaged_weights

    def _update_global_model(self, averaged_weights: List[np.ndarray]):
        state_dict = OrderedDict({
            k: torch.tensor(v)
            for k, v in zip(self.global_model.state_dict().keys(), averaged_weights)
        })
        self.global_model.load_state_dict(state_dict, strict=True)

    def save_global_model(self, path: str = "mlops/global_model.pt"):
        torch.save(self.global_model.state_dict(), path)
        print(f"[Federated] Global model saved to {path}")

    def load_global_model(self, path: str = "mlops/global_model.pt"):
        self.global_model.load_state_dict(torch.load(path))
        print(f"[Federated] Global model loaded from {path}")


class HoneypotFlowerClient(fl.client.NumPyClient):
    """
    Flower client that runs on each honeypot node.
    Trains locally and sends only weight updates to aggregator.
    """

    def __init__(self, model: nn.Module, train_data, node_id: str):
        self.model = model
        self.train_data = train_data
        self.node_id = node_id

    def get_parameters(self, config):
        return [val.cpu().numpy() for _, val in self.model.state_dict().items()]

    def set_parameters(self, parameters):
        state_dict = OrderedDict({
            k: torch.tensor(v)
            for k, v in zip(self.model.state_dict().keys(), parameters)
        })
        self.model.load_state_dict(state_dict, strict=True)

    def fit(self, parameters, config):
        self.set_parameters(parameters)
        # Local training on this node's session data
        # Wire your actual training loop here
        n_samples = len(self.train_data)
        print(f"[Node {self.node_id}] Local training on {n_samples} samples.")
        return self.get_parameters(config={}), n_samples, {}

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        # Local evaluation
        loss = float(np.random.uniform(0.1, 0.4))  # replace with real eval
        accuracy = float(np.random.uniform(0.85, 0.99))
        return loss, len(self.train_data), {"accuracy": accuracy}


def start_federated_server(num_rounds: int = 10, min_clients: int = 2):
    strategy = fl.server.strategy.FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=min_clients,
        min_evaluate_clients=min_clients,
        min_available_clients=min_clients,
    )
    fl.server.start_server(
        server_address="0.0.0.0:8080",
        config=fl.server.ServerConfig(num_rounds=num_rounds),
        strategy=strategy
    )