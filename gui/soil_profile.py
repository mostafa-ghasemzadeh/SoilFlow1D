import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QDoubleSpinBox, QSpinBox,
    QComboBox, QScrollArea, QFrame, QSizePolicy, QTabWidget
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont

# Texture colors
TEXTURE_COLORS = {
    "Sand": "#F5DEB3", "Loamy Sand": "#DEB887", "Sandy Loam": "#D2B48C",
    "Loam": "#8B7355", "Silt Loam": "#A0896B", "Silt": "#C8A882",
    "Sandy Clay Loam": "#CD853F", "Clay Loam": "#A0522D",
    "Silty Clay Loam": "#8B6914", "Sandy Clay": "#B8860B",
    "Silty Clay": "#6B4423", "Clay": "#4A3728", "Custom": "#9E9E9E",
}

# van Genuchten presets
VG_PRESETS = {
    "Sand": dict(theta_r=0.045, theta_s=0.430, alpha=0.145, n=2.68, Ks=712.8),
    "Loamy Sand": dict(theta_r=0.057, theta_s=0.410, alpha=0.124, n=2.28, Ks=350.2),
    "Sandy Loam": dict(theta_r=0.065, theta_s=0.410, alpha=0.075, n=1.89, Ks=106.1),
    "Loam": dict(theta_r=0.078, theta_s=0.430, alpha=0.036, n=1.56, Ks=24.96),
    "Silt Loam": dict(theta_r=0.067, theta_s=0.450, alpha=0.020, n=1.41, Ks=10.80),
    "Silt": dict(theta_r=0.034, theta_s=0.460, alpha=0.016, n=1.37, Ks=6.00),
    "Sandy Clay Loam": dict(theta_r=0.100, theta_s=0.390, alpha=0.059, n=1.48, Ks=31.44),
    "Clay Loam": dict(theta_r=0.095, theta_s=0.410, alpha=0.019, n=1.31, Ks=6.24),
    "Silty Clay Loam": dict(theta_r=0.089, theta_s=0.430, alpha=0.010, n=1.23, Ks=1.68),
    "Sandy Clay": dict(theta_r=0.100, theta_s=0.380, alpha=0.027, n=1.23, Ks=2.88),
    "Silty Clay": dict(theta_r=0.070, theta_s=0.360, alpha=0.005, n=1.09, Ks=0.48),
    "Clay": dict(theta_r=0.068, theta_s=0.380, alpha=0.008, n=1.09, Ks=4.80),
    "Custom": dict(theta_r=0.078, theta_s=0.430, alpha=0.036, n=1.56, Ks=24.96),
}

# Brooks-Corey presets
BC_PRESETS = {
    "Sand": dict(theta_r=0.045, theta_s=0.430, h_b=-7.26, lam=0.592, Ks=712.8),
    "Loamy Sand": dict(theta_r=0.057, theta_s=0.410, h_b=-8.69, lam=0.474, Ks=350.2),
    "Sandy Loam": dict(theta_r=0.065, theta_s=0.410, h_b=-14.66, lam=0.322, Ks=106.1),
    "Loam": dict(theta_r=0.078, theta_s=0.430, h_b=-11.15, lam=0.220, Ks=24.96),
    "Silt Loam": dict(theta_r=0.067, theta_s=0.450, h_b=-20.76, lam=0.211, Ks=10.80),
    "Silt": dict(theta_r=0.034, theta_s=0.460, h_b=-28.13, lam=0.127, Ks=6.00),
    "Sandy Clay Loam": dict(theta_r=0.100, theta_s=0.390, h_b=-28.08, lam=0.250, Ks=31.44),
    "Clay Loam": dict(theta_r=0.095, theta_s=0.410, h_b=-25.89, lam=0.194, Ks=6.24),
    "Silty Clay Loam": dict(theta_r=0.089, theta_s=0.430, h_b=-32.56, lam=0.151, Ks=1.68),
    "Sandy Clay": dict(theta_r=0.100, theta_s=0.380, h_b=-29.17, lam=0.168, Ks=2.88),
    "Silty Clay": dict(theta_r=0.070, theta_s=0.360, h_b=-34.19, lam=0.127, Ks=0.48),
    "Clay": dict(theta_r=0.068, theta_s=0.380, h_b=-37.30, lam=0.131, Ks=4.80),
    "Custom": dict(theta_r=0.068, theta_s=0.380, h_b=-20.0, lam=0.220, Ks=10.0),
}

