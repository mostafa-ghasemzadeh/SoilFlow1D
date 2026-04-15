from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QDoubleSpinBox, QCheckBox, QGroupBox, QGridLayout, QLabel
from PyQt6.QtCore import pyqtSignal


class SoluteWidget(QWidget):
    changed = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.cb_enabled = QCheckBox("Enable Solute Transport")
        self.cb_enabled.stateChanged.connect(self.changed.emit)
        form.addRow("", self.cb_enabled)
        
        self.sp_diff = QDoubleSpinBox()
        self.sp_diff.setRange(0, 100000)
        self.sp_diff.setValue(1.0)
        self.sp_diff.valueChanged.connect(self.changed.emit)
        form.addRow("Diffusion Coeff (cm²/d):", self.sp_diff)
        
        self.sp_disp = QDoubleSpinBox()
        self.sp_disp.setRange(0, 100000)
        self.sp_disp.setValue(5.0)
        self.sp_disp.valueChanged.connect(self.changed.emit)
        form.addRow("Dispersivity (cm):", self.sp_disp)
        


        ic_box = QGroupBox("Initial Conditions")
        ic_layout = QGridLayout(ic_box)

        ic_layout.addWidget(QLabel("Initial Concentration g/m³:"), 0, 0)
        self.sp_c0 = QDoubleSpinBox()
        self.sp_c0.setRange(0, 1000)
        self.sp_c0.setValue(0)
        self.sp_c0.setDecimals(4)
        self.sp_c0.valueChanged.connect(self.changed)
        ic_layout.addWidget(self.sp_c0, 0, 1)

        layout.addWidget(ic_box)
        layout.addLayout(form)
        layout.addStretch()

        
    
    def get_data(self):
        return {
            "enabled": self.cb_enabled.isChecked(),
            "diffusion": self.sp_diff.value(),
            "dispersivity": self.sp_disp.value(),
            "initial_concentration": self.sp_c0.value()
            }
    
    def set_data(self, data):
        self.cb_enabled.setChecked(data.get("enabled", False))
        self.sp_diff.setValue(data.get("diffusion", 1.0))
        self.sp_disp.setValue(data.get("dispersivity", 5.0))
        self.sp_c0.setValue(data.get("initial_concentration", 0))

    
