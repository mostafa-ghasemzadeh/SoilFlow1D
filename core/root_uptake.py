import numpy as np


class RootWaterUptake:
    """
    Root water uptake models for 1D soil-water simulations.

    Supported models:
        - Feddes et al. (1978) stress function
        - van Genuchten (1987) osmotic + matric stress
        - Jarvis (1989) macropore-aware uptake

    Reference thickness convention: z = 0 at surface, positive downward [cm].
    """

    # ------------------------------------------------------------------
    # Root distribution
    # ------------------------------------------------------------------
    @staticmethod
    def root_distribution(z, z_root, model="linear"):
        """
        Normalised root length density  b(z)  [-/cm],  ∫b dz = 1.

        Parameters
        ----------
        z      : ndarray  node thicknesss [cm]
        z_root : float    maximum rooting thickness [cm]
        model  : str      'linear' | 'exponential' | 'uniform'

        Returns
        -------
        b : ndarray  normalised root density [1/cm]
        """
        b = np.zeros_like(z, dtype=float)
        mask = z <= z_root

        if model == "uniform":
            b[mask] = 1.0 / z_root

        elif model == "linear":
            # Triangular: maximum at surface, zero at z_root
            b[mask] = 2.0 * (z_root - z[mask]) / z_root**2

        elif model == "exponential":
            # Exponential decay with scale = z_root / 3
            scale = z_root / 3.0
            raw   = np.exp(-z / scale)
            raw[~mask] = 0.0
            integral = np.trapezoid(raw, z) if np.any(mask) else 1.0
            b = raw / (integral + 1e-30)

        else:
            raise ValueError(f"Unknown root distribution model: {model!r}")

        return b

    # ------------------------------------------------------------------
    # Feddes stress function
    # ------------------------------------------------------------------
    @staticmethod
    def feddes_stress(h, h1, h2, h3, h4):
        """
        Feddes et al. (1978) water stress reduction factor α(h) ∈ [0, 1].

        Piecewise linear:
            h  > h1  (anaerobic)  → α = 0
            h1 ≥ h > h2           → α increases linearly 0 → 1
            h2 ≥ h > h3           → α = 1  (optimal)
            h3 ≥ h > h4           → α decreases linearly 1 → 0
            h  ≤ h4  (wilting)    → α = 0

        Parameters
        ----------
        h  : ndarray  pressure head [cm]  (negative = unsaturated)
        h1 : float    anaerobic point [cm]
        h2 : float    upper optimal [cm]
        h3 : float    lower optimal [cm]
        h4 : float    wilting point [cm]

        Returns
        -------
        alpha : ndarray  stress factor [-]
        """
        h = np.asarray(h, dtype=float)
        alpha = np.zeros_like(h)

        # Optimal zone
        alpha = np.where((h <= h2) & (h > h3), 1.0, alpha)

        # Anaerobic stress (h > h1 → 0, h1 > h > h2 → ramp up)
        alpha = np.where(
            (h <= h1) & (h > h2),
            (h1 - h) / (h1 - h2),
            alpha
        )

        # Drought stress (h3 > h > h4 → ramp down)
        alpha = np.where(
            (h <= h3) & (h > h4),
            (h - h4) / (h3 - h4),
            alpha
        )

        return np.clip(alpha, 0.0, 1.0)

    # ------------------------------------------------------------------
    # Potential transpiration distribution
    # ------------------------------------------------------------------
    def potential_uptake(self, Tp, z, z_root, dz,
                         root_model="linear"):
        """
        Distribute potential transpiration Tp over the root zone.

        Parameters
        ----------
        Tp         : float    potential transpiration [cm/day]
        z          : ndarray  node thicknesss [cm]
        z_root     : float    rooting thickness [cm]
        dz         : float    node spacing [cm]
        root_model : str      root distribution model

        Returns
        -------
        S_pot : ndarray  potential uptake rate [1/day]
        """
        b     = self.root_distribution(z, z_root, model=root_model)
        S_pot = Tp * b   # [cm/day * 1/cm] = [1/day]
        return S_pot

    # ------------------------------------------------------------------
    # Actual uptake with Feddes stress
    # ------------------------------------------------------------------
    def actual_uptake_feddes(self, Tp, h, z, z_root, dz,
                             h1=-10.0, h2=-25.0,
                             h3=-200.0, h4=-8000.0,
                             root_model="linear",
                             compensate=False):
        """
        Actual root water uptake using the Feddes stress function.

        Parameters
        ----------
        Tp          : float    potential transpiration [cm/day]
        h           : ndarray  pressure head [cm]
        z           : ndarray  node thicknesss [cm]
        z_root      : float    rooting thickness [cm]
        dz          : float    node spacing [cm]
        h1–h4       : float    Feddes parameters [cm]
        root_model  : str      root distribution model
        compensate  : bool     redistribute uptake from stressed nodes

        Returns
        -------
        S_act : ndarray  actual uptake rate [1/day]
        """
        S_pot  = self.potential_uptake(Tp, z, z_root, dz, root_model)
        alpha  = self.feddes_stress(h, h1, h2, h3, h4)
        S_act  = alpha * S_pot

        if compensate:
            # Redistribute deficit to unstressed nodes
            deficit   = np.sum((S_pot - S_act) * dz)
            unstressed = alpha >= 1.0
            if unstressed.any():
                extra = deficit / (np.sum(S_pot[unstressed]) * dz + 1e-30)
                S_act[unstressed] = np.minimum(
                    S_pot[unstressed] * (1.0 + extra),
                    S_pot[unstressed] * 2.0   # cap at 2× potential
                )

        return S_act

    # ------------------------------------------------------------------
    # van Genuchten osmotic + matric stress
    # ------------------------------------------------------------------
    @staticmethod
    def vg_stress(h, EC, h50=-200.0, p=3.0, EC50=4.0, q_osm=3.0):
        """
        Combined matric and osmotic stress after van Genuchten (1987).

        α(h, EC) = α_matric(h) × α_osmotic(EC)

        Parameters
        ----------
        h    : ndarray  pressure head [cm]
        EC   : ndarray  electrical conductivity [dS/m]
        h50  : float    h at which α_matric = 0.5 [cm]
        p    : float    shape parameter for matric stress
        EC50 : float    EC at which α_osmotic = 0.5 [dS/m]
        q_osm: float    shape parameter for osmotic stress

        Returns
        -------
        alpha : ndarray  combined stress factor [-]
        """
        h  = np.asarray(h,  dtype=float)
        EC = np.asarray(EC, dtype=float)

        alpha_m = 1.0 / (1.0 + (h / h50)**p)
        alpha_o = 1.0 / (1.0 + (EC / EC50)**q_osm)

        return np.clip(alpha_m * alpha_o, 0.0, 1.0)

    def actual_uptake_vg(self, Tp, h, EC, z, z_root, dz,
                         h50=-200.0, p=3.0,
                         EC50=4.0, q_osm=3.0,
                         root_model="linear"):
        """
        Actual uptake using van Genuchten combined stress.

        Parameters
        ----------
        Tp         : float    potential transpiration [cm/day]
        h          : ndarray  pressure head [cm]
        EC         : ndarray  electrical conductivity [dS/m]
        z          : ndarray  node thicknesss [cm]
        z_root     : float    rooting thickness [cm]
        dz         : float    node spacing [cm]
        h50, p     : float    matric stress parameters
        EC50, q_osm: float    osmotic stress parameters
        root_model : str      root distribution model

        Returns
        -------
        S_act : ndarray  actual uptake rate [1/day]
        """
        S_pot = self.potential_uptake(Tp, z, z_root, dz, root_model)
        alpha = self.vg_stress(h, EC, h50, p, EC50, q_osm)
        return alpha * S_pot

    # ------------------------------------------------------------------
    # Integrated transpiration (diagnostic)
    # ------------------------------------------------------------------
    @staticmethod
    def integrated_transpiration(S, dz):
        """
        Integrate uptake over thickness to get total transpiration [cm/day].

        Parameters
        ----------
        S  : ndarray  uptake rate [1/day]
        dz : float    node spacing [cm]

        Returns
        -------
        T_act : float  [cm/day]
        """
        return float(np.sum(S) * dz)


def compute_sink(h, z, params):
    """Compute root water uptake using Feddes model."""
    h1 = params.get("h1", -10)      # Anaerobiosis point
    h2 = params.get("h2", -25)      # Optimal uptake start
    h3 = params.get("h3", -200)     # Optimal uptake end
    h4 = params.get("h4", -8000)    # Wilting point
    
    Tp = params.get("potential_transpiration", 0.5)  # cm/day
    root_thickness = params.get("root_thickness", 50)  # cm
    
    # Root distribution (exponential decay)
    b = 0.05  # root distribution parameter
    root_dist = np.exp(-b * z)
    root_dist = root_dist / np.trapezoid(root_dist, z)
    
    # Water stress function
    alpha = np.ones_like(h)
    alpha[h > h1] = 0  # Too wet
    alpha[(h <= h1) & (h > h2)] = (h1 - h[(h <= h1) & (h > h2)]) / (h1 - h2)
    alpha[(h <= h3) & (h > h4)] = (h[(h <= h3) & (h > h4)] - h4) / (h3 - h4)
    alpha[h <= h4] = 0  # Too dry
    
    # Sink term
    sink = Tp * root_dist * alpha
    sink[z > root_thickness] = 0
    
    return sink
