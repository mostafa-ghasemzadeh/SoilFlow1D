from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal


class ResultsWidget(QWidget):
    plot_requested = pyqtSignal(str, int)
    
    def __init__(self, plot_canvas, parent=None):
        super().__init__(parent)
        self.plot_canvas = plot_canvas
        self.results = None
        
        layout = QVBoxLayout(self)
        
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Variable:"))
        self.cb_var = QComboBox()
        self.cb_var.addItems(["Water Content", "Pressure Head", "Concentration", "Temperature"])
        ctrl.addWidget(self.cb_var)
        
        ctrl.addWidget(QLabel("Time:"))
        self.cb_time = QComboBox()
        ctrl.addWidget(self.cb_time)
        
        btn_plot = QPushButton("Plot")
        btn_plot.clicked.connect(self._plot)
        ctrl.addWidget(btn_plot)
        
        ctrl.addStretch()
        layout.addLayout(ctrl)
    
    def load_results(self, results):
        self.results = results
        times = results.get("times", [])
        self.cb_time.clear()
        self.cb_time.addItems([f"{t:.2f} d" for t in times])
    
    def _plot(self):
        if not self.results:
            return
        var_map = {
            "Water Content": "theta",
            "Pressure Head": "h",
            "Concentration": "conc",
            "Temperature": "temp"
        }
        var = var_map[self.cb_var.currentText()]
        time_idx = self.cb_time.currentIndex()
        self.plot_canvas.plot_results(self.results, plot_type=var, time_idx=time_idx)
