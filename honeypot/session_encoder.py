# honeypot/session_encoder.py
from transformers import AutoTokenizer, AutoModel
import torch, redis, numpy as np

class SessionEncoder:
    def __init__(self):
        self.tok = AutoTokenizer.from_pretrained("microsoft/codebert-base")
        self.model = AutoModel.from_pretrained("microsoft/codebert-base")
        self.store = redis.Redis()

    def encode(self, commands: list[str]) -> np.ndarray:
        text = " [SEP] ".join(commands)
        inputs = self.tok(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            emb = self.model(**inputs).last_hidden_state[:, 0].numpy()
        return emb.squeeze()

    def store_session(self, session_id: str, emb: np.ndarray):
        self.store.set(f"emb:{session_id}", emb.tobytes())