import tkinter as tk

from gui import ESP32TelemetryGUI


if __name__ == "__main__":
    root = tk.Tk()
    app = ESP32TelemetryGUI(root)
    root.mainloop()
