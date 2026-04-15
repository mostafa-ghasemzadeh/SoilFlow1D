"""
Core simulation orchestrator integrating Richards, solute, and heat transport.
"""
import numpy as np
from core.richards import Richards1D
from core.solute import Solute1D
from core.heat import HeatTransport1D
from core.root_uptake import compute_sink


def run_simulation(config: dict, progress_cb=None):
    """
    Run coupled vadose zone simulation from GUI configuration.
    
    Args:
        config: Dictionary with keys:
            - simulation: {nodes_per_cm, dt_init, dt_max, t_end, tolerance, ...}
            - soil_profile: {layers, total_thickness, ...}
            - boundaries: {top, bottom}
            - time_series: {...}
            - solute: {enabled, ...}
            - heat: {enabled, ...}
            - root_uptake: {enabled, ...}
        progress_cb: Optional callback(pct: int, msg: str)
    
    Returns:
        dict with keys: times, z, thickness, h, pressure, theta, flux, conc, temp
    """
    
    def progress(pct, msg):
        if progress_cb:
            progress_cb(pct, msg)
    
    progress(0, "Parsing configuration...")
    
    # Extract settings
    sim = config.get("simulation", {})
    t_start = sim.get("t_start", 0.0)
    t_end = sim.get("t_end", 100.0)
    dt = sim.get("dt_init", 0.01)
    dt_max = sim.get("dt_max", 1.0)
    output_interval = sim.get("output_interval", 1.0)
    tolerance = sim.get("tolerance", 1e-3)
    max_iter = sim.get("max_iter", 100)
    
    soil = config.get("soil_profile", {})
    layers = soil.get("layers", [])
    # Ensure all layers have required hydraulic parameters
    for layer in layers:
        if layer.get("model") == "brooks_corey":
            layer.setdefault("alpha", 0.01)
            layer.setdefault("n", 1.1)
        elif layer.get("model") == "van_genuchten":
            layer.setdefault("h_b", -20.0)
            layer.setdefault("lam", 0.5)
    total_thickness = soil.get("total_thickness", 100.0)
    nodes_per_cm = sim.get("nodes_per_cm", 1)
    nz = int(total_thickness * nodes_per_cm) + 1
    
    boundaries = config.get("boundaries", {})
    bc_top = boundaries.get("top", {"type": "flux", "value": 0.0})
    bc_bot = boundaries.get("bottom", {"type": "free_drainage", "value": 0.0})
    
    solute_cfg = config.get("solute", {})
    solute_enabled = solute_cfg.get("enabled", False)
    
    heat_cfg = config.get("heat", {})
    heat_enabled = heat_cfg.get("enabled", False)
    
    root_cfg = config.get("root_uptake", {})
    root_enabled = root_cfg.get("enabled", False)
    
    progress(10, "Initializing Richards solver...")
    
    # Initialize Richards equation solver
    richards = Richards1D(
        layers=layers,
        nz=nz,
        dt=dt,
        dt_max=dt_max,
        max_iter=max_iter,
        tol=tolerance,
        hydraulic_model=layers[0].get("model", "van Genuchten-Mualem") if layers else "van Genuchten-Mualem"
    )
    
    # Initialize solute transport
    solute = None
    if solute_enabled:
        progress(15, "Initializing solute transport...")
        solute = Solute1D(
            nz=nz,
            dz=richards.dz,
            dt_max=dt_max,
            dispersivity=solute_cfg.get("dispersivity", 5.0),
            diffusion_coeff=solute_cfg.get("diffusion", 1.0)
        )
    
    # Initialize heat transport
    heat = None
    if heat_enabled:
        progress(20, "Initializing heat transport...")
        heat = HeatTransport1D(
            nz=nz,
            dz=richards.dz,
            dt_max=dt_max
        )
    
    progress(25, "Setting initial conditions...")
    
    # Initial conditions
    h = np.ones(nz) * sim.get("initial_head", -100.0)
    theta, K, C = richards._hydraulics(h)
    c = np.ones(nz) * solute_cfg.get("initial_concentration", 0.0)
    T = np.ones(nz) * heat_cfg.get("initial_temperature", 20.0)
    
    # Storage for output
    times_out = []
    h_out = []
    theta_out = []
    flux_out = []
    c_out = []
    T_out = []
    
    progress(30, "Starting time loop...")
    
    t = t_start
    next_output = t_start
    step_count = 0
    
    # --- Root uptake config ---
