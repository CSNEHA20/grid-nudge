"""Linear Thompson Sampling (LinTS) contextual bandit implementation.

Implements Bayesian linear regression with discounting for non-stationary environments,
Cholesky sampling of posterior parameter vectors theta, and batch covariance updates.
"""

from typing import Any, Dict
import numpy as np

from gridnudge.persuasion.features import FEATURE_DIM


class LinTS:
    """Discounted Linear Thompson Sampling contextual bandit."""

    def __init__(
        self,
        d: int = FEATURE_DIM,
        lam: float = 1.0,
        v: float = 0.5,
        gamma: float = 0.999,
        seed: int = 42,
    ):
        """Initialize LinTS model.

        Args:
            d: Feature vector dimension (default 121).
            lam: Ridge regularization parameter (prior precision scalar).
            v: Thompson exploration noise scale.
            gamma: Discount factor for non-stationarity (e.g. 0.999).
            seed: Random seed for posterior parameter draws.
        """
        self.d = d
        self.lam = float(lam)
        self.v = float(v)
        self.gamma = float(gamma)
        self.rng = np.random.default_rng(seed)

        # Sufficient statistics: Precision matrix A and reward vector b
        self.A = self.lam * np.eye(d, dtype=float)
        self.b = np.zeros(d, dtype=float)
        self.update_count = 0
        self.version = 1

    def sample_theta(self, m: int = 64) -> np.ndarray:
        """Sample m parameter vectors from posterior distribution N(mu, v^2 * A^-1).

        Args:
            m: Number of posterior draws (default 64).

        Returns:
            Array of shape (m, d).
        """
        # Invert precision matrix using pinv for numerical stability
        A_inv = np.linalg.pinv(self.A)
        mu = A_inv @ self.b

        # Symmetrize and regularize covariance matrix for Cholesky
        cov = self.v**2 * A_inv
        cov = 0.5 * (cov + cov.T) + 1e-7 * np.eye(self.d)

        try:
            L = np.linalg.cholesky(cov)
        except np.linalg.LinAlgError:
            # SVD fallback if Cholesky fails on ill-conditioned matrix
            u, s, _ = np.linalg.svd(cov)
            L = u @ np.diag(np.sqrt(np.maximum(1e-8, s)))

        standard_normal = self.rng.standard_normal((self.d, m))
        theta_samples = mu[:, np.newaxis] + (L @ standard_normal)
        return theta_samples.T  # Shape (m, d)

    def update(self, Phi: np.ndarray, r: np.ndarray) -> None:
        """Update sufficient statistics with observed feature vectors and rewards.

        Args:
            Phi: Batch matrix of chosen action feature vectors, shape (n, d).
            r: Observed causal reward vector, shape (n,).
        """
        Phi = np.atleast_2d(Phi)
        r = np.atleast_1d(r)
        n = len(r)

        if n == 0 or Phi.shape[1] != self.d:
            return

        eye_d = np.eye(self.d, dtype=float)

        # Apply exponential discounting gamma to past history
        self.A = self.gamma * (self.A - self.lam * eye_d) + self.lam * eye_d + (Phi.T @ Phi)
        self.b = self.gamma * self.b + (Phi.T @ r)

        self.update_count += n
        self.version += 1

    def get_state(self) -> Dict[str, Any]:
        """Serialize model parameters for storage (DynamoDB or InMemoryStore)."""
        return {
            "d": self.d,
            "lam": self.lam,
            "v": self.v,
            "gamma": self.gamma,
            "A": self.A.tolist(),
            "b": self.b.tolist(),
            "update_count": self.update_count,
            "version": self.version,
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """Restore model parameters from stored state."""
        self.d = int(state.get("d", self.d))
        self.lam = float(state.get("lam", self.lam))
        self.v = float(state.get("v", self.v))
        self.gamma = float(state.get("gamma", self.gamma))
        self.A = np.array(state.get("A"), dtype=float)
        self.b = np.array(state.get("b"), dtype=float)
        self.update_count = int(state.get("update_count", 0))
        self.version = int(state.get("version", 1))
