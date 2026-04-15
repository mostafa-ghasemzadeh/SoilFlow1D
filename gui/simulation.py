from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QProgressBar, QLabel
)
from PyQt6.QtCore import pyqtSignal, QThread
import json


class SimulationWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            import numpy as np
            from core.richards import Richards1D
    
            cfg     = self.config
            self.log.emit("Building solver...")
            self.progress.emit(5)
    
            # ── Soil layers ──────────────────────────────────────────────
            layers = cfg["soil_profile"]["layers"]   # list of layer dicts
    
            # ── Solver settings ──────────────────────────────────────────
            sim_cfg = cfg.get("simulation", {})
            nz      = int(sim_cfg.get("nz",      100))
            dz      = float(sim_cfg.get("dz",    0.1))
            dt      = float(sim_cfg.get("dt",    0.01))
            dt_max  = float(sim_cfg.get("dt_max", 1.0))
            dt_min  = float(sim_cfg.get("dt_min", 1e-4))
            t_end   = float(sim_cfg.get("t_end", 10.0))
            hyd_model = sim_cfg.get("hydraulic_model", "van_genuchten")
    
            solver = Richards1D(
                layers         = layers,
                dz             = dz,
                hydraulic_model= hyd_model,
                nz             = nz,
                dt             = dt,
                dt_max         = dt_max,
                dt_min         = dt_min,
            )
            self.log.emit(f"Solver ready — {nz} nodes, dz={dz} cm")
            self.progress.emit(15)
    
            # ── Initial conditions ───────────────────────────────────────
            h_init_val = float(cfg.get("initial_conditions", {}).get("h_init", -100.0))
            h_init     = np.full(nz, h_init_val)
    
            # ── Boundary conditions ──────────────────────────────────────
            bc      = cfg.get("boundaries", {})
            bc_top_raw = bc.get("top",    {"type": "flux",          "value": 0.5})
            bc_bot     = bc.get("bottom", {"type": "free_drainage", "value": 0.0})
    
            # Guarantee "value" key exists (safety net)
            if "value" not in bc_top_raw:
                bc_top_raw["value"] = (
                    bc_top_raw.get("precip", 0.0) - bc_top_raw.get("evap", 0.0)
                )
            if "value" not in bc_bot:
                bc_bot["value"] = bc_bot.get("flux", bc_bot.get("head", 0.0))
    
            # Build bc_top_series & rainfall_series as constant time series
            t_series       = [0.0, t_end]
            bc_top_series  = [(t, bc_top_raw) for t in t_series]
    
            precip         = bc_top_raw.get("precip", bc_top_raw.get("value", 0.0))
            evap           = bc_top_raw.get("evap",   0.0)
            rainfall_series = [(t, precip)           for t in t_series]
            Tp_series       = [(t, evap)             for t in t_series]
    
            # ── Root uptake ──────────────────────────────────────────────
            ru          = cfg.get("root_uptake", {})
            root_depth  = float(ru.get("root_depth",  30.0))
            root_dist   = ru.get("root_distribution", "exponential")
            stress_model= ru.get("stress_model",      "Feddes")
            stress_params = ru.get("stress_params",   {})
    
            self.log.emit("Starting Richards solver...")
            self.progress.emit(20)
    
            # ── Run ──────────────────────────────────────────────────────
            results = solver.run(
                h_init          = h_init,
                t_end           = t_end,
                bc_top_series   = bc_top_series,
                bc_bot          = bc_bot,
                Tp_series       = Tp_series,
                rainfall_series = rainfall_series,
                root_thickness  = root_depth,
                root_dist       = root_dist,
                stress_model    = stress_model,
                stress_params   = stress_params,
                output_times    = np.linspace(0, t_end, 50),
                progress_callback = lambda p: self.progress.emit(20 + int(p * 0.78)),
            )
    
            self.results = results   # store for results panel
            self.log.emit(f"Done — {len(results['times'])} output steps saved.")
            self.progress.emit(100)
            self.finished.emit(True)
    
        except Exception as e:
            import traceback
            self.log.emit(f"ERROR: {e}")
            self.log.emit(traceback.format_exc())
            self.finished.emit(False)


class SimulationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = {}
        self.worker = None
        
        layout = QVBoxLayout(self)
        
        # Status
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Progress
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        
        # Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_run = QPushButton("Run Simulation")
        self.btn_run.clicked.connect(self._run)
        btn_layout.addWidget(self.btn_run)
        
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop)
        btn_layout.addWidget(self.btn_stop)
        
        btn_clear = QPushButton("Clear Log")
        btn_clear.clicked.connect(self.log.clear)
        btn_layout.addWidget(btn_clear)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def set_config(self, config):
        self.config = config

    def _run(self):
        if not self.config:
            self.log.append("Error: No configuration loaded")
            return
        
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress.setValue(0)
        self.status_label.setText("Running...")
        
        self.worker = SimulationWorker(self.config)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log.connect(self.log.append)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.log.append("Simulation stopped by user")
            self._on_finished(False)

    def _on_finished(self, success):
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("Completed" if success else "Failed")
