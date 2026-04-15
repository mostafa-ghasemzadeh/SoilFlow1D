from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation


class PlotCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)
        
        self.ax = self.figure.add_subplot(111)
        self.results = None
        self.animation = None
        self.clear()
    
    def clear(self):
        self.ax.clear()
        self.ax.set_xlabel("Value")
        self.ax.set_ylabel("thickness (cm)")
        self.ax.invert_yaxis()
        self.ax.grid(True, alpha=0.3)
        self.canvas.draw()
    
    def plot_results(self, results, plot_type="theta", time_idx=-1):
        self.results = results
        self.ax.clear()
    
        z = results.get("z", [])
        data = results.get(plot_type, [])
    
        if len(data) > 0 and abs(time_idx) <= len(data):  # ← fix here
            values = data[time_idx]
            times = results.get("times", [])
            time_label = f" at t={times[time_idx]:.2f} d" if abs(time_idx) <= len(times) else ""
    
            self.ax.plot(values, z, 'b-', linewidth=2)
    
            labels = {
                "theta": "Water Content",
                "h": "Pressure Head (cm)",
                "conc": "Concentration (mg/cm³)",
                "temp": "Temperature (°C)"
            }
            self.ax.set_xlabel(labels.get(plot_type, "Value"))
            self.ax.set_title(f"{labels.get(plot_type, 'Value')}{time_label}")
    
        self.ax.set_ylabel("thickness (cm)")
        self.ax.invert_yaxis()
        self.ax.grid(True, alpha=0.3)
        self.figure.tight_layout()
        self.canvas.draw()

    
    def show_plot(self, plot_type):
        if self.results:
            self.plot_results(self.results, plot_type=plot_type, time_idx=-1)
    
    def animate(self, results):
        if self.animation:
            self.animation.event_source.stop()
        
        self.results = results
        plot_type = "theta"
        
        z = results.get("z", [])
        data = results.get(plot_type, [[]])
        times = results.get("times", [])
        
        if not data or not times:
            return
        
        self.ax.clear()
        line, = self.ax.plot([], [], 'b-', linewidth=2)
        self.ax.set_xlim(min(data[0]), max(data[0]))
        self.ax.set_ylim(max(z), min(z))
        self.ax.set_xlabel("Water Content")
        self.ax.set_ylabel("thickness (cm)")
        self.ax.grid(True, alpha=0.3)
        
        title = self.ax.text(0.5, 1.05, '', transform=self.ax.transAxes, ha='center')
        def update(frame):
            line.set_data(data[frame], z)
            title.set_text(f"t = {times[frame]:.2f} d")
            return line, title
        
        self.animation = FuncAnimation(
            self.figure, update, frames=len(times),
            interval=200, blit=True, repeat=True
        )
        self.canvas.draw()
