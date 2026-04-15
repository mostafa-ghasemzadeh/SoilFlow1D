from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QDoubleSpinBox, QCheckBox
from PyQt6.QtCore import pyqtSignal


class HeatWidget(QWidget):
    changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.cb_enabled = QCheckBox("Enable Heat Transport")
        self.cb_enabled.stateChanged.connect(self.changed.emit)
        form.addRow("", self.cb_enabled)
        
        self.sp_lambda = QDoubleSpinBox()
        self.sp_lambda.setRange(0, 100)
        self.sp_lambda.setValue(0.5)
        self.sp_lambda.valueChanged.connect(self.changed.emit)
        form.addRow("Thermal Conductivity:", self.sp_lambda)
        
        self.sp_capacity = QDoubleSpinBox()
        self.sp_capacity.setRange(0, 50)
        self.sp_capacity.setValue(2.0)
        self.sp_capacity.valueChanged.connect(self.changed.emit)
        form.addRow("Heat Capacity:", self.sp_capacity)
        
        layout.addLayout(form)
        layout.addStretch()
    
    def get_data(self):
        return {
            "enabled": self.cb_enabled.isChecked(),
            "thermal_conductivity": self.sp_lambda.value(),
            "heat_capacity": self.sp_capacity.value()
        }
    
    def set_data(self, data):
        self.cb_enabled.setChecked(data.get("enabled", False))
        self.sp_lambda.setValue(data.get("thermal_conductivity", 0.5))
        self.sp_capacity.setValue(data.get("heat_capacity", 2.0))
