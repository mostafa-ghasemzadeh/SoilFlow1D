from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QComboBox, QDoubleSpinBox, QCheckBox
from PyQt6.QtCore import pyqtSignal


class RootUptakeWidget(QWidget):
    changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.cb_enabled = QCheckBox("Enable Root Uptake")
        self.cb_enabled.stateChanged.connect(self.changed.emit)
        form.addRow("", self.cb_enabled)
        
        self.cb_model = QComboBox()
        self.cb_model.addItems(["Feddes", "van Genuchten"])
        self.cb_model.currentIndexChanged.connect(self.changed.emit)
        form.addRow("Model:", self.cb_model)
        
        self.sp_max_uptake = QDoubleSpinBox()
        self.sp_max_uptake.setRange(0, 10)
        self.sp_max_uptake.setValue(0.5)
        self.sp_max_uptake.valueChanged.connect(self.changed.emit)
        form.addRow("Max Uptake (cm/d):", self.sp_max_uptake)
        
        layout.addLayout(form)
        layout.addStretch()
    
    def get_data(self):
        return {
            "enabled": self.cb_enabled.isChecked(),
            "model": self.cb_model.currentText().lower(),
            "max_uptake": self.sp_max_uptake.value()
        }
    
    def set_data(self, data):
        self.cb_enabled.setChecked(data.get("enabled", False))
        model = data.get("model", "feddes")
        idx = 0 if model == "feddes" else 1
        self.cb_model.setCurrentIndex(idx)
        self.sp_max_uptake.setValue(data.get("max_uptake", 0.5))
