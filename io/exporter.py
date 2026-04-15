import csv
import json
from pathlib import Path
import numpy as np


class DataExporter:
    @staticmethod
    def export_csv(filepath, data):
        """Export simulation results to CSV"""
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['Time (d)', 'thickness (cm)', 'Pressure (cm)', 
                           'Water Content', 'Flux (cm/d)', 'Concentration (mg/L)'])
            
            # Data
            times = data.get('times', [])
            thickness = data.get('thickness', [])
            
            for t_idx, t in enumerate(times):
                for d_idx, d in enumerate(thickness):
                    row = [
                        t,
                        d,
                        data.get('pressure', [[]])[t_idx][d_idx] if t_idx < len(data.get('pressure', [])) else 0,
                        data.get('theta', [[]])[t_idx][d_idx] if t_idx < len(data.get('theta', [])) else 0,
                        data.get('flux', [[]])[t_idx][d_idx] if t_idx < len(data.get('flux', [])) else 0,
                        data.get('conc', [[]])[t_idx][d_idx] if t_idx < len(data.get('conc', [])) else 0
                    ]
                    writer.writerow(row)

    @staticmethod
    def export_json(filepath, data):
        """Export simulation results to JSON"""
        # Convert numpy arrays to lists
        export_data = {}
        for key, value in data.items():
            if isinstance(value, np.ndarray):
                export_data[key] = value.tolist()
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], np.ndarray):
                export_data[key] = [v.tolist() for v in value]
            else:
                export_data[key] = value
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)

    @staticmethod
    def export_profile(filepath, thickness, values, time, variable_name):
        """Export single profile to CSV"""
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['thickness (cm)', f'{variable_name} at t={time} d'])
            for d, v in zip(thickness, values):
                writer.writerow([d, v])
