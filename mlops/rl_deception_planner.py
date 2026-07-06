# mlops/rl_deception_planner.py
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
import os

MODEL_PATH = "mlops/rl_deception_policy.zip"

# --- Deception action types the agent can choose ---
DECEPTION_ACTIONS = [
    "serve_fake_file",           # 0
    "inject_honeypot_credential",# 1
    "return_false_command_output",# 2
    "simulate_vulnerable_service",# 3
    "delay_response",            # 4
    "present_fake_network_share", # 5
    "expose_decoy_database",     # 6
    "mirror_attacker_commands"   # 7
]


class DeceptionEnv(gym.Env):
    """
    RL environment for adaptive deception planning.

    State  : session embedding (256-dim) + MITRE tactic vector (14-dim) = 270-dim
    Action : which deception response to serve (8 discrete actions)
    Reward : attacker continued engagement without detecting honeypot
    """

    def __init__(self):
        super().__init__()
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(270,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(len(DECEPTION_ACTIONS))

        self.current_state = None
        self.engagement_steps = 0
        self.max_steps = 50

    def reset(self, seed=None, options=None):
        self.current_state = np.random.randn(270).astype(np.float32)
        self.engagement_steps = 0
        return self.current_state, {}

    def step(self, action):
        self.engagement_steps += 1

        # Reward logic:
        # +2.0  attacker stays engaged (continues sending commands)
        # +3.0  attacker attempts to use fake credential (high value intel)
        # -5.0  attacker disconnects abruptly (likely detected honeypot)
        # -10.0 attacker deploys counter-detection tool

        reward = self._compute_reward(action)
        terminated = self.engagement_steps >= self.max_steps
        self.current_state = np.random.randn(270).astype(np.float32)

        return self.current_state, reward, terminated, False, {}

    def _compute_reward(self, action: int) -> float:
        # In production: replace with real engagement signals from ssh_honeypot.py
        base_reward = np.random.choice(
            [2.0, 3.0, -5.0, -10.0],
            p=[0.55, 0.25, 0.15, 0.05]
        )
        # Bonus: high-value deception actions get slight boost
        if action in [1, 3, 6]:
            base_reward += 0.5
        return float(base_reward)


def train_policy(total_timesteps: int = 100_000):
    env = make_vec_env(DeceptionEnv, n_envs=4)
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        tensorboard_log="mlops/rl_tensorboard/"
    )
    model.learn(total_timesteps=total_timesteps)
    model.save(MODEL_PATH)
    print(f"[RL] Policy trained and saved to {MODEL_PATH}")
    return model


def load_policy():
    if os.path.exists(MODEL_PATH):
        return PPO.load(MODEL_PATH)
    raise FileNotFoundError("No RL policy found. Run train_policy() first.")


def get_deception_action(session_embedding: np.ndarray, mitre_vector: np.ndarray) -> dict:
    """
    Given current session state, return the best deception action.
    """
    model = load_policy()
    state = np.concatenate([session_embedding, mitre_vector]).astype(np.float32)
    action, _ = model.predict(state, deterministic=True)

    return {
        "action_id": int(action),
        "action_name": DECEPTION_ACTIONS[int(action)],
        "reasoning": f"RL policy selected based on current behavioral state"
    }