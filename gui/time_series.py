from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog
)
from PyQt6.QtCore import pyqtSignal
import json


class TimeSeriesPanel(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Time (d)", "Precip (cm/d)", "Evap (cm/d)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self.changed)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_add = QPushButton("Add Row")
        btn_add.clicked.connect(self._add_row)
        btn_layout.addWidget(btn_add)
        
        btn_remove = QPushButton("Remove Row")
        btn_remove.clicked.connect(self._remove_row)
        btn_layout.addWidget(btn_remove)
        
        btn_import = QPushButton("Import CSV")
        btn_import.clicked.connect(self._import_csv)
        btn_layout.addWidget(btn_import)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Add initial row
        self._add_row()

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem("0.0"))
        self.table.setItem(row, 1, QTableWidgetItem("0.5"))
        self.table.setItem(row, 2, QTableWidgetItem("0.3"))
        self.changed.emit()

    def _remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.changed.emit()

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        
        try:
            with open(path, 'r') as f:
                lines = f.readlines()[1:]  # Skip header
                self.table.setRowCount(0)
                for line in lines:
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        row = self.table.rowCount()
                        self.table.insertRow(row)
                        self.table.setItem(row, 0, QTableWidgetItem(parts[0]))
                        self.table.setItem(row, 1, QTableWidgetItem(parts[1]))
                        self.table.setItem(row, 2, QTableWidgetItem(parts[2]))
                        self.changed.emit()
        except Exception as e:
            print(f"Import error: {e}")

    def get_data(self):
        data = []
        for row in range(self.table.rowCount()):
            try:
                t = float(self.table.item(row, 0).text())
                p = float(self.table.item(row, 1).text())
                e = float(self.table.item(row, 2).text())
                data.append({"time": t, "precip": p, "evap": e})
            except:
                pass
        return data

    def set_data(self, data):
        self.table.setRowCount(0)
        for item in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(item.get("time", 0))))
            self.table.setItem(row, 1, QTableWidgetItem(str(item.get("precip", 0))))
            self.table.setItem(row, 2, QTableWidgetItem(str(item.get("evap", 0))))