# ✅ Before the time loop
    root_cfg      = config.get("root_uptake", {})
    Tp_series     = root_cfg.get("potential_transpiration", 0.0)
    root_depth    = root_cfg.get("root_depth", 0.3)
    root_dist     = root_cfg.get("root_distribution", "uniform")
    stress_model  = root_cfg.get("stress_model", "none")
    stress_params = {
        "h1": root_cfg.get("h1", -10),
        "h2": root_cfg.get("h2", -25),
        "h3": root_cfg.get("h3", -200),
        "h4": root_cfg.get("h4", -800),
        **root_cfg.get("vg_stress_params", {}),
    }

    print("Start time loop")
    while t < t_end:
        current_dt = min(dt, t_end - t)
        
        # Compute root water uptake sink term
        
        Tp = float(np.interp(t, range(len(Tp_series)), Tp_series)) \
             if isinstance(Tp_series, (list, tuple)) else float(Tp_series)
        print("Tp done")

        
        h, theta, K = richards._step(
            h, theta, current_dt,
            bc_top, bc_bot,
            Tp,
            root_depth,
            root_dist,
            stress_model,
            stress_params,
        )  
        print("richards done")     
        # Compute Darcy flux
        q = np.zeros(nz)
        if len(K) > 1:
            K_int = 0.5 * (K[:-1] + K[1:])
            dh = np.diff(h) / richards.dz
            q_int = -K_int * (dh + 1.0)
            q[1:-1] = 0.5 * (q_int[:-1] + q_int[1:])
            q[0] = q_int[0]
            q[-1] = q_int[-1]
        print("darcy flux done")
        
        # Solve solute transport
        if solute:
            c = solute.step(
                c, c, theta, theta, q, current_dt,
                {"decay": solute_cfg.get("decay", 0.0),
                 "Kd": solute_cfg.get("Kd", 0.0),
                 "rho_b": solute_cfg.get("bulk_density", 1.5)},
                {"type": solute_cfg.get("bc_top_type", "concentration"),
                 "value": solute_cfg.get("bc_top_value", 0.0)},
                {"type": solute_cfg.get("bc_bot_type", "zero_gradient"),
                 "value": 0.0}
            )
        print("solute transport done done")

        # Solve heat transport
        if heat:
            T = heat.solve(
                T, theta, q, current_dt,
                heat_cfg.get("bc_top_type", "temperature"),
                heat_cfg.get("bc_top_value", 20.0),
                heat_cfg.get("bc_bot_type", "zero_gradient"),
                0.0
            )
        print("Heat transport done")
        t += current_dt
        step_count += 1
        
        # Save output at specified intervals
        if t >= next_output or t >= t_end:
            times_out.append(t)
            h_out.append(h.copy())
            theta_out.append(theta.copy())
            flux_out.append(q.copy())
            c_out.append(c.copy())
            T_out.append(T.copy())
            next_output += output_interval
            
            pct = 30 + int(65 * (t - t_start) / (t_end - t_start))
            progress(pct, f"Time: {t:.2f} d (step {step_count})")
    
    progress(95, "Finalizing results...")
    
    # Convert to arrays
    times_arr = np.array(times_out)
    h_arr = np.array(h_out)
    theta_arr = np.array(theta_out)
    flux_arr = np.array(flux_out)
    c_arr = np.array(c_out)
    T_arr = np.array(T_out)
    
    progress(100, "Simulation complete")
    
    # Return results with all required keys for GUI and export
    return {
        "times": times_arr,
        "z": richards.z,
        "thickness": richards.z,
        "h": h_arr,
        "pressure": h_arr,
        "theta": theta_arr,
        "flux": flux_arr,
        "conc": c_arr,
        "temp": T_arr
    }
