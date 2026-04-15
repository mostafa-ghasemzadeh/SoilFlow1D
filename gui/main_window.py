import json
import csv
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QMenuBar, QMenu, QToolBar, QFileDialog,
    QMessageBox, QLabel, QProgressBar, QDockWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from gui.soil_profile import SoilProfileEditor
from gui.boundary_conditions import BoundaryConditionPanel
from gui.time_series import TimeSeriesPanel
from gui.solute_tab import SoluteWidget
from gui.heat_tab import HeatWidget
from gui.root_uptake_tab import RootUptakeWidget
from gui.results_tab import ResultsWidget
from gui.plot_canvas import PlotCanvas
from gui.simulation_tab import SimulationPanel


class SimulationWorker(QThread):
    """Runs the simulation in a background thread."""

    progress   = pyqtSignal(int, str)   # percent, message
    finished   = pyqtSignal(dict)       # results dict
    error      = pyqtSignal(str)        # error message

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            from core.simulation import run_simulation
            results = run_simulation(self.config, progress_cb=self._cb)
            self.finished.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))

    def _cb(self, pct, msg):
        self.progress.emit(pct, msg)


class MainWindow(QMainWindow):
    """
    Top-level application window.

    Layout
    ------
    MenuBar
    ToolBar
    ─────────────────────────────────────────
    Left panel (tabs)  │  Right panel (plot)
      • Soil Profile   │
      • Boundaries     │   PlotCanvas
      • Time Series    │
      • Solute         │
      • Heat           │
      • Root Uptake
      • simulation
    ─────────────────────────────────────────
    StatusBar  [progress bar]
    """

    APP_NAME    = "SoilFlow 1D"
    APP_VERSION = "Beta 1"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{self.APP_NAME} v{self.APP_VERSION}")
        self.resize(1280, 800)

        self._project_path = None
        self._dirty        = False
        self._worker       = None
        self._results      = None

        self._settings = QSettings("SoilFlow", "SoilFlow1D")

        self._build_ui()
        self._build_menu()
        self._build_toolbar()
        self._restore_geometry()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter)

        # ── Left: input tabs ──────────────────────────────────────────
        self.input_tabs = QTabWidget()
        self.input_tabs.setMinimumWidth(420)
        self.input_tabs.setMaximumWidth(600)

        self.soil_profile_tab  = SoilProfileEditor()
        self.bc_tab            = BoundaryConditionPanel()
        self.ts_tab            = TimeSeriesPanel()
        self.solute_tab        = SoluteWidget()
        self.heat_tab          = HeatWidget()
        self.root_tab          = RootUptakeWidget()
        self.simulation_tab    =SimulationPanel()

        self.input_tabs.addTab(self.soil_profile_tab,  "Soil Profile")
        self.input_tabs.addTab(self.bc_tab,            "Boundaries")
        self.input_tabs.addTab(self.ts_tab,            "Time Series")
        self.input_tabs.addTab(self.solute_tab,        "Solute")
        self.input_tabs.addTab(self.heat_tab,          "Heat")
        self.input_tabs.addTab(self.root_tab,          "Root Uptake")
        self.input_tabs.addTab(self.simulation_tab,    "simulation")

        splitter.addWidget(self.input_tabs)

        # ── Right: plot + results ─────────────────────────────────────
        right_widget  = QWidget()
        right_layout  = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.plot_canvas  = PlotCanvas()
        self.results_tab  = ResultsWidget(self.plot_canvas)

        right_layout.addWidget(self.plot_canvas, stretch=3)
        right_layout.addWidget(self.results_tab, stretch=1)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # ── Status bar ────────────────────────────────────────────────
        self.status_bar  = QStatusBar()
        self.setStatusBar(self.status_bar)

        self._status_label = QLabel("Ready")
        self.status_bar.addWidget(self._status_label, 1)

        self._progress = QProgressBar()
        self._progress.setFixedWidth(200)
        self._progress.setVisible(False)
        self.status_bar.addPermanentWidget(self._progress)


        # Dirty-state tracking
        for tab in (self.soil_profile_tab, self.bc_tab,
                    self.ts_tab, self.solute_tab,
                    self.heat_tab, self.root_tab):
            if hasattr(tab, "changed"):
                tab.changed.connect(self._mark_dirty)

    def _build_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        self._add_action(file_menu, "&New",         self.new_project,
                         QKeySequence.StandardKey.New)
        self._add_action(file_menu, "&Open…",       self.open_project,
                         QKeySequence.StandardKey.Open)
        self._add_action(file_menu, "&Save",        self.save_project,
                         QKeySequence.StandardKey.Save)
        self._add_action(file_menu, "Save &As…",    self.save_project_as,
                         QKeySequence.StandardKey.SaveAs)
        file_menu.addSeparator()
        self._add_action(file_menu, "Export CSV…",  self.export_csv)
        file_menu.addSeparator()
        self._add_action(file_menu, "E&xit",        self.close,
                         QKeySequence.StandardKey.Quit)

        # Simulation
        sim_menu = mb.addMenu("&Simulation")
        self._act_run   = self._add_action(sim_menu, "&Run",  self.run_simulation,  "F5")
        self._act_stop  = self._add_action(sim_menu, "&Stop", self.stop_simulation, "F6")
        self._act_stop.setEnabled(False)

        # View
        view_menu = mb.addMenu("&View")
        self._add_action(view_menu, "Water Content Profile",
                         lambda: self.plot_canvas.show_plot("theta"))
        self._add_action(view_menu, "Pressure Head Profile",
                         lambda: self.plot_canvas.show_plot("h"))
        self._add_action(view_menu, "Solute Concentration",
                         lambda: self.plot_canvas.show_plot("conc"))
        self._add_action(view_menu, "Temperature Profile",
                         lambda: self.plot_canvas.show_plot("temp"))
        self._add_action(view_menu, "Water Balance",
                         lambda: self.plot_canvas.show_plot("balance"))
        view_menu.addSeparator()
        self._add_action(view_menu, "Animate Results",
                         self.animate_results)

        # Help
        help_menu = mb.addMenu("&Help")
        self._add_action(help_menu, "About", self._show_about)

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)

        tb.addAction("New",  self.new_project)
        tb.addAction("Open", self.open_project)
        tb.addAction("Save", self.save_project)
        tb.addSeparator()
        self._tb_run  = tb.addAction("▶  Run",  self.run_simulation)
        self._tb_stop = tb.addAction("■  Stop", self.stop_simulation)
        self._tb_stop.setEnabled(False)
        tb.addSeparator()
        tb.addAction("Export CSV", self.export_csv)

    @staticmethod
    def _add_action(menu, label, slot, shortcut=None):
        act = QAction(label, menu.parent() or menu)
        if shortcut:
            act.setShortcut(shortcut)
        act.triggered.connect(slot)
        menu.addAction(act)
        return act

    # ------------------------------------------------------------------
    # Project I/O
    # ------------------------------------------------------------------
    def _collect_config(self):
        """Gather all widget state into a serialisable dict."""
        return {
            "version":      self.APP_VERSION,
            "soil_profile": self.soil_profile_tab.get_data(),
            "boundaries":   self.bc_tab.get_data(),
            "time_series":  self.ts_tab.get_data(),
            "solute":       self.solute_tab.get_data(),
            "heat":         self.heat_tab.get_data(),
            "root_uptake":  self.root_tab.get_data(),
            "simulation":   self.simulation_tab.get_data(),
        }

    def _apply_config(self, cfg):
        """Push a loaded config dict back into all widgets."""
        self.soil_profile_tab.set_data(cfg.get("soil_profile", {}))
        self.bc_tab.set_data(cfg.get("boundaries",   {}))
        self.ts_tab.set_data(cfg.get("time_series",  {}))
        self.solute_tab.set_data(cfg.get("solute",   {}))
        self.heat_tab.set_data(cfg.get("heat",       {}))
        self.root_tab.set_data(cfg.get("root_uptake",{}))
        self.simulation_tab.set_data(cfg.get("simulation"),{})



    def new_project(self):
        if not self._confirm_discard():
            return
        self._apply_config({})
        self._project_path = None
        self._dirty        = False
        self._results      = None
        self.plot_canvas.clear()
        self._set_title()

    def open_project(self):
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "",
            "SoilFlow Project (*.sfp);;JSON (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self._apply_config(cfg)
            self._project_path = path
            self._dirty        = False
            self._set_title()
            self._set_status(f"Opened: {Path(path).name}")
        except Exception as exc:
            QMessageBox.critical(self, "Open Failed", str(exc))

    def save_project(self):
        if self._project_path is None:
            self.save_project_as()
        else:
            self._write_project(self._project_path)

    def save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", "",
            "SoilFlow Project (*.sfp);;JSON (*.json)"
        )
        if path:
            self._write_project(path)

    def _write_project(self, path):
        try:
            cfg = self._collect_config()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            self._project_path = path
            self._dirty        = False
            self._set_title()
            self._set_status(f"Saved: {Path(path).name}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))

    def export_csv(self):
        if self._results is None:
            QMessageBox.information(self, "No Results",
                                    "Run a simulation first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        try:
            self._write_csv(path, self._results)
            self._set_status(f"Exported: {Path(path).name}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def _write_csv(self, path, results):
        times  = results.get("times",  [])
        z      = results.get("z",      [])
        theta  = results.get("theta",  [])
        h      = results.get("h",      [])
        conc   = results.get("conc",   [])
        temp   = results.get("temp",   [])

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            h_row = ["time_day", "thickness_cm", "theta", "h_cm"]
            if conc:
                h_row.append("conc_mg_per_cm3")
            if temp:
                h_row.append("temp_C")
            writer.writerow(h_row)

            for ti, t in enumerate(times):
                for zi, thickness in enumerate(z):
                    row = [
                        round(t, 6),
                        round(thickness, 4),
                        round(theta[ti][zi], 6),
                        round(h[ti][zi], 4),
                    ]
                    if conc:
                        row.append(round(conc[ti][zi], 6))
                    if temp:
                        row.append(round(temp[ti][zi], 4))
                    writer.writerow(row)

    # ------------------------------------------------------------------
    # Simulation control
    # ------------------------------------------------------------------
    def run_simulation(self):
        if self._worker and self._worker.isRunning():
            return

        cfg = self._collect_config()
        ok, msg = self._validate_config(cfg)
        if not ok:
            QMessageBox.warning(self, "Validation Error", msg)
            return

        self._worker = SimulationWorker(cfg)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._act_run.setEnabled(False)
        self._tb_run.setEnabled(False)
        self._act_stop.setEnabled(True)
        self._tb_stop.setEnabled(True)
        self._set_status("Running simulation…")

        self._worker.start()

    def stop_simulation(self):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()
            self._set_status("Simulation stopped.")
            self._reset_run_buttons()

    def _on_progress(self, pct, msg):
        self._progress.setValue(pct)
        self._set_status(msg)

    def _on_finished(self, results):
        self._results = results
        self.results_tab.load_results(results)
        self.plot_canvas.plot_results(results, plot_type="theta")
        self._set_status("Simulation complete.")
        self._reset_run_buttons()

    def _on_error(self, msg):
        QMessageBox.critical(self, "Simulation Error", msg)
        self._set_status("Simulation failed.")
        self._reset_run_buttons()

    def _reset_run_buttons(self):
        self._progress.setVisible(False)
        self._act_run.setEnabled(True)
        self._tb_run.setEnabled(True)
        self._act_stop.setEnabled(False)
        self._tb_stop.setEnabled(False)

    def animate_results(self):
        if self._results is None:
            QMessageBox.information(self, "No Results",
                                    "Run a simulation first.")
            return
        self.plot_canvas.animate(self._results)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate_config(self, cfg):
        sp = cfg.get("soil_profile", {})
        layers = sp.get("layers", [])
        if not layers:
            return False, "Define at least one soil layer."

        total_thickness = sum(L.get("thickness", 0) for L in layers)
        if total_thickness <= 0:
            return False, "Total soil column thickness must be > 0 cm."
        if total_thickness > 50000:
            return False, "Total thickness exceeds 50m limit."

        ts = cfg.get("time_series", [])
        if isinstance(ts, list) and len(ts) > 0:
        # Time series is a list of time points, validate it has data
            if len(ts) == 0:
                return False, "Time series cannot be empty"
        else:
            # Handle as dict if needed for other validation
            pass

        return True, ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _mark_dirty(self):
        if not self._dirty:
            self._dirty = True
            self._set_title()

    def _set_title(self):
        name  = Path(self._project_path).name if self._project_path else "Untitled"
        dirty = " *" if self._dirty else ""
        self.setWindowTitle(
            f"{self.APP_NAME} v{self.APP_VERSION}  —  {name}{dirty}"
        )

    def _set_status(self, msg):
        self._status_label.setText(msg)

    def _confirm_discard(self):
        if not self._dirty:
            return True
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            "You have unsaved changes. Discard them?",
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel
        )
        return reply == QMessageBox.StandardButton.Discard

    def _show_about(self):
        QMessageBox.about(
            self, f"About {self.APP_NAME}",
            f"<b>{self.APP_NAME}</b> v{self.APP_VERSION}<br><br>"
            "1D Soil Water Flow, Solute Transport,<br>"
            "Heat Transport &amp; Root Water Uptake Simulator.<br><br>"
            "Numerical scheme: Galerkin FEM, Picard iteration,<br>"
            "Backward Euler (Richards/Solute), Crank-Nicolson (Heat).<br><br>"
            "Units: cm, cm/day, °C <br><br>"
            "Version: Beta 1 <br><br>"
            "Created by Mostafa Ghasemzadeh Ortakand Email: mortakand@gmail.com"
        )

    # ------------------------------------------------------------------
    # Window events
    # ------------------------------------------------------------------
    def closeEvent(self, event):
        if self._confirm_discard():
            self._save_geometry()
            event.accept()
        else:
            event.ignore()

    def _save_geometry(self):
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("windowState", self.saveState())

    def _restore_geometry(self):
        geom  = self._settings.value("geometry")
        state = self._settings.value("windowState")
        if geom:
            self.restoreGeometry(geom)
        if state:
            self.restoreState(state)
