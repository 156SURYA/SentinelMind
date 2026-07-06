# honeypot/anomaly_engine.py
from sklearn.ensemble import IsolationForest
import torch, torch.nn as nn

class SessionVAE(nn.Module):
    def __init__(self, input_dim=256, latent_dim=32):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dim, 128), nn.ReLU(),
                                      nn.Linear(128, latent_dim*2))
        self.decoder = nn.Sequential(nn.Linear(latent_dim, 128), nn.ReLU(),
                                      nn.Linear(128, input_dim))

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        return mu + std * torch.randn_like(std)

    def forward(self, x):
        h = self.encoder(x)
        mu, logvar = h.chunk(2, dim=-1)
        z = self.reparameterize(mu, logvar)
        return self.decoder(z), mu, logvar