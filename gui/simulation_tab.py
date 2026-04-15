from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QDoubleSpinBox, QSpinBox, QGroupBox
from PyQt6.QtCore import pyqtSignal


class SimulationPanel(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Time settings
        time_box = QGroupBox("Time Settings")
        g = QGridLayout(time_box)
        
        g.addWidget(QLabel("Start Time (d):"), 0, 0)
        self.sp_t_start = QDoubleSpinBox()
        self.sp_t_start.setRange(0, 10000000)
        self.sp_t_start.setValue(0)
        self.sp_t_start.valueChanged.connect(self.changed)
        g.addWidget(self.sp_t_start, 0, 1)
        
        g.addWidget(QLabel("End Time (d):"), 1, 0)
        self.sp_t_end = QDoubleSpinBox()
        self.sp_t_end.setRange(0, 10000000)
        self.sp_t_end.setValue(100)
        self.sp_t_end.valueChanged.connect(self.changed)
        g.addWidget(self.sp_t_end, 1, 1)
        
        g.addWidget(QLabel("Time Step (d):"), 2, 0)
        self.sp_dt = QDoubleSpinBox()
        self.sp_dt.setRange(0.00000001, 10)
        self.sp_dt.setValue(0.01)
        self.sp_dt.setDecimals(4)
        self.sp_dt.valueChanged.connect(self.changed)
        g.addWidget(self.sp_dt, 2, 1)
        
        g.addWidget(QLabel("Output Interval:"), 3, 0)
        self.sp_output = QSpinBox()
        self.sp_output.setRange(1, 10000000)
        self.sp_output.setValue(10)
        self.sp_output.valueChanged.connect(self.changed)
        g.addWidget(self.sp_output, 3, 1)
        
        layout.addWidget(time_box)
        # Solver settings
        solver_box = QGroupBox("Solver Settings")
        g2 = QGridLayout(solver_box)
        
        g2.addWidget(QLabel("Max Iterations:"), 0, 0)
        self.sp_max_iter = QSpinBox()
        self.sp_max_iter.setRange(1, 1000000000)
        self.sp_max_iter.setValue(1000)
        self.sp_max_iter.valueChanged.connect(self.changed)
        g2.addWidget(self.sp_max_iter, 0, 1)
        
        g2.addWidget(QLabel("Tolerance:"), 1, 0)
        self.sp_tol = QDoubleSpinBox()
        self.sp_tol.setRange(1e-10, 1000)
        self.sp_tol.setValue(1e-2)
        self.sp_tol.setDecimals(10)
        self.sp_tol.valueChanged.connect(self.changed)
        g2.addWidget(self.sp_tol, 1, 1)
        
        layout.addWidget(solver_box)
        layout.addStretch()

    def get_data(self):
        return {
            "t_start": self.sp_t_start.value(),
            "t_end": self.sp_t_end.value(),
            "dt": self.sp_dt.value(),
            "output_interval": self.sp_output.value(),
            "max_iter": self.sp_max_iter.value(),
            "tolerance": self.sp_tol.value()
        }

    def set_data(self, d):
        self.sp_t_start.setValue(d.get("t_start", 0))
        self.sp_t_end.setValue(d.get("t_end", 100))
        self.sp_dt.setValue(d.get("dt", 0.01))
        self.sp_output.setValue(d.get("output_interval", 10))
        self.sp_max_iter.setValue(d.get("max_iter", 100))
        self.sp_tol.setValue(d.get("tolerance", 1e-2))
