from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QDoubleSpinBox, QComboBox,
    QRadioButton, QButtonGroup, QTabWidget
)
from PyQt6.QtCore import pyqtSignal


class BoundaryConditionPanel(QWidget):
    """Boundary conditions for top and bottom."""
    
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        
        tabs = QTabWidget()
        tabs.addTab(self._build_top(), "Top Boundary")
        tabs.addTab(self._build_bottom(), "Bottom Boundary")
        root.addWidget(tabs)

    def _build_top(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        # Type selection
        type_box = QGroupBox("Boundary Type")
        type_layout = QVBoxLayout(type_box)
        
        self.top_group = QButtonGroup()
        self.rb_top_flux = QRadioButton("Constant Flux")
        self.rb_top_head = QRadioButton("Constant Head")
        self.rb_top_atm = QRadioButton("Atmospheric")
        
        self.top_group.addButton(self.rb_top_flux, 0)
        self.top_group.addButton(self.rb_top_head, 1)
        self.top_group.addButton(self.rb_top_atm, 2)
        
        type_layout.addWidget(self.rb_top_flux)
        type_layout.addWidget(self.rb_top_head)
        type_layout.addWidget(self.rb_top_atm)
        
        self.rb_top_atm.setChecked(True)
        self.top_group.buttonClicked.connect(self.changed)
        
        layout.addWidget(type_box)
        
        # Parameters
        param_box = QGroupBox("Parameters")
        g = QGridLayout(param_box)
        
        g.addWidget(QLabel("Flux (cm/d):"), 0, 0)
        self.sp_top_flux = QDoubleSpinBox()
        self.sp_top_flux.setRange(-1000.0, 1000.0)
        self.sp_top_flux.setValue(0.5)
        self.sp_top_flux.setDecimals(4)
        self.sp_top_flux.valueChanged.connect(self.changed)
        g.addWidget(self.sp_top_flux, 0, 1)
        
        g.addWidget(QLabel("Head (cm):"), 1, 0)
        self.sp_top_head = QDoubleSpinBox()
        self.sp_top_head.setRange(-10000.0, 10000.0)
        self.sp_top_head.setValue(0.0)
        self.sp_top_head.setDecimals(2)
        self.sp_top_head.valueChanged.connect(self.changed)
        g.addWidget(self.sp_top_head, 1, 1)
        
        g.addWidget(QLabel("Precip (cm/d):"), 2, 0)
        self.sp_precip = QDoubleSpinBox()
        self.sp_precip.setRange(0.0, 100.0)
        self.sp_precip.setValue(0.5)
        self.sp_precip.setDecimals(4)
        self.sp_precip.valueChanged.connect(self.changed)
        g.addWidget(self.sp_precip, 2, 1)
        
        g.addWidget(QLabel("Evap (cm/d):"), 3, 0)
        self.sp_evap = QDoubleSpinBox()
        self.sp_evap.setRange(0.0, 100.0)
        self.sp_evap.setValue(0.3)
        self.sp_evap.setDecimals(4)
        self.sp_evap.valueChanged.connect(self.changed)
        g.addWidget(self.sp_evap, 3, 1)
        
        layout.addWidget(param_box)
        layout.addStretch()
        
        return w

    def _build_bottom(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        # Type selection
        type_box = QGroupBox("Boundary Type")
        type_layout = QVBoxLayout(type_box)
        
        self.bot_group = QButtonGroup()
        self.rb_bot_flux = QRadioButton("Constant Flux")
        self.rb_bot_head = QRadioButton("Constant Head")
        self.rb_bot_free = QRadioButton("Free Drainage")
        self.rb_bot_seep = QRadioButton("Seepage Face")
        
        self.bot_group.addButton(self.rb_bot_flux, 0)
        self.bot_group.addButton(self.rb_bot_head, 1)
        self.bot_group.addButton(self.rb_bot_free, 2)
        self.bot_group.addButton(self.rb_bot_seep, 3)
        
        type_layout.addWidget(self.rb_bot_flux)
        type_layout.addWidget(self.rb_bot_head)
        type_layout.addWidget(self.rb_bot_free)
        type_layout.addWidget(self.rb_bot_seep)
        
        self.rb_bot_free.setChecked(True)
        self.bot_group.buttonClicked.connect(self.changed)
        
        layout.addWidget(type_box)
        
        # Parameters
        param_box = QGroupBox("Parameters")
        g = QGridLayout(param_box)
        
        g.addWidget(QLabel("Flux (cm/d):"), 0, 0)
        self.sp_bot_flux = QDoubleSpinBox()
        self.sp_bot_flux.setRange(-1000.0, 1000.0)
        self.sp_bot_flux.setValue(0.0)
        self.sp_bot_flux.setDecimals(4)
        self.sp_bot_flux.valueChanged.connect(self.changed)
        g.addWidget(self.sp_bot_flux, 0, 1)
        
        g.addWidget(QLabel("Head (cm):"), 1, 0)
        self.sp_bot_head = QDoubleSpinBox()
        self.sp_bot_head.setRange(-10000.0, 10000.0)
        self.sp_bot_head.setValue(-100.0)
        self.sp_bot_head.setDecimals(2)
        self.sp_bot_head.valueChanged.connect(self.changed)
        g.addWidget(self.sp_bot_head, 1, 1)
        
        layout.addWidget(param_box)
        layout.addStretch()
        
        return w

    def get_data(self) -> dict:
        top_type = ["flux", "head", "atmospheric"][self.top_group.checkedId()]
        bot_type = ["flux", "head", "free_drainage", "seepage"][self.bot_group.checkedId()]
    
        # Build "value" based on selected type
        if top_type == "flux":
            top_value = self.sp_top_flux.value()
        elif top_type == "head":
            top_value = self.sp_top_head.value()
        else:  # atmospheric
            top_value = self.sp_precip.value() - self.sp_evap.value()
    
        if bot_type == "flux":
            bot_value = self.sp_bot_flux.value()
        elif bot_type == "head":
            bot_value = self.sp_bot_head.value()
        else:  # free_drainage or seepage — value unused but must exist
            bot_value = 0.0
    
        return {
            "top": {
                "type":   top_type,
                "value":  top_value,
                # keep extras so set_data() round-trips correctly
                "flux":   self.sp_top_flux.value(),
                "head":   self.sp_top_head.value(),
                "precip": self.sp_precip.value(),
                "evap":   self.sp_evap.value(),
            },
            "bottom": {
                "type":  bot_type,
                "value": bot_value,
                "flux":  self.sp_bot_flux.value(),
                "head":  self.sp_bot_head.value(),
            }
        }


    def set_data(self, d: dict):
        top = d.get("top", {})
        bot = d.get("bottom", {})
        
        # Top boundary
        top_type = top.get("type", "atmospheric")
        type_map = {"flux": 0, "head": 1, "atmospheric": 2}
        self.top_group.button(type_map.get(top_type, 2)).setChecked(True)
        
        self.sp_top_flux.setValue(top.get("flux", 0.5))
        self.sp_top_head.setValue(top.get("head", 0.0))
        self.sp_precip.setValue(top.get("precip", 0.5))
        self.sp_evap.setValue(top.get("evap", 0.3))
        
        # Bottom boundary
        bot_type = bot.get("type", "free_drainage")
        type_map = {"flux": 0, "head": 1, "free_drainage": 2, "seepage": 3}
        self.bot_group.button(type_map.get(bot_type, 2)).setChecked(True)
        
        self.sp_bot_flux.setValue(bot.get("flux", 0.0))
        self.sp_bot_head.setValue(bot.get("head", -100.0))
