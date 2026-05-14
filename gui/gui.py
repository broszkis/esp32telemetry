import tkinter as tk

window = tk.Tk()
window.title("ESP32 Telemetry & Video System")
window.geometry("800x600")

label = tk.Label(window, text="Waiting for data...", font=("Arial", 16))
label.pack(pady=20)

window.mainloop()