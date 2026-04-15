import numpy as np
from scipy.linalg import solve_banded


class Solute1D:
    """
    Solves the 1D Advection-Dispersion Equation (ADE) for solute transport
    in variably saturated soil.

    Governing equation:
        d(theta*c)/dt = d/dz[theta*D*dc/dz] - d(q*c)/dz
                        - mu*theta*c          (degradation)
                        - rho*dS/dt           (sorption)

    Supports:
        - Multiple solutes simultaneously
        - Degradation: first-order decay
        - Sorption: Linear / Freundlich / Langmuir
        - Volatilization (Henry's law)
        - Upstream weighting for advection stability
    """

    SORPTION_MODELS = ("none", "linear", "freundlich", "langmuir")

    def __init__(self, nz, dz, dt_max=1.0,
                 dispersivity=10.0,
                 diffusion_coeff=1e-4,
                 upstream_weight=0.5):
        """
        Parameters
        ----------
        nz              : int    number of nodes
        dz              : float  node spacing [cm]
        dt_max          : float  max time step [days]
        dispersivity    : float  mechanical dispersivity [cm]
        diffusion_coeff : float  molecular diffusion [cm²/day]
        upstream_weight : float  0=central diff, 1=full upstream
        """
        self.nz             = nz
        self.dz             = dz
        self.dt_max         = dt_max
        self.dispersivity   = dispersivity
        self.diffusion_coeff= diffusion_coeff
        self.upstream_weight= upstream_weight

    # ------------------------------------------------------------------
    # Dispersion coefficient
    # ------------------------------------------------------------------
    def _dispersion(self, q, theta):
        """
        Hydrodynamic dispersion:
            D = alpha_L * |v| + D_e
            D_e = D0 * theta^(7/3) / theta_s^2  (Millington-Quirk)
        v = q / theta (pore water velocity)
        """
        v  = np.abs(q) / (theta + 1e-30)
        De = self.diffusion_coeff * theta**(7/3) / (np.max(theta)**2 + 1e-30)
        return self.dispersivity * v + De

    # ------------------------------------------------------------------
    # Sorption isotherm: returns sorbed concentration S [mg/g]
    # ------------------------------------------------------------------
    def _sorption(self, c, model, params):
        c = np.maximum(c, 0.0)
        if model == "none":
            return np.zeros_like(c), np.zeros_like(c)

        elif model == "linear":
            # S = Kd * c
            Kd = params.get("Kd", 0.0)
            S  = Kd * c
            dS = Kd * np.ones_like(c)

        elif model == "freundlich":
            # S = Kf * c^N
            Kf = params.get("Kf", 1.0)
            N  = params.get("N",  1.0)
            S  = Kf * c**N
            dS = Kf * N * c**(N - 1)

        elif model == "langmuir":
            # S = (Smax * Kl * c) / (1 + Kl * c)
            Smax = params.get("Smax", 1.0)
            Kl   = params.get("Kl",   0.1)
            S    = (Smax * Kl * c) / (1 + Kl * c)
            dS   = (Smax * Kl)    / (1 + Kl * c)**2

        else:
            raise ValueError(f"Unknown sorption model: {model}")

        return S, dS

    # ------------------------------------------------------------------
    # Assemble tridiagonal system for one solute
    # ------------------------------------------------------------------
    def _assemble(self, c, c_old, theta, theta_old,
                  q, dt, mu, rho_b,
                  sorption_model, sorption_params,
                  henry_kh):
        """
        Returns banded matrix ab (3 x nz) and rhs vector.
        Uses Crank-Nicolson weighting (0.5 implicit).
        """
        n   = self.nz
        dz  = self.dz
        D   = self._dispersion(q, theta)
        Dh  = 0.5 * (D[:-1] + D[1:])   # interface dispersion, length n-1

        # Sorption retardation
        _, dS = self._sorption(c, sorption_model, sorption_params)
        R      = 1.0 + rho_b * dS / (theta + 1e-30)   # retardation factor

        # Volatilization sink: Sv = kh * c  (Henry's law, dimensionless)
        kh = henry_kh

        ab  = np.zeros((3, n))
        rhs = np.zeros(n)

        w  = self.upstream_weight   # upstream weighting factor
        CN = 0.5                    # Crank-Nicolson

        for i in range(1, n - 1):
            Dp = Dh[i]       # D at i+1/2
            Dm = Dh[i - 1]   # D at i-1/2
            qp = 0.5 * (q[i] + q[i + 1])   # flux at i+1/2
            qm = 0.5 * (q[i] + q[i - 1])   # flux at i-1/2

            # Dispersion terms (central difference)
            disp_upper =  CN * Dp / dz**2
            disp_lower =  CN * Dm / dz**2
            disp_main  = -CN * (Dp + Dm) / dz**2

            # Advection terms (upstream weighted)
            # Positive q = downward flow
            adv_upper = -CN * (max(qp, 0) * (1 - w) + min(qp, 0) * w) / dz
            adv_lower =  CN * (max(qm, 0) * w + min(qm, 0) * (1 - w)) / dz
            adv_main  =  CN * (max(qp, 0) * w + min(qp, 0) * (1 - w)
                              - max(qm, 0) * (1 - w) - min(qm, 0) * w) / dz

            # Storage + retardation
            stor = theta[i] * R[i] / dt

            # Degradation + volatilization
            decay = mu * theta[i] + kh * theta[i]

            a_upper = disp_upper + adv_upper
            a_lower = disp_lower + adv_lower
            a_main  = disp_main  + adv_main - stor - decay

            # RHS: explicit part + storage
            rhs[i] = (
                -stor * c_old[i]
                - (1 - CN) * (
                    Dp * (c_old[i+1] - c_old[i]) / dz**2
                  - Dm * (c_old[i]   - c_old[i-1]) / dz**2
                  - (qp * c_old[i+1] - qm * c_old[i-1]) / (2 * dz)
                )
                - mu * theta_old[i] * c_old[i]
                - kh  * theta_old[i] * c_old[i]
            )

            ab[0, i + 1] = a_upper
            ab[1, i]     = a_main
            ab[2, i - 1] = a_lower

        return ab, rhs

    # ------------------------------------------------------------------
    # Apply boundary conditions for solute
    # ------------------------------------------------------------------
    def _apply_bc(self, ab, rhs, c, bc_top, bc_bot, q, theta, D):
        n  = self.nz
        dz = self.dz

        # ---- Top BC ----
        if bc_top["type"] == "concentration":
            ab[1, 0] = 1.0
            ab[0, 1] = 0.0
            rhs[0]   = bc_top["value"]

        elif bc_top["type"] == "flux":
            # Third-type (Cauchy) BC: q*c - theta*D*dc/dz = q*c_in
            c_in     = bc_top["value"]
            D0       = D[0]
            ab[1, 0] = q[0] + theta[0] * D0 / dz
            ab[0, 1] = -theta[0] * D0 / dz
            rhs[0]   = q[0] * c_in

        elif bc_top["type"] == "zero_gradient":
            ab[1, 0] =  1.0
            ab[0, 1] = -1.0
            rhs[0]   =  0.0

        # ---- Bottom BC ----
        if bc_bot["type"] == "concentration":
            ab[1, n-1] = 1.0
            ab[2, n-2] = 0.0
            rhs[n-1]   = bc_bot["value"]

        elif bc_bot["type"] == "zero_gradient":
            ab[1, n-1] =  1.0
            ab[2, n-2] = -1.0
            rhs[n-1]   =  0.0

        elif bc_bot["type"] == "free_exit":
            # Advective flux only at exit
            ab[1, n-1] =  1.0
            ab[2, n-2] = -1.0
            rhs[n-1]   =  0.0

        return ab, rhs

    # ------------------------------------------------------------------
    # Step one solute forward in time
    # ------------------------------------------------------------------
    def step(self, c, c_old, theta, theta_old, q, dt,
             solute_props, bc_top, bc_bot):
        """
        Parameters
        ----------
        c, c_old      : array (nz,)  current and previous concentration [mg/cm³]
        theta, theta_old: array (nz,) water content
        q             : array (nz,)  Darcy flux [cm/day]
        dt            : float        time step [days]
        solute_props  : dict with keys:
                          mu             - first-order decay [1/day]
                          rho_b          - bulk density [g/cm³]
                          sorption_model - 'none','linear','freundlich','langmuir'
                          sorption_params- dict of isotherm params
                          henry_kh       - Henry volatilization coeff [1/day]
        bc_top, bc_bot: dicts with 'type' and 'value'

        Returns
        -------
        c_new : array (nz,)
        """
        mu             = solute_props.get("mu", 0.0)
        rho_b          = solute_props.get("rho_b", 1.5)
        sorption_model = solute_props.get("sorption_model", "none")
        sorption_params= solute_props.get("sorption_params", {})
        henry_kh       = solute_props.get("henry_kh", 0.0)

        D   = self._dispersion(q, theta)
        ab, rhs = self._assemble(
            c, c_old, theta, theta_old, q, dt,
            mu, rho_b, sorption_model, sorption_params, henry_kh)

        ab, rhs = self._apply_bc(ab, rhs, c, bc_top, bc_bot, q, theta, D)

        c_new = solve_banded((1, 1), ab, rhs)
        return np.maximum(c_new, 0.0)   # no negative concentrations

    # ------------------------------------------------------------------
    # Run full simulation for all solutes
    # ------------------------------------------------------------------
    def run(self, solutes, theta_series, q_series, times,
            progress_callback=None):
        """
        Parameters
        ----------
        solutes : list of dicts, each with:
                    name           - str
                    c_init         - array (nz,) initial concentration
                    props          - solute_props dict (see step())
                    bc_top         - BC dict
                    bc_bot         - BC dict
        theta_series : list of (time, theta_array) from Richards solver
        q_series     : list of (time, q_array)     Darcy flux arrays
        times        : array of output times

        Returns
        -------
        dict: {solute_name: {"times": [...], "c": [arrays]}}
        """
        results = {s["name"]: {"times": [], "c": []} for s in solutes}

        # Initialize
        c_current = {s["name"]: s["c_init"].copy() for s in solutes}
        c_old     = {s["name"]: s["c_init"].copy() for s in solutes}

        theta_times = [x[0] for x in theta_series]
        q_times     = [x[0] for x in q_series]

        for step_idx in range(len(times) - 1):
            t    = times[step_idx]
            t_next = times[step_idx + 1]
            dt   = t_next - t

            # Interpolate theta and q at current time
            theta = self._interp_field(theta_series, theta_times, t)
            theta_old = self._interp_field(theta_series, theta_times, t)
            q     = self._interp_field(q_series, q_times, t)

            for s in solutes:
                name = s["name"]
                c_new = self.step(
                    c_current[name], c_old[name],
                    theta, theta_old, q, dt,
                    s["props"], s["bc_top"], s["bc_bot"])

                c_old[name]     = c_current[name].copy()
                c_current[name] = c_new

                results[name]["times"].append(t_next)
                results[name]["c"].append(c_new.copy())

            if progress_callback:
                progress_callback(int(100 * step_idx / (len(times) - 1)))

        return results

    # ------------------------------------------------------------------
    # Helper: interpolate field array at time t
    # ------------------------------------------------------------------
    @staticmethod
    def _interp_field(series, times, t):
        if t <= times[0]:
            return series[0][1].copy()
        if t >= times[-1]:
            return series[-1][1].copy()
        for i in range(len(times) - 1):
            if times[i] <= t <= times[i + 1]:
                alpha = (t - times[i]) / (times[i + 1] - times[i])
                return (1 - alpha) * series[i][1] + alpha * series[i + 1][1]
        return series[-1][1].copy()
