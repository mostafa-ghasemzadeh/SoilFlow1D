from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QLabel
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np


class ResultsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        layout = QVBoxLayout(self)
        
        # Controls
        ctrl_layout = QHBoxLayout()
        
        ctrl_layout.addWidget(QLabel("Variable:"))
        self.cb_var = QComboBox()
        self.cb_var.addItems(["Pressure Head", "Water Content", "Flux", "Concentration"])
        self.cb_var.currentIndexChanged.connect(self._plot)
        ctrl_layout.addWidget(self.cb_var)
        
        ctrl_layout.addWidget(QLabel("Time:"))
        self.cb_time = QComboBox()
        self.cb_time.currentIndexChanged.connect(self._plot)
        ctrl_layout.addWidget(self.cb_time)
        
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self._load_data)
        ctrl_layout.addWidget(btn_refresh)
        
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)
        
        # Plot
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)
        
        self._load_data()

    def _load_data(self):
        # Generate sample data
        self.data = {
            "times": [0, 1, 2, 5, 10],
            "thickness": np.linspace(0, 100, 50),
            "pressure": np.random.randn(5, 50) * 50 - 100,
            "theta": np.random.rand(5, 50) * 0.2 + 0.2,
            "flux": np.random.randn(5, 50) * 0.5,
            "conc": np.random.rand(5, 50) * 10
        }
        
        self.cb_time.clear()
        self.cb_time.addItems([f"{t} days" for t in self.data["times"]])
        self._plot()

    def _plot(self):
        if not self.data:
            return
        
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        time_idx = self.cb_time.currentIndex()
        var_idx = self.cb_var.currentIndex()
        
        thickness = self.data["thickness"]
        if var_idx == 0:
            values = self.data["pressure"][time_idx]
            ax.set_xlabel("Pressure Head (cm)")
        elif var_idx == 1:
            values = self.data["theta"][time_idx]
            ax.set_xlabel("Water Content")
        elif var_idx == 2:
            values = self.data["flux"][time_idx]
            ax.set_xlabel("Flux (cm/d)")
        else:
            values = self.data["conc"][time_idx]
            ax.set_xlabel("Concentration (mg/L)")
        
        ax.plot(values, thickness)
        ax.set_ylabel("thickness (cm)")
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3)
        
        self.canvas.draw()
