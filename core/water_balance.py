import numpy as np


class WaterBalance:
    """
    Tracks and diagnoses the soil column water balance at each time step.

    Conservation equation (integrated over column thickness L):

        dS/dt = P + I - ET - D - R

    Where:
        S  = total soil water storage [cm]
        P  = precipitation [cm/day]
        I  = irrigation [cm/day]
        ET = evapotranspiration (E + T) [cm/day]
        D  = deep drainage (bottom flux) [cm/day]
        R  = surface runoff [cm/day]

    Cumulative error:
        ΔS_error = ΔS_actual - ΔS_predicted
    """

    def __init__(self, nz, dz):
        """
        Parameters
        ----------
        nz : int    number of nodes
        dz : float  node spacing [cm]
        """
        self.nz = nz
        self.dz = dz

        # Cumulative fluxes [cm]
        self.cum_precip    = 0.0
        self.cum_irrig     = 0.0
        self.cum_evap      = 0.0
        self.cum_transp    = 0.0
        self.cum_drainage  = 0.0
        self.cum_runoff    = 0.0

        # Storage history
        self._S_initial    = None
        self._S_prev       = None

        # Cumulative balance error [cm]
        self.cum_error     = 0.0

        # Per-step log
        self.log = []

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    def storage(self, theta):
        """
        Total water storage in the column [cm].

        Parameters
        ----------
        theta : ndarray  volumetric water content [-]

        Returns
        -------
        S : float  [cm]
        """
        return float(np.sum(theta) * self.dz)

    def initialize(self, theta):
        """Record initial storage. Must be called before the first step."""
        S0 = self.storage(theta)
        self._S_initial = S0
        self._S_prev    = S0

    # ------------------------------------------------------------------
    # Update at each time step
    # ------------------------------------------------------------------
    def update(self, theta_new, theta_old, dt,
               precip=0.0, irrig=0.0,
               evap=0.0, transp=0.0,
               drainage=0.0, runoff=0.0):
        """
        Update cumulative fluxes and compute balance error for one step.

        Parameters
        ----------
        theta_new : ndarray  water content at end of step [-]
        theta_old : ndarray  water content at start of step [-]
        dt        : float    time step [days]
        precip    : float    precipitation rate [cm/day]
        irrig     : float    irrigation rate [cm/day]
        evap      : float    evaporation rate [cm/day]
        transp    : float    transpiration rate [cm/day]
        drainage  : float    bottom drainage rate [cm/day]  (positive = out)
        runoff    : float    surface runoff rate [cm/day]   (positive = out)

        Returns
        -------
        error : float  balance error this step [cm]
        """
        if self._S_prev is None:
            raise RuntimeError("Call initialize(theta) before update().")

        S_new = self.storage(theta_new)
        S_old = self.storage(theta_old)
        dS    = S_new - S_old

        # Predicted change from fluxes
        net_in  = (precip + irrig) * dt
        net_out = (evap + transp + drainage + runoff) * dt
        dS_pred = net_in - net_out

        error = dS - dS_pred

        # Accumulate
        self.cum_precip   += precip   * dt
        self.cum_irrig    += irrig    * dt
        self.cum_evap     += evap     * dt
        self.cum_transp   += transp   * dt
        self.cum_drainage += drainage * dt
        self.cum_runoff   += runoff   * dt
        self.cum_error    += error
        self._S_prev       = S_new

        self.log.append({
            "dS":       dS,
            "dS_pred":  dS_pred,
            "error":    error,
            "S":        S_new,
        })

        return error

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    def summary(self, theta_current):
        """
        Print a formatted water balance summary.

        Parameters
        ----------
        theta_current : ndarray  current water content [-]
        """
        S_now   = self.storage(theta_current)
        delta_S = S_now - (self._S_initial or 0.0)

        print("=" * 46)
        print(f"{'Water Balance Summary':^46}")
        print("=" * 46)
        print(f"  Initial storage       : {self._S_initial or 0.0:>10.4f} cm")
        print(f"  Current storage       : {S_now:>10.4f} cm")
        print(f"  ΔS (actual)           : {delta_S:>10.4f} cm")
        print("-" * 46)
        print(f"  Cumulative precip     : {self.cum_precip:>10.4f} cm")
        print(f"  Cumulative irrigation : {self.cum_irrig:>10.4f} cm")
        print(f"  Cumulative evaporation: {self.cum_evap:>10.4f} cm")
        print(f"  Cumulative transpir.  : {self.cum_transp:>10.4f} cm")
        print(f"  Cumulative drainage   : {self.cum_drainage:>10.4f} cm")
        print(f"  Cumulative runoff     : {self.cum_runoff:>10.4f} cm")
        print("-" * 46)
        predicted = (
            self.cum_precip + self.cum_irrig
            - self.cum_evap - self.cum_transp
            - self.cum_drainage - self.cum_runoff
        )
        print(f"  ΔS (predicted)        : {predicted:>10.4f} cm")
        print(f"  Cumulative error      : {self.cum_error:>10.4f} cm")
        rel = (
            abs(self.cum_error) / (abs(predicted) + 1e-30) * 100.0
        )
        print(f"  Relative error        : {rel:>10.4f} %")
        print("=" * 46)

    def relative_error(self):
        """
        Relative cumulative balance error [-].

        Returns
        -------
        float  |cum_error| / (|total_input| + ε)
        """
        total_input = self.cum_precip + self.cum_irrig + 1e-30
        return abs(self.cum_error) / total_input

    def reset(self, theta):
        """Reset all accumulators and reinitialize storage."""
        self.__init__(self.nz, self.dz)
        self.initialize(theta)

    # ------------------------------------------------------------------
    # Profile diagnostics
    # ------------------------------------------------------------------
    def theta_profile_stats(self, theta, z):
        """
        Compute thickness-weighted statistics of the water content profile.

        Parameters
        ----------
        theta : ndarray  volumetric water content [-]
        z     : ndarray  node thicknesss [cm]

        Returns
        -------
        dict with keys: mean, min, max, storage, centroid_thickness
        """
        theta = np.asarray(theta)
        z     = np.asarray(z)
        S     = self.storage(theta)

        # thickness of centroid of water storage
        centroid = (
            float(np.sum(theta * z) * self.dz) / (S + 1e-30)
        )

        return {
            "mean":           float(np.mean(theta)),
            "min":            float(np.min(theta)),
            "max":            float(np.max(theta)),
            "storage":        S,
            "centroid_thickness": centroid,
        }
