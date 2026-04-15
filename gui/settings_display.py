from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QPushButton, QDialogButtonBox
)
from PyQt6.QtCore import Qt


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Solver settings
        solver_box = QGroupBox("Solver")
        solver_grid = QGridLayout(solver_box)
        
        solver_grid.addWidget(QLabel("Max Iterations:"), 0, 0)
        self.sp_max_iter = QSpinBox()
        self.sp_max_iter.setRange(10, 1000)
        self.sp_max_iter.setValue(100)
        solver_grid.addWidget(self.sp_max_iter, 0, 1)
        
        solver_grid.addWidget(QLabel("Tolerance:"), 1, 0)
        self.sp_tol = QDoubleSpinBox()
        self.sp_tol.setRange(1e-10, 1e-2)
        self.sp_tol.setDecimals(10)
        self.sp_tol.setValue(1e-6)
        solver_grid.addWidget(self.sp_tol, 1, 1)
        
        layout.addWidget(solver_box)
        
        # Output settings
        output_box = QGroupBox("Output")
        output_grid = QGridLayout(output_box)
        
        output_grid.addWidget(QLabel("Output Directory:"), 0, 0)
        self.le_output_dir = QLineEdit("./output")
        output_grid.addWidget(self.le_output_dir, 0, 1)
        
        output_grid.addWidget(QLabel("Save Interval (d):"), 1, 0)
        self.sp_save_interval = QDoubleSpinBox()
        self.sp_save_interval.setRange(0.1, 100)
        self.sp_save_interval.setValue(1.0)
        output_grid.addWidget(self.sp_save_interval, 1, 1)
        
        self.cb_save_profiles = QCheckBox("Save Profiles")
        self.cb_save_profiles.setChecked(True)
        output_grid.addWidget(self.cb_save_profiles, 2, 0, 1, 2)
        
        layout.addWidget(output_box)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self):
        return {
            "max_iterations": self.sp_max_iter.value(),
            "tolerance": self.sp_tol.value(),
            "output_dir": self.le_output_dir.text(),
            "save_interval": self.sp_save_interval.value(),
            "save_profiles": self.cb_save_profiles.isChecked()
        }

    def set_settings(self, settings):
        self.sp_max_iter.setValue(settings.get("max_iterations", 100))
        self.sp_tol.setValue(settings.get("tolerance", 1e-6))
        self.le_output_dir.setText(settings.get("output_dir", "./output"))
        self.sp_save_interval.setValue(settings.get("save_interval", 1.0))
        self.cb_save_profiles.setChecked(settings.get("save_profiles", True))
