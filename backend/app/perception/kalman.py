"""Three-dimensional constant-velocity Kalman filter."""
from __future__ import annotations

import math

import numpy as np

from .. import config


class Kalman3D:
    def __init__(self, position, covariance=None):
        self.x = np.zeros(6, dtype=float)
        self.x[:3] = position
        self.P = np.eye(6) * config.PERCEPTION_INITIAL_VELOCITY_STD ** 2
        self.P[:3, :3] = np.eye(3) * config.PERCEPTION_MIN_VARIANCE_M2 if covariance is None else np.asarray(covariance, dtype=float)

    def predict(self, dt: float):
        if dt < 0:
            raise ValueError("Prediction dt must be nonnegative")
        transition = np.eye(6)
        transition[:3, 3:] = np.eye(3) * dt
        accel = np.vstack((np.eye(3) * dt ** 2 / 2, np.eye(3) * dt))
        self.x = transition @ self.x
        self.P = transition @ self.P @ transition.T + accel @ accel.T * config.KALMAN_ACCEL_SIGMA ** 2
        return self.x.copy()

    def update(self, z, R):
        R = np.asarray(R, dtype=float)
        residual = np.asarray(z, dtype=float) - self.x[:3]
        innovation = self.P[:3, :3] + R
        gain = np.linalg.solve(innovation, self.P[:3, :]).T
        self.x += gain @ residual
        # Joseph form preserves positive semidefiniteness over long demonstrations.
        remainder = np.eye(6)
        remainder[:, :3] -= gain
        self.P = remainder @ self.P @ remainder.T + gain @ R @ gain.T
        self.P = (self.P + self.P.T) / 2
        return self.x.copy()

    def error_ellipse(self):
        values, vectors = np.linalg.eigh(self.P[:2, :2])
        order = np.argsort(values)[::-1]
        major = vectors[:, order[0]]
        return {"a_m": math.sqrt(max(float(values[order[0]]), 0)), "b_m": math.sqrt(max(float(values[order[1]]), 0)),
                "angle_deg": math.degrees(math.atan2(major[1], major[0])) % 180}


# Keep the spelling discoverable for C's and B's numerical integration code.
Kalman3d = Kalman3D
