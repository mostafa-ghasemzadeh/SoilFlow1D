import json
from pathlib import Path


class ProjectManager:
    def __init__(self):
        self.current_file = None
        self.modified = False

    def save_project(self, filepath, data):
        """Save project data to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        self.current_file = filepath
        self.modified = False

    def load_project(self, filepath):
        """Load project data from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.current_file = filepath
        self.modified = False
        return data

    def export_to_csv(self, filepath, results):
        """Export results to CSV"""
        import csv
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Time', 'thickness', 'Pressure', 'Theta', 'Flux', 'Concentration'])
            for row in results:
                writer.writerow(row)

    def get_project_name(self):
        """Get current project name"""
        if self.current_file:
            return Path(self.current_file).stem
        return "Untitled"

    def mark_modified(self):
        """Mark project as modified"""
        self.modified = True

    def is_modified(self):
        """Check if project has unsaved changes"""
        return self.modified
