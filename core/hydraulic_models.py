import numpy as np


class HydraulicModel:
    """Abstract base for soil hydraulic property models."""

    def theta(self, h): raise NotImplementedError
    def K(self, h):     raise NotImplementedError
    def C(self, h):     raise NotImplementedError
    def Se(self, h):    raise NotImplementedError


class VanGenuchten(HydraulicModel):
    """
    van Genuchten (1980) retention + Mualem (1976) conductivity.

    θ(h) = θ_r + (θ_s - θ_r) / [1 + |αh|^n]^m    h < 0
    K(h) = Ks · Se^l · [1 - (1 - Se^(1/m))^m]²
    C(h) = dθ/dh
    """

    def __init__(self, theta_r=0.078, theta_s=0.43,
                 alpha=0.036, n=1.56, Ks=24.96, l=0.5):
        self.theta_r = theta_r
        self.theta_s = theta_s
        self.alpha   = alpha
        self.n       = n
        self.m       = 1.0 - 1.0 / n
        self.Ks      = Ks
        self.l       = l

    def Se(self, h):
        h = np.asarray(h, dtype=float)
        Se = np.where(
            h < 0.0,
            1.0 / (1.0 + (self.alpha * np.abs(h)) ** self.n) ** self.m,
            1.0
        )
        return np.clip(Se, 0.0, 1.0)

    def theta(self, h):
        return self.theta_r + (self.theta_s - self.theta_r) * self.Se(h)

    def K(self, h):
        Se = np.clip(self.Se(h), 1e-10, 1.0)
        inner = (1.0 - Se ** (1.0 / self.m)) ** self.m
        return self.Ks * Se ** self.l * (1.0 - inner) ** 2

    def C(self, h):
        h = np.asarray(h, dtype=float)
        C = np.zeros_like(h)
        mask = h < 0.0
        ah   = self.alpha * np.abs(h[mask])
        denom = (1.0 + ah ** self.n) ** (self.m + 1.0)
        C[mask] = (
            self.alpha * self.n * self.m
            * (self.theta_s - self.theta_r)
            * ah ** (self.n - 1.0)
            / denom
        )
        return C

    def h_from_theta(self, theta):
        """Analytical inverse of θ(h)."""
        theta = np.asarray(theta, dtype=float)
        theta = np.clip(theta, self.theta_r + 1e-10, self.theta_s - 1e-10)
        Se    = (theta - self.theta_r) / (self.theta_s - self.theta_r)
        Se    = np.clip(Se, 1e-10, 1.0 - 1e-10)
        return -(1.0 / self.alpha) * (Se ** (-1.0 / self.m) - 1.0) ** (1.0 / self.n)


class BrooksCorey(HydraulicModel):
    """
    Brooks & Corey (1964) hydraulic model.

    θ(h) = θ_r + (θ_s - θ_r) · (h_b / h)^λ    h < h_b
    K(h) = Ks · Se^(2/λ + l + 2)
    """

    def __init__(self, theta_r=0.05, theta_s=0.40,
                 h_b=-20.0, lam=0.5, Ks=10.0, l=2.0):
        self.theta_r = theta_r
        self.theta_s = theta_s
        self.h_b     = h_b
        self.lam     = lam
        self.Ks      = Ks
        self.l       = l

    def Se(self, h):
        h = np.asarray(h, dtype=float)
        Se = np.where(
            h < self.h_b,
            (self.h_b / np.where(h < self.h_b, h, self.h_b)) ** self.lam,
            1.0
        )
        return np.clip(Se, 0.0, 1.0)

    def theta(self, h):
        return self.theta_r + (self.theta_s - self.theta_r) * self.Se(h)

    def K(self, h):
        Se = np.clip(self.Se(h), 1e-10, 1.0)
        return self.Ks * Se ** (2.0 / self.lam + self.l + 2.0)

    def C(self, h):
        h = np.asarray(h, dtype=float)
        C = np.zeros_like(h)
        mask = h < self.h_b
        C[mask] = (
            -self.lam
            * (self.theta_s - self.theta_r)
            * self.h_b ** self.lam
            / np.abs(h[mask]) ** (self.lam + 1.0)
        )
        return C


class DualPorosity(HydraulicModel):
    """
    Dual-porosity model (Gerke & van Genuchten, 1993).

    θ_total = w_f · θ_f(h) + (1 - w_f) · θ_m(h)
    K_total = w_f · K_f(h)   (only mobile domain conducts)
    Γ_w     = α_w · (θ_f - θ_m)
    """

    def __init__(self, mobile, immobile, w_f=0.05, alpha_w=0.1):
        self.mobile   = mobile
        self.immobile = immobile
        self.w_f      = w_f
        self.alpha_w  = alpha_w

    def Se(self, h):
        return (self.w_f * self.mobile.Se(h)
                + (1.0 - self.w_f) * self.immobile.Se(h))

    def theta(self, h):
        return (self.w_f * self.mobile.theta(h)
                + (1.0 - self.w_f) * self.immobile.theta(h))

    def K(self, h):
        return self.w_f * self.mobile.K(h)

    def C(self, h):
        return (self.w_f * self.mobile.C(h)
                + (1.0 - self.w_f) * self.immobile.C(h))

    def mass_transfer(self, theta_f, theta_m):
        """First-order mass transfer [1/day]."""
        return self.alpha_w * (theta_f - theta_m)


def build_hydraulic_model(model_type, params):
    """
    Factory: instantiate a hydraulic model from a dict.

    Parameters
    ----------
    model_type : str   'van_genuchten' | 'brooks_corey'
    params     : dict  keyword arguments passed to the constructor

    Returns
    -------
    HydraulicModel instance
    """
    registry = {
        "van_genuchten": VanGenuchten,
        "brooks_corey":  BrooksCorey,
    }
    if model_type not in registry:
        raise ValueError(
            f"Unknown model '{model_type}'. "
            f"Choose from: {list(registry.keys())}"
        )
    return registry[model_type](**params)

MODELS = {
    "van_genuchten": VanGenuchten,
    "brooks_corey": BrooksCorey,
    "dual_porosity": DualPorosity
}