MAX_LAYERS = 5


class ProfileCanvas(QFrame):
    """Visual soil profile."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(110, 300)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._layers = []

    def update_layers(self, layers):
        self._layers = [L for L in layers if L.get("thickness", 0) > 0]
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._layers:
            return

        total = sum(L["thickness"] for L in self._layers)
        if total <= 0:
            return

        painter = QPainter(self)
        W, H = self.width(), self.height()
        MT, MB, x0, col_w = 22, 14, 18, W - 30
        draw_h = H - MT - MB

        painter.setFont(QFont("Arial", 7))
        painter.setPen(QPen(QColor("#333"), 1))
        painter.drawText(2, MT - 4, "0 cm")
        painter.drawLine(x0, MT, x0 + col_w, MT)

        y, cum = MT, 0.0
        for i, layer in enumerate(self._layers):
            lh = max(int((layer["thickness"] / total) * draw_h), 6)
            color = QColor(TEXTURE_COLORS.get(layer.get("texture", "Custom"), "#9E9E9E"))
            
            painter.fillRect(x0, y, col_w, lh, QBrush(color))
            painter.setPen(QPen(QColor("#555"), 1))
            painter.drawRect(x0, y, col_w, lh)
            
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            txt_color = QColor("#fff" if (0.299*color.red() + 0.587*color.green() + 0.114*color.blue()) < 128 else "#111")
            painter.setPen(QPen(txt_color))
            painter.drawText(x0 + 2, y + 2, col_w - 4, lh - 4, Qt.AlignmentFlag.AlignCenter, f"L{i+1}")
            
            y += lh
            cum += layer["thickness"]
            painter.setFont(QFont("Arial", 7))
            painter.setPen(QPen(QColor("#333")))
            painter.drawLine(x0, y, x0 + col_w, y)
            painter.drawText(2, y + 9, f"{cum:.0f}")


class LayerPanel(QGroupBox):
    """Single layer parameters."""
    
    changed = pyqtSignal()

    def __init__(self, index: int, parent=None):
        super().__init__(f"Layer {index + 1}", parent)
        self.index = index
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        
        # Texture + thickness
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Texture:"))
        self.cb_texture = QComboBox()
        self.cb_texture.addItems(list(TEXTURE_COLORS.keys()))
        self.cb_texture.setCurrentText("Loam")
        self.cb_texture.currentTextChanged.connect(self._on_texture_changed)
        r1.addWidget(self.cb_texture, 1)
        
        r1.addWidget(QLabel("Thickness (cm):"))
        self.sp_thick = QDoubleSpinBox()
        self.sp_thick.setRange(1.0, 500.0)
        self.sp_thick.setValue(50.0)
        self.sp_thick.valueChanged.connect(self.changed)
        r1.addWidget(self.sp_thick)
        root.addLayout(r1)
        
        # Model
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Model:"))
        self.cb_model = QComboBox()
        self.cb_model.addItems(["van_genuchten", "brooks_corey"])
        self.cb_model.currentTextChanged.connect(self._on_model_changed)
        r2.addWidget(self.cb_model, 1)
        root.addLayout(r2)
        
        # Tabs
        self.tabs = QTabWidget()
        self._build_vg_tab()
        self._build_bc_tab()
        self._build_solute_tab()
        self._build_thermal_tab()
        root.addWidget(self.tabs)
        
        self._on_model_changed("van_genuchten")

    def _build_vg_tab(self):
        w, g = QWidget(), QGridLayout()
        w.setLayout(g)
        
        params = [
            ("θ_r:", "sp_theta_r", 0.078, 0.001), ("θ_s:", "sp_theta_s", 0.430, 0.001),
            ("α (1/cm):", "sp_alpha", 0.036, 0.001), ("n:", "sp_n", 1.56, 0.01),
            ("Ks (cm/d):", "sp_Ks", 24.96, 0.1), ("l:", "sp_l", 0.5, 0.1),
        ]
        for row, (lbl, attr, val, step) in enumerate(params):
            g.addWidget(QLabel(lbl), row, 0)
            sb = QDoubleSpinBox()
            sb.setRange(0.0, 5000.0)
            sb.setValue(val)
            sb.setSingleStep(step)
            sb.setDecimals(4)
            sb.valueChanged.connect(self.changed)
            setattr(self, attr, sb)
            g.addWidget(sb, row, 1)
        
        self._vg_idx = self.tabs.addTab(w, "van Genuchten")

    def _build_bc_tab(self):
        w, g = QWidget(), QGridLayout()
        w.setLayout(g)
        
        params = [
            ("θ_r:", "sp_bc_theta_r", 0.068, 0.001), ("θ_s:", "sp_bc_theta_s", 0.380, 0.001),
            ("h_b (cm):", "sp_bc_hb", -20.0, 0.5), ("λ:", "sp_bc_lam", 0.220, 0.01),
            ("Ks (cm/d):", "sp_bc_Ks", 10.0, 0.1), ("l:", "sp_bc_l", 2.0, 0.1),
        ]
        for row, (lbl, attr, val, step) in enumerate(params):
            g.addWidget(QLabel(lbl), row, 0)
            sb = QDoubleSpinBox()
            sb.setRange(-500.0, 5000.0)
            sb.setValue(val)
            sb.setSingleStep(step)
            sb.setDecimals(4)
            sb.valueChanged.connect(self.changed)
            setattr(self, attr, sb)
            g.addWidget(sb, row, 1)
        
        self._bc_idx = self.tabs.addTab(w, "Brooks-Corey")

    def _build_solute_tab(self):
        w, g = QWidget(), QGridLayout()
        w.setLayout(g)
        
        params = [
            ("D_L (cm²/d):", "sp_DL", 1.0), ("D_e (cm²/d):", "sp_De", 0.01),
            ("ρ_b (g/cm³):", "sp_rho_b", 1.5), ("K_d (cm³/g):", "sp_Kd", 0.0),
        ]
        for row, (lbl, attr, val) in enumerate(params):
            g.addWidget(QLabel(lbl), row, 0)
            sb = QDoubleSpinBox()
            sb.setRange(0.0, 1000.0)
            sb.setValue(val)
            sb.setDecimals(4)
            sb.valueChanged.connect(self.changed)
            setattr(self, attr, sb)
            g.addWidget(sb, row, 1)
        
        self.tabs.addTab(w, "Solute")

    def _build_thermal_tab(self):
        w, g = QWidget(), QGridLayout()
        w.setLayout(g)
        
        params = [
            ("λ_dry (W/m·K):", "sp_lam_dry", 0.25), ("λ_sat (W/m·K):", "sp_lam_sat", 1.80),
            ("C_s (J/kg·K):", "sp_Cs", 800.0), ("T_init (°C):", "sp_T_init", 20.0),
        ]
        for row, (lbl, attr, val) in enumerate(params):
            g.addWidget(QLabel(lbl), row, 0)
            sb = QDoubleSpinBox()
            sb.setRange(-20.0, 5000.0)
            sb.setValue(val)
            sb.setDecimals(2)
            sb.valueChanged.connect(self.changed)
            setattr(self, attr, sb)
            g.addWidget(sb, row, 1)
        
        self.tabs.addTab(w, "Thermal")

    def _on_texture_changed(self, texture):
        model = self.cb_model.currentText()
        p = VG_PRESETS.get(texture, VG_PRESETS["Custom"]) if model == "van_genuchten" else BC_PRESETS.get(texture, BC_PRESETS["Custom"])
        
        if model == "van_genuchten":
            self.sp_theta_r.setValue(p["theta_r"])
            self.sp_theta_s.setValue(p["theta_s"])
            self.sp_alpha.setValue(p["alpha"])
            self.sp_n.setValue(p["n"])
            self.sp_Ks.setValue(p["Ks"])
        else:
            self.sp_bc_theta_r.setValue(p["theta_r"])
            self.sp_bc_theta_s.setValue(p["theta_s"])
            self.sp_bc_hb.setValue(p["h_b"])
            self.sp_bc_lam.setValue(p["lam"])
            self.sp_bc_Ks.setValue(p["Ks"])
        self.changed.emit()

    def _on_model_changed(self, model):
        vg = model == "van_genuchten"
        self.tabs.setTabVisible(self._vg_idx, vg)
        self.tabs.setTabVisible(self._bc_idx, not vg)
        self.tabs.setCurrentIndex(self._vg_idx if vg else self._bc_idx)
        self.changed.emit()

    def get_data(self) -> dict:
        model = self.cb_model.currentText()
        d = {
            "label": f"L{self.index + 1}",
            "texture": self.cb_texture.currentText(),
            "thickness": self.sp_thick.value(),
            "model": model,
            "DL": self.sp_DL.value(),
            "De": self.sp_De.value(),
            "rho_b": self.sp_rho_b.value(),
            "Kd": self.sp_Kd.value(),
            "lam_dry": self.sp_lam_dry.value(),
            "lam_sat": self.sp_lam_sat.value(),
            "Cs": self.sp_Cs.value(),
            "T_init": self.sp_T_init.value(),
        }
        
        if model == "van_genuchten":
            d.update({
                "theta_r": self.sp_theta_r.value(), "theta_s": self.sp_theta_s.value(),
                "alpha": self.sp_alpha.value(), "n": self.sp_n.value(),
                "Ks": self.sp_Ks.value(), "l": self.sp_l.value(),
            })
        else:
            d.update({
                "theta_r": self.sp_bc_theta_r.value(), "theta_s": self.sp_bc_theta_s.value(),
                "h_b": self.sp_bc_hb.value(), "lam": self.sp_bc_lam.value(),
                "Ks": self.sp_bc_Ks.value(), "l": self.sp_bc_l.value(),
            })
        return d

    def set_data(self, d: dict):
        self.cb_texture.setCurrentText(d.get("texture", "Loam"))
        self.sp_thick.setValue(d.get("thickness", 50.0))
        model = d.get("model", "van_genuchten")
        self.cb_model.setCurrentText(model)
        
        if model == "van_genuchten":
            self.sp_theta_r.setValue(d.get("theta_r", 0.078))
            self.sp_theta_s.setValue(d.get("theta_s", 0.430))
            self.sp_alpha.setValue(d.get("alpha", 0.036))
            self.sp_n.setValue(d.get("n", 1.56))
            self.sp_Ks.setValue(d.get("Ks", 24.96))
            self.sp_l.setValue(d.get("l", 0.5))
        else:
            self.sp_bc_theta_r.setValue(d.get("theta_r", 0.068))
            self.sp_bc_theta_s.setValue(d.get("theta_s", 0.380))
            self.sp_bc_hb.setValue(d.get("h_b", -20.0))
            self.sp_bc_lam.setValue(d.get("lam", 0.220))
            self.sp_bc_Ks.setValue(d.get("Ks", 10.0))
            self.sp_bc_l.setValue(d.get("l", 2.0))
        
        self.sp_DL.setValue(d.get("DL", 1.0))
        self.sp_De.setValue(d.get("De", 0.01))
        self.sp_rho_b.setValue(d.get("rho_b", 1.5))
        self.sp_Kd.setValue(d.get("Kd", 0.0))
        self.sp_lam_dry.setValue(d.get("lam_dry", 0.25))
        self.sp_lam_sat.setValue(d.get("lam_sat", 1.80))
        self.sp_Cs.setValue(d.get("Cs", 800.0))
        self.sp_T_init.setValue(d.get("T_init", 20.0))


class SimSettingsPanel(QGroupBox):
    """Simulation settings."""
    
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Simulation Settings", parent)
        g = QGridLayout(self)
        
        params = [
            ("Nodes/cm:", "sp_nodes_per_cm", 2.0, 0.5),
            ("t_end (day):", "sp_t_end", 30.0, 1.0),
            ("dt_init (day):", "sp_dt_init", 0.01, 0.001),
            ("dt_max (day):", "sp_dt_max", 1.0, 0.1),
            ("Tolerance:", "sp_tol", 1e-4, 1e-5),
            ("Max iter:", "sp_max_iter", 25, 1),
        ]
        
        for row, (lbl, attr, val, step) in enumerate(params):
            g.addWidget(QLabel(lbl), row, 0)
            if attr == "sp_max_iter":
                sb = QSpinBox()
                sb.setRange(5, 200)
                sb.setValue(int(val))
            else:
                sb = QDoubleSpinBox()
                sb.setRange(0.0, 1e6)
                sb.setValue(val)
                sb.setSingleStep(step)
                sb.setDecimals(6)
            sb.valueChanged.connect(self.changed)
            setattr(self, attr, sb)
            g.addWidget(sb, row, 1)

        def get_data(self) -> dict:
            return {
                "nodes_per_cm": self.sp_nodes_per_cm.value(),
                "t_end": self.sp_t_end.value(),
                "dt_init": self.sp_dt_init.value(),
                "dt_max": self.sp_dt_max.value(),
                "tol": self.sp_tol.value(),
                "max_iter": self.sp_max_iter.value(),
            }

    def set_data(self, d: dict):
        self.sp_nodes_per_cm.setValue(d.get("nodes_per_cm", 2.0))
        self.sp_t_end.setValue(d.get("t_end", 30.0))
        self.sp_dt_init.setValue(d.get("dt_init", 0.01))
        self.sp_dt_max.setValue(d.get("dt_max", 1.0))
        self.sp_tol.setValue(d.get("tol", 1e-4))
        self.sp_max_iter.setValue(d.get("max_iter", 25))


###############################################################
class SoilLayerPanel(QWidget):
    changed = pyqtSignal()
    
    def __init__(self, layer_num, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.addWidget(QLabel(f"Layer {layer_num}"), 0, 0, 1, 2)
        
        layout.addWidget(QLabel("thickness (cm):"), 1, 0)
        self.sp_thickness = QDoubleSpinBox()
        self.sp_thickness.setRange(0.1, 10000)
        self.sp_thickness.setValue(10 * layer_num)
        self.sp_thickness.valueChanged.connect(self.changed)
        layout.addWidget(self.sp_thickness, 1, 1)


        layout.addWidget(QLabel("θr:"), 2, 0)
        self.sp_theta_r = QDoubleSpinBox()
        self.sp_theta_r.setRange(0, 1)
        self.sp_theta_r.setValue(0.05)
        self.sp_theta_r.setDecimals(3)
        self.sp_theta_r.valueChanged.connect(self.changed)
        layout.addWidget(self.sp_theta_r, 2, 1)
        
        layout.addWidget(QLabel("θs:"), 3, 0)
        self.sp_theta_s = QDoubleSpinBox()
        self.sp_theta_s.setRange(0, 1)
        self.sp_theta_s.setValue(0.4)
        self.sp_theta_s.setDecimals(3)
        self.sp_theta_s.valueChanged.connect(self.changed)
        layout.addWidget(self.sp_theta_s, 3, 1)
        
        layout.addWidget(QLabel("α (1/cm):"), 4, 0)
        self.sp_alpha = QDoubleSpinBox()
        self.sp_alpha.setRange(0.001, 1)
        self.sp_alpha.setValue(0.02)
        self.sp_alpha.setDecimals(4)
        self.sp_alpha.valueChanged.connect(self.changed)
        layout.addWidget(self.sp_alpha, 4, 1)
        
        layout.addWidget(QLabel("n:"), 5, 0)
        self.sp_n = QDoubleSpinBox()
        self.sp_n.setRange(1, 10)
        self.sp_n.setValue(1.5)
        self.sp_n.setDecimals(3)
        self.sp_n.valueChanged.connect(self.changed)
        layout.addWidget(self.sp_n, 5, 1)
        
        layout.addWidget(QLabel("Ks (cm/d):"), 6, 0)
        self.sp_ks = QDoubleSpinBox()
        self.sp_ks.setRange(0.01, 1000)
        self.sp_ks.setValue(10)
        self.sp_ks.setDecimals(2)
        self.sp_ks.valueChanged.connect(self.changed)
        layout.addWidget(self.sp_ks, 6, 1)

    
    def get_data(self):
        return {
            "thickness": self.sp_thickness.value(),
            "theta_r": self.sp_theta_r.value(),
            "theta_s": self.sp_theta_s.value(),
            "alpha": self.sp_alpha.value(),
            "n": self.sp_n.value(),
            "Ks": self.sp_ks.value()
        }
    
    def set_data(self, d):
        self.sp_thickness.setValue(d.get("thickness", 10))
        self.sp_theta_r.setValue(d.get("theta_r", 0.05))
        self.sp_theta_s.setValue(d.get("theta_s", 0.4))
        self.sp_alpha.setValue(d.get("alpha", 0.02))
        self.sp_n.setValue(d.get("n", 1.5))
        self.sp_ks.setValue(d.get("Ks", 10))






class SoilLayerPanel(QWidget):
    changed = pyqtSignal()
    
    def __init__(self, layer_num, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.addWidget(QLabel(f"Layer {layer_num}"), 0, 0, 1, 2)
        
        layout.addWidget(QLabel("thickness (cm):"), 1, 0)
        self.sp_thickness = QDoubleSpinBox()
        self.sp_thickness.setRange(0.1, 1000)
        self.sp_thickness.setValue(10 * layer_num)
        self.sp_thickness.valueChanged.connect(self.changed)
        layout.addWidget(self.sp_thickness, 1, 1)
        
        layout.addWidget(QLabel("Texture:"), 2, 0)
        self.cb_texture = QComboBox()
        self.cb_texture.addItems(list(TEXTURE_COLORS.keys()))
        self.cb_texture.currentTextChanged.connect(self._on_texture_changed)
        layout.addWidget(self.cb_texture, 2, 1)
        
        layout.addWidget(QLabel("Model:"), 3, 0)
        self.cb_model = QComboBox()
        self.cb_model.addItems(["van_genuchten", "brooks_corey"])
        self.cb_model.currentTextChanged.connect(self._on_model_changed)
        layout.addWidget(self.cb_model, 3, 1)
        
        layout.addWidget(QLabel("θr:"), 4, 0)
        self.sp_theta_r = QDoubleSpinBox()
        self.sp_theta_r.setRange(0, 1)
        self.sp_theta_r.setValue(0.078)
        self.sp_theta_r.setDecimals(3)
        self.sp_theta_r.valueChanged.connect(self.changed)
        layout.addWidget(self.sp_theta_r, 4, 1)
        
        layout.addWidget(QLabel("θs:"), 5, 0)
        self.sp_theta_s = QDoubleSpinBox()
        self.sp_theta_s.setRange(0, 1)
        self.sp_theta_s.setValue(0.43)
        self.sp_theta_s.setDecimals(3)
        self.sp_theta_s.valueChanged.connect(self.changed)
        layout.addWidget(self.sp_theta_s, 5, 1)
        
        layout.addWidget(QLabel("α/h_b:"), 6, 0)
        self.sp_alpha = QDoubleSpinBox()
        self.sp_alpha.setRange(-500, 1)
        self.sp_alpha.setValue(0.036)
        self.sp_alpha.setDecimals(4)
        self.sp_alpha.valueChanged.connect(self.changed)
        layout.addWidget(self.sp_alpha, 6, 1)
        
        layout.addWidget(QLabel("n/λ:"), 7, 0)
        self.sp_n = QDoubleSpinBox()
        self.sp_n.setRange(0.1, 10)
        self.sp_n.setValue(1.56)
        self.sp_n.setDecimals(3)
        self.sp_n.valueChanged.connect(self.changed)
        layout.addWidget(self.sp_n, 7, 1)
        
        layout.addWidget(QLabel("Ks (cm/d):"), 8, 0)
        self.sp_ks = QDoubleSpinBox()
        self.sp_ks.setRange(0.01, 1000)
        self.sp_ks.setValue(24.96)
        self.sp_ks.setDecimals(2)
        self.sp_ks.valueChanged.connect(self.changed)
        layout.addWidget(self.sp_ks, 8, 1)
    
    def _on_texture_changed(self, texture):
        model = self.cb_model.currentText()
        p = VG_PRESETS.get(texture, VG_PRESETS["Loam"]) if model == "van_genuchten" else BC_PRESETS.get(texture, BC_PRESETS["Loam"])
        
        self.sp_theta_r.setValue(p["theta_r"])
        self.sp_theta_s.setValue(p["theta_s"])
        self.sp_ks.setValue(p["Ks"])
        
        if model == "van_genuchten":
            self.sp_alpha.setValue(p["alpha"])
            self.sp_n.setValue(p["n"])
        else:
            self.sp_alpha.setValue(p["h_b"])
            self.sp_n.setValue(p["lam"])
        
        self.changed.emit()
    
    def _on_model_changed(self, model):
        texture = self.cb_texture.currentText()
        self._on_texture_changed(texture)
    
    def get_data(self):
        model = self.cb_model.currentText()
        d = {
            "thickness": self.sp_thickness.value(),
            "texture": self.cb_texture.currentText(),
            "model": model,
            "theta_r": self.sp_theta_r.value(),
            "theta_s": self.sp_theta_s.value(),
            "Ks": self.sp_ks.value()
        }
        
        if model == "van_genuchten":
            d["alpha"] = self.sp_alpha.value()
            d["n"] = self.sp_n.value()
        else:
            d["h_b"] = self.sp_alpha.value()
            d["lam"] = self.sp_n.value()
        
        return d
    
    def set_data(self, d):
        self.sp_thickness.setValue(d.get("thickness", 10))
        self.cb_texture.setCurrentText(d.get("texture", "Loam"))
        model = d.get("model", "van_genuchten")
        self.cb_model.setCurrentText(model)
        self.sp_theta_r.setValue(d.get("theta_r", 0.078))
        self.sp_theta_s.setValue(d.get("theta_s", 0.43))
        self.sp_ks.setValue(d.get("Ks", 24.96))
        
        if model == "van_genuchten":
            self.sp_alpha.setValue(d.get("alpha", 0.036))
            self.sp_n.setValue(d.get("n", 1.56))
        else:
            self.sp_alpha.setValue(d.get("h_b", -20.0))
            self.sp_n.setValue(d.get("lam", 0.22))


class ProfileCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layers = []
        self.setMinimumSize(250, 500)
    
    def update_layers(self, layers):
        self.layers = layers
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.layers:
            return

        y = 10
        width = self.width() - 20
        total_thickness = sum(layer['thickness'] for layer in self.layers)

        for layer in self.layers:
            height = int((layer['thickness'] / total_thickness) * (self.height() - 20))

            texture = layer.get('texture')
            color = QColor(TEXTURE_COLORS.get(texture))
            painter.setBrush(color)
            painter.setPen(Qt.GlobalColor.black)
            painter.drawRect(10, y, width, height)
            painter.drawText(15, y + height//2, f"{layer['thickness']:.1f} cm")
            y += height



class SoilProfileEditor(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Number of Layers:"))
        self.sp_layer_count = QSpinBox()
        self.sp_layer_count.setRange(1, 20)
        self.sp_layer_count.setValue(3)
        self.sp_layer_count.valueChanged.connect(self._update_layer_count)
        count_layout.addWidget(self.sp_layer_count)
        count_layout.addStretch()
        main_layout.addLayout(count_layout)
        
        h_layout = QHBoxLayout()
        
        self.canvas = ProfileCanvas()
        h_layout.addWidget(self.canvas)
    
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        container = QWidget()
        self.layers_layout = QVBoxLayout(container)
        
        self.layer_panels = []
        for i in range(3):
            panel = SoilLayerPanel(i + 1)
            panel.changed.connect(self._update_canvas)
            self.layer_panels.append(panel)
            self.layers_layout.addWidget(panel)
        
        self.layers_layout.addStretch()
        scroll.setWidget(container)
        h_layout.addWidget(scroll, 1)
        
        main_layout.addLayout(h_layout)
        self._update_canvas()

    def _update_canvas(self):
        layers = [p.get_data() for p in self.layer_panels]
        self.canvas.update_layers(layers)
        self.changed.emit()

    def get_layers(self):
        return [p.get_data() for p in self.layer_panels]

    def set_layers(self, layers):
        for i, data in enumerate(layers):
            if i < len(self.layer_panels):
                self.layer_panels[i].set_data(data)
        self._update_canvas()

    def get_data(self):
        return {"layers": self.get_layers()}
    
    def set_data(self, data):
        if "layers" in data:
            self.set_layers(data["layers"])

    def _update_layer_count(self, count):
        current = len(self.layer_panels)

        if count > current:
            for i in range(current, count):
                panel = SoilLayerPanel(i + 1)
                panel.changed.connect(self._update_canvas)
                self.layer_panels.append(panel)
                self.layers_layout.insertWidget(i, panel)
        elif count < current:
            for i in range(count, current):
                panel = self.layer_panels.pop()
                self.layers_layout.removeWidget(panel)
                panel.deleteLater()

        self._update_canvas()
