import numpy as np
from scipy.linalg import solve_banded


class HeatTransport1D:
    """
    Solves the 1D heat transport equation with advection and dispersion.

    Governing equation:
        C_eff * dT/dt = d/dz[lambda_eff * dT/dz] - d(q * rho_w * Cp_w * T)/dz

    Where:
        T            = temperature [°C]
        C_eff        = effective volumetric heat capacity [J/(cm³·K)]
        lambda_eff   = effective thermal conductivity [W/(m·K)]
        q            = Darcy flux [cm/day]
        rho_w        = density of water [g/cm³]
        Cp_w         = specific heat of water [J/(g·K)]
    """

    RHO_W  = 1.0     # g/cm³
    CP_W   = 4186.0  # J/(g·K)
    # W/(m·K) → J/(cm·day·K): multiply by 864
    LAMBDA_CONV = 864.0

    def __init__(self, nz, dz, dt_max=1.0,
                 thermal_dispersivity=1.0,
                 rho_s=1.5, Cp_s=800.0,
                 lambda_s=2.0, lambda_w=0.58, lambda_a=0.025):
        """
        Parameters
        ----------
        nz                   : int   number of nodes
        dz                   : float node spacing [cm]
        dt_max               : float max time step [days]
        thermal_dispersivity : float dispersion length [cm]
        rho_s                : float bulk density of solid [g/cm³]
        Cp_s                 : float specific heat of solid [J/(g·K)]
        lambda_s             : float thermal conductivity of solid [W/(m·K)]
        lambda_w             : float thermal conductivity of water [W/(m·K)]
        lambda_a             : float thermal conductivity of air   [W/(m·K)]
        """
        self.nz   = nz
        self.dz   = dz
        self.dt_max = dt_max
        self.thermal_dispersivity = thermal_dispersivity
        self.rho_s    = rho_s
        self.Cp_s     = Cp_s
        self.lambda_s = lambda_s
        self.lambda_w = lambda_w
        self.lambda_a = lambda_a

    # ------------------------------------------------------------------
    # Effective thermal conductivity  [W/(m·K)]
    # Weighted arithmetic mean of phase conductivities
    # ------------------------------------------------------------------
    def _lambda_eff(self, theta):
        """
        Parameters
        ----------
        theta : ndarray  volumetric water content [-]

        Returns
        -------
        lambda_eff : ndarray  [W/(m·K)]
        """
        f_w = np.clip(theta, 0.0, 1.0)
        f_s = np.clip(1.0 - theta, 0.0, 1.0)
        f_a = np.maximum(0.0, 1.0 - f_s - f_w)
        return f_s * self.lambda_s + f_w * self.lambda_w + f_a * self.lambda_a

    # ------------------------------------------------------------------
    # Effective volumetric heat capacity  [J/(cm³·K)]
    # ------------------------------------------------------------------
    def _VHC(self, theta):
        """
        Parameters
        ----------
        theta : ndarray  volumetric water content [-]

        Returns
        -------
        VHCt : ndarray  [J/(cm³·K)]
        """
        VHCw = theta * self.RHO_W * self.CP_W
        VHCs = (1.0 - theta) * self.rho_s * self.Cp_s
        return VHCw + VHCs

    # ------------------------------------------------------------------
    # Assemble banded system  (Crank–Nicolson, θ = 0.5)
    # ------------------------------------------------------------------
    def _assemble(self, T_old, theta, q, dt,
                  bc_top_type, bc_top_val,
                  bc_bot_type, bc_bot_val):
        """
        Build the banded matrix (3 × nz) and RHS for the heat equation.

        Band storage layout for scipy.linalg.solve_banded (l=1, u=1):
            ab[0, i+1] = upper diagonal  a_{i, i+1}
            ab[1, i]   = main  diagonal  a_{i, i}
            ab[2, i-1] = lower diagonal  a_{i, i-1}

        Parameters
        ----------
        T_old        : ndarray  temperature at previous time step [°C]
        theta        : ndarray  volumetric water content [-]
        q            : ndarray  Darcy flux [cm/day]  (positive downward)
        dt           : float    time step [days]
        bc_top_type  : str      'temperature' | 'flux'
        bc_top_val   : float    value for top BC
        bc_bot_type  : str      'temperature' | 'flux' | 'zero_gradient'
        bc_bot_val   : float    value for bottom BC

        Returns
        -------
        ab  : ndarray (3, nz)
        rhs : ndarray (nz,)
        """
        n   = self.nz
        dz  = self.dz
        CN  = 0.5   # Crank–Nicolson weight

        lam   = self._lambda_eff(theta) * self.LAMBDA_CONV   # J/(cm·day·K)
        VHCt  = self._VHC(theta)                              # J/(cm³·K)
        adv   = q * self.RHO_W * self.CP_W                   # J/(cm²·day·K)

        # Interface values (arithmetic mean)
        lam_h = 0.5 * (lam[:-1]  + lam[1:])   # length n-1
        adv_h = 0.5 * (adv[:-1]  + adv[1:])   # length n-1

        ab  = np.zeros((3, n))
        rhs = np.zeros(n)

        # ---- Interior nodes ----
        for i in range(1, n - 1):
            lp = lam_h[i]       # λ_{i+1/2}
            lm = lam_h[i - 1]   # λ_{i-1/2}
            ap = adv_h[i]       # advective coeff at i+1/2
            am = adv_h[i - 1]   # advective coeff at i-1/2

            # Diffusive coefficients
            d_up   =  CN * lp / dz**2
            d_lo   =  CN * lm / dz**2
            d_main = -CN * (lp + lm) / dz**2

            # Advective coefficients (central differencing)
            a_up   = -CN * ap / (2.0 * dz)
            a_lo   =  CN * am / (2.0 * dz)
            a_main =  CN * (ap - am) / (2.0 * dz)

            stor = VHCt[i] / dt

            ab[0, i + 1] = d_up  + a_up
            ab[1, i]     = d_main + a_main - stor
            ab[2, i - 1] = d_lo  + a_lo

            # Explicit part of Crank–Nicolson
            rhs[i] = (
                -stor * T_old[i]
                - (1.0 - CN) * (
                    lp * (T_old[i + 1] - T_old[i]) / dz**2
                  - lm * (T_old[i]     - T_old[i - 1]) / dz**2
                  - ap * (T_old[i + 1] - T_old[i - 1]) / (2.0 * dz)
                )
            )

        # ---- Top boundary (i = 0) ----
        if bc_top_type == "temperature":
            ab[1, 0] = 1.0
            ab[0, 1] = 0.0
            rhs[0]   = bc_top_val
        elif bc_top_type == "flux":
            # -λ * dT/dz|_top = bc_top_val  [J/(cm²·day)]
            lam0 = lam_h[0]
            ab[1, 0] =  lam0 / dz
            ab[0, 1] = -lam0 / dz
            rhs[0]   = bc_top_val
        else:
            raise ValueError(f"Unknown bc_top_type: {bc_top_type!r}")

        # ---- Bottom boundary (i = n-1) ----
        if bc_bot_type == "temperature":
            ab[1, n - 1] = 1.0
            ab[2, n - 2] = 0.0
            rhs[n - 1]   = bc_bot_val
        elif bc_bot_type == "flux":
            lam_b = lam_h[-1]
            ab[1, n - 1] = -lam_b / dz
            ab[2, n - 2] =  lam_b / dz
            rhs[n - 1]   = bc_bot_val
        elif bc_bot_type == "zero_gradient":
            ab[1, n - 1] =  1.0
            ab[2, n - 2] = -1.0
            rhs[n - 1]   = 0.0
        else:
            raise ValueError(f"Unknown bc_bot_type: {bc_bot_type!r}")

        return ab, rhs

    # ------------------------------------------------------------------
    # Public solver
    # ------------------------------------------------------------------
    def solve(self, T, theta, q, dt,
              bc_top_type="temperature", bc_top_val=20.0,
              bc_bot_type="zero_gradient", bc_bot_val=0.0):
        """
        Advance temperature one time step.

        Parameters
        ----------
        T            : ndarray  current temperature [°C]
        theta        : ndarray  volumetric water content [-]
        q            : ndarray  Darcy flux [cm/day]
        dt           : float    time step [days]
        bc_top_type  : str
        bc_top_val   : float
        bc_bot_type  : str
        bc_bot_val   : float

        Returns
        -------
        T_new : ndarray  updated temperature [°C]
        """
        dt = min(dt, self.dt_max)
        ab, rhs = self._assemble(
            T, theta, q, dt,
            bc_top_type, bc_top_val,
            bc_bot_type, bc_bot_val
        )
        T_new = solve_banded((1, 1), ab, rhs)
        return T_new
