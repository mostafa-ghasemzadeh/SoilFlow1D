import numpy as np
from scipy.linalg import solve_banded
from core.hydraulic_models import MODELS
from core.root_uptake import compute_sink


class Richards1D:
    """
    Solves the 1D Richards equation using Galerkin FEM
    with implicit (backward Euler) time stepping and
    Picard iteration for nonlinearity.

    Governing equation:
        C(h) * dh/dt = d/dz[K(h)(dh/dz + 1)] - S(h,z)

    z is positive downward, units: cm and days.
    """

    def __init__(self, layers, dz=0.1 , hydraulic_model="van_genuchten", 
                 nz=100, dt=0.01, dt_max=1.0, dt_min=0.0001, 
                 max_iter=20, tol=1e-4):
        self.layers = layers
        self.dz = dz
        self.nz = nz
        self.dt = dt
        self.dt_max = dt_max
        self.dt_min = dt_min
        self.max_iter = max_iter
        self.tol = tol
        self.hydraulic_model = hydraulic_model
        self._build_grid()

        # Instantiate one model per layer
        model_class = MODELS[hydraulic_model]
        self.layer_models = []
        for layer in layers:
            params = {k: layer[k] for k in ['theta_r', 'theta_s', 'Ks', 'l'] if k in layer}
            if hydraulic_model == "van_genuchten":
                params.update({k: layer[k] for k in ['alpha', 'n'] if k in layer})
            elif hydraulic_model == "brooks_corey":
                params.update({k: layer[k] for k in ['h_b', 'lam'] if k in layer})
            self.layer_models.append(model_class(**params))


    # ------------------------------------------------------------------
    # Grid
    # ------------------------------------------------------------------
    def _build_grid(self):
        total_thickness = sum(l["thickness"] for l in self.layers)
        self.z  = np.linspace(0, total_thickness, self.nz)
        # Map each node to its layer
        self.layer_idx = np.zeros(self.nz, dtype=int)
        thickness = 0.0
        li    = 0
        for i, node_z in enumerate(self.z):
            while (li < len(self.layers) - 1 and
                   node_z > thickness + self.layers[li]["thickness"] - 1e-10):
                thickness += self.layers[li]["thickness"]
                li    += 1
            self.layer_idx[i] = li

    # ------------------------------------------------------------------
    # Hydraulic properties at node i
    # ------------------------------------------------------------------


    def _hydraulics(self, h):
        theta = np.zeros(self.nz)
        K = np.zeros(self.nz)
        C = np.zeros(self.nz)
        for i in range(self.nz):
            model = self.layer_models[self.layer_idx[i]]
            theta[i] = model.theta(h[i])
            K[i] = model.K(h[i])
            C[i] = max(model.C(h[i]),1e-10)
        return theta, K, C


    def _internode_K(self, K):
        """Arithmetic mean conductivity at element interfaces."""
        return 0.5 * (K[:-1] + K[1:])

    # ------------------------------------------------------------------
    # Assemble tridiagonal system (banded format for solve_banded)
    # ------------------------------------------------------------------
    def _assemble(self, h, h_old, theta_old, dt, S):
        n      = self.nz
        dz     = self.dz
        theta, K, C = self._hydraulics(h)
        Kh     = self._internode_K(K)

        ab  = np.zeros((3, n))
        rhs = np.zeros(n)

        # ── Boundary rows: placeholder identity (overwritten by _apply_bc) ──
        ab[1, 0]     = 1.0
        ab[1, n - 1] = 1.0

        # ── Interior nodes ───────────────────────────────────────────────────
        for i in range(1, n - 1):
            Kp = Kh[i]
            Km = Kh[i - 1]

            a_upper =  Kp / dz**2
            a_lower =  Km / dz**2
            a_main  = -(Kp + Km) / dz**2 - C[i] / dt

            if abs(a_main) < 1e-20:
                a_main = -1e-10 / dt

            gravity = (Kp - Km) / dz

            rhs[i] = (-C[i] / dt * h_old[i]
                      - (theta[i] - theta_old[i]) / dt
                      + C[i] / dt * h[i]
                      + gravity
                      - S[i])

            ab[0, i + 1] = a_upper
            ab[1, i]     = a_main
            ab[2, i - 1] = a_lower

        return ab, rhs, theta, C


    # ------------------------------------------------------------------
    # Boundary conditions
    # ------------------------------------------------------------------
    def _apply_bc(self, ab, rhs, h, bc_top, bc_bot, K, Kh):
        n  = self.nz
        dz = self.dz

        # ---- Top BC (i=0) ----
        # ab[1,0] = main diag of row 0
        # ab[0,1] = upper diag of row 0  (does NOT belong to interior node 1)
        if bc_top["type"] == "head":
            ab[1, 0] = 1.0
            ab[0, 1] = 0.0          # safe: row 0's upper slot
            rhs[0]   = bc_top["value"]

        elif bc_top["type"] in ("flux", "atmospheric"):
            if bc_top["type"] == "atmospheric" and h[0] >= 0:
                # Ponding → Dirichlet h=0
                ab[1, 0] = 1.0
                ab[0, 1] = 0.0
                rhs[0]   = 0.0
            else:
                q = bc_top["value"]
                ab[1, 0] = 1.0
                ab[0, 1] = -1.0
                rhs[0]   = dz * (-q / (Kh[0] + 1e-30) - 1.0)

        # ---- Bottom BC (i=n-1) ----
        # ab[1, n-1] = main diag of row n-1
        # ab[2, n-2] = lower diag of row n-1
        #   ⚠️  This slot was written by _assemble for interior node n-2!
        #   We must NOT overwrite it. Instead, encode the BC differently.

        if bc_bot["type"] == "head":
            ab[1, n-1] = 1.0
            ab[2, n-2] = 0.0        # zero out the coupling to node n-2
            rhs[n-1]   = bc_bot["value"]

        elif bc_bot["type"] == "free_drainage":
            # Unit gradient: h[n-1] = h[n-2]  →  h[n-1] - h[n-2] = 0
            ab[1, n-1] =  1.0
            ab[2, n-2] = -1.0       # this IS intentional for this BC
            rhs[n-1]   =  0.0

        elif bc_bot["type"] == "flux":
            q = bc_bot["value"]
            ab[1, n-1] =  1.0
            ab[2, n-2] = -1.0
            rhs[n-1]   = dz * (-q / (K[n-1] + 1e-30) - 1.0)

        elif bc_bot["type"] == "seepage":
            if h[n-1] >= 0:
                ab[1, n-1] = 1.0
                ab[2, n-2] = 0.0
                rhs[n-1]   = 0.0
            else:
                ab[1, n-1] =  1.0
                ab[2, n-2] = -1.0
                rhs[n-1]   =  0.0

        return ab, rhs


    # ------------------------------------------------------------------
    # Single time step (Picard iteration)
    # ------------------------------------------------------------------
    def _step(self, h, theta, dt, bc_top, bc_bot,
              Tp, root_thickness, root_dist, stress_model,
              stress_params):
        h_old     = h.copy()
        theta_old = theta.copy()
        h_iter    = h.copy()

        for _ in range(self.max_iter):
            # Sink term
            _sink_params = {
                "potential_transpiration": Tp,
                "root_depth":              root_thickness,
                "root_distribution":       root_dist,
                "stress_model":            stress_model,
                **stress_params,           # unpacks h1,h2,h3,h4 or vg params
            }
            S = compute_sink(h_iter, self.z, _sink_params)

            ab, rhs, theta_new, C = self._assemble(
                h_iter, h_old, theta_old, dt, S)

            _, K, _ = self._hydraulics(h_iter)
            Kh      = self._internode_K(K)
            ab, rhs = self._apply_bc(ab, rhs, h_iter, bc_top, bc_bot, K, Kh)

            # Solve banded system
            h_new = solve_banded((1, 1), ab, rhs)

            # Convergence check
            err = np.max(np.abs(h_new - h_iter))
            h_iter = h_new.copy()
            if err < self.tol:
                break

        _, K_new, _ = self._hydraulics(h_new)
        return h_new, theta_new, K_new

    # ------------------------------------------------------------------
    # Full simulation
    # ------------------------------------------------------------------
    def run(self, h_init, t_end, bc_top_series, bc_bot,
            Tp_series, rainfall_series,
            root_thickness=30.0, root_dist="exponential",
            stress_model="Feddes", stress_params=None,
            output_times=None, progress_callback=None):
        """
        Parameters
        ----------
        h_init          : array (nz,)  initial pressure head [cm]
        t_end           : float        simulation end time [days]
        bc_top_series   : list of (time, bc_dict) sorted by time
        bc_bot          : dict         bottom BC (constant)
        Tp_series       : list of (time, Tp_value)
        rainfall_series : list of (time, rainfall_value)
        output_times    : list of times to save full profile
        progress_callback: callable(percent) for GUI progress bar

        Returns
        -------
        dict with keys: times, h, theta, K, water_balance
        """
        if stress_params is None:
            stress_params = {}
        if output_times is None:
            output_times = np.linspace(0, t_end, 50)

        h     = h_init.copy()
        theta, K, _ = self._hydraulics(h)

        t          = 0.0
        dt         = self.dt
        out_idx    = 0
        results    = {
            "times":         [],
            "h":             [],
            "theta":         [],
            "K":             [],
            "flux_top":      [],
            "flux_bot":      [],
            "water_balance": [],
        }

        total_inflow  = 0.0
        total_outflow = 0.0

        def _interp_series(series, t):
            """Linear interpolation from a (time, value) list."""
            times  = [s[0] for s in series]
            values = [s[1] for s in series]
            return float(np.interp(t, times, values))

        def _get_bc_top(t):
            rain = _interp_series(rainfall_series, t)
            Ep   = _interp_series(Tp_series, t)
            return {"type": "atmospheric", "value": rain - Ep}

        while t < t_end:
            dt = min(dt, t_end - t)

            bc_top = _get_bc_top(t)
            Tp     = _interp_series(Tp_series, t)

            h_new, theta_new, K_new = self._step(
                h, theta, dt, bc_top, bc_bot,
                Tp, root_thickness, root_dist,
                stress_model, stress_params)

            # Water balance
            _, K_cur, _ = self._hydraulics(h)
            flux_top = -K_new[0]  * ((h_new[1]  - h_new[0])  / self.dz + 1)
            flux_bot = -K_new[-1] * ((h_new[-1] - h_new[-2]) / self.dz + 1)
            total_inflow  += max(0,  flux_top) * dt
            total_outflow += max(0, -flux_bot) * dt

            h, theta, K = h_new, theta_new, K_new
            t += dt

            # Save output at requested times
            if out_idx < len(output_times) and t >= output_times[out_idx]:
                results["times"].append(t)
                results["h"].append(h.copy())
                results["theta"].append(theta.copy())
                results["K"].append(K.copy())
                results["flux_top"].append(flux_top)
                results["flux_bot"].append(flux_bot)
                wb = np.trapezoid(theta, self.z)
                results["water_balance"].append({
                    "time":          t,
                    "storage":       wb,
                    "total_inflow":  total_inflow,
                    "total_outflow": total_outflow,
                })
                out_idx += 1

            # Adaptive time stepping
            dt = min(dt * 1.3, self.dt_max)
            dt = max(dt, self.dt_min)

            if progress_callback:
                progress_callback(int(100 * t / t_end))

        return results
