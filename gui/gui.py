import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import re

import cv2
from PIL import Image, ImageTk
import serial
import serial.tools.list_ports


SERIAL_BAUDRATE = 115200

# Przykład: "Received! #12 | Temp: 24.51 | Humidity: 45.22 | Pressure: 1008.33 hPa"
TELEMETRY_REGEX = re.compile(
    r"Received!\s*#(?P<counter>\d+)\s*\|\s*"
    r"Temp:\s*(?P<temp>-?\d+(?:\.\d+)?)\s*\|\s*"
    r"Humidity:\s*(?P<humi>-?\d+(?:\.\d+)?)\s*\|\s*"
    r"Pressure:\s*(?P<pressure>-?\d+(?:\.\d+)?)\s*hPa"
)


class ESP32TelemetryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 Telemetry & Video Stream System")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)

        self.serial_conn = None
        self.video_capture = None

        self.serial_running = False
        self.video_running = False

        self.latest_frame = None

        self.temp_var = tk.StringVar(value="-- °C")
        self.humi_var = tk.StringVar(value="-- %")
        self.pressure_var = tk.StringVar(value="-- hPa")
        self.counter_var = tk.StringVar(value="#--")
        self.serial_status_var = tk.StringVar(value="Serial: disconnected")
        self.video_status_var = tk.StringVar(value="Video: disconnected")

        self.create_widgets()
        self.refresh_serial_ports()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(
            main,
            text="ESP32 Telemetry & Video Stream System",
            font=("Segoe UI", 20, "bold")
        )
        title.pack(anchor="w", pady=(0, 10))

        controls = ttk.LabelFrame(main, text="Connection settings", padding=10)
        controls.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(controls, text="Receiver COM port:").grid(row=0, column=0, sticky="w", padx=5, pady=5)

        self.port_combo = ttk.Combobox(controls, width=18, state="readonly")
        self.port_combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Button(
            controls,
            text="Refresh ports",
            command=self.refresh_serial_ports
        ).grid(row=0, column=2, sticky="w", padx=5, pady=5)

        self.serial_button = ttk.Button(
            controls,
            text="Connect Serial",
            command=self.toggle_serial
        )
        self.serial_button.grid(row=0, column=3, sticky="w", padx=5, pady=5)

        ttk.Label(controls, text="ESP32 video URL:").grid(row=1, column=0, sticky="w", padx=5, pady=5)

        self.video_url_entry = ttk.Entry(controls, width=35)
        self.video_url_entry.insert(0, "http://192.168.1.100/")
        self.video_url_entry.grid(row=1, column=1, columnspan=2, sticky="we", padx=5, pady=5)

        self.video_button = ttk.Button(
            controls,
            text="Connect Video",
            command=self.toggle_video
        )
        self.video_button.grid(row=1, column=3, sticky="w", padx=5, pady=5)

        controls.columnconfigure(2, weight=1)

        status_frame = ttk.Frame(main)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(status_frame, textvariable=self.serial_status_var).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(status_frame, textvariable=self.video_status_var).pack(side=tk.LEFT)

        content = ttk.Frame(main)
        content.pack(fill=tk.BOTH, expand=True)

        video_frame = ttk.LabelFrame(content, text="Live video stream", padding=10)
        video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.video_label = ttk.Label(video_frame, text="No video", anchor="center")
        self.video_label.pack(fill=tk.BOTH, expand=True)

        telemetry_frame = ttk.LabelFrame(content, text="Telemetry", padding=15)
        telemetry_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self.create_telemetry_card(telemetry_frame, "Temperature", self.temp_var)
        self.create_telemetry_card(telemetry_frame, "Humidity", self.humi_var)
        self.create_telemetry_card(telemetry_frame, "Pressure", self.pressure_var)
        self.create_telemetry_card(telemetry_frame, "Packet counter", self.counter_var)

        log_frame = ttk.LabelFrame(main, text="Serial log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))

        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text.configure(yscrollcommand=scrollbar.set)

    def create_telemetry_card(self, parent, title, variable):
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill=tk.X, pady=8)

        label = ttk.Label(frame, text=title, font=("Segoe UI", 11))
        label.pack(anchor="w")

        value = ttk.Label(frame, textvariable=variable, font=("Segoe UI", 22, "bold"))
        value.pack(anchor="w")

    def refresh_serial_ports(self):
        ports = list(serial.tools.list_ports.comports())
        port_names = [port.device for port in ports]

        self.port_combo["values"] = port_names

        if port_names:
            self.port_combo.current(0)
        else:
            self.port_combo.set("")

    def toggle_serial(self):
        if self.serial_running:
            self.stop_serial()
        else:
            self.start_serial()

    def start_serial(self):
        port = self.port_combo.get()

        if not port:
            messagebox.showerror("Serial error", "Select receiver COM port first.")
            return

        try:
            self.serial_conn = serial.Serial(port, SERIAL_BAUDRATE, timeout=1)
            time.sleep(2)

            self.serial_running = True
            self.serial_button.configure(text="Disconnect Serial")
            self.serial_status_var.set(f"Serial: connected to {port}")

            thread = threading.Thread(target=self.serial_worker, daemon=True)
            thread.start()

            thread = threading.Thread(target=self.serial_worker_sim, daemon=True)
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Serial error", str(e))
            self.serial_status_var.set("Serial: connection failed")

    def stop_serial(self):
        self.serial_running = False
        self.serial_button.configure(text="Connect Serial")
        self.serial_status_var.set("Serial: disconnected")

        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
        except Exception:
            pass

        self.serial_conn = None

    def serial_worker(self):
        while self.serial_running:
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    line = self.serial_conn.readline().decode(errors="ignore").strip()

                    if line:
                        self.root.after(0, self.add_log, line)
                        self.parse_telemetry(line)

            except Exception as e:
                self.root.after(0, self.add_log, f"Serial error: {e}")
                self.root.after(0, self.stop_serial)
                break
    import random
    import time

    def serial_worker_sim(self):
            counter = 0
            while self.serial_running:
                counter += 1
                temp = random.uniform(20, 30)      # przykładowa temperatura
                humi = random.uniform(40, 60)      # wilgotność
                pressure = random.uniform(990, 1020)  # ciśnienie hPa
                line = f"Received! #{counter} | Temp: {temp:.2f} | Humidity: {humi:.2f} | Pressure: {pressure:.2f} hPa"
        
                self.root.after(0, self.add_log, line)
                self.parse_telemetry(line)
                time.sleep(2)

    def parse_telemetry(self, line):
        match = TELEMETRY_REGEX.search(line)

        if not match:
            return

        temp = float(match.group("temp"))
        humi = float(match.group("humi"))
        pressure = float(match.group("pressure"))
        counter = int(match.group("counter"))

        self.root.after(0, self.update_telemetry, temp, humi, pressure, counter)

    def update_telemetry(self, temp, humi, pressure, counter):
        self.temp_var.set(f"{temp:.2f} °C")
        self.humi_var.set(f"{humi:.2f} %")
        self.pressure_var.set(f"{pressure:.2f} hPa")
        self.counter_var.set(f"#{counter}")

    def add_log(self, text):
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def toggle_video(self):
        if self.video_running:
            self.stop_video()
        else:
            self.start_video()

    def start_video(self):
        url = self.video_url_entry.get().strip()

        if not url:
            messagebox.showerror("Video error", "Enter ESP32 video URL first.")
            return

        self.video_running = True
        self.video_button.configure(text="Disconnect Video")
        self.video_status_var.set(f"Video: connecting to {url}")

        thread = threading.Thread(target=self.video_worker, args=(url,), daemon=True)
        thread.start()

    def stop_video(self):
        self.video_running = False
        self.video_button.configure(text="Connect Video")
        self.video_status_var.set("Video: disconnected")

        try:
            if self.video_capture:
                self.video_capture.release()
        except Exception:
            pass

        self.video_capture = None
        self.video_label.configure(image="", text="No video")

    def video_worker(self, url):
        try:
            self.video_capture = cv2.VideoCapture(url)

            if not self.video_capture.isOpened():
                self.root.after(0, self.video_status_var.set, "Video: connection failed")
                self.root.after(0, self.stop_video)
                return

            self.root.after(0, self.video_status_var.set, "Video: connected")

            while self.video_running:
                ret, frame = self.video_capture.read()

                if not ret:
                    time.sleep(0.1)
                    continue

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                label_width = max(self.video_label.winfo_width(), 640)
                label_height = max(self.video_label.winfo_height(), 480)

                frame_height, frame_width, _ = frame.shape
                scale = min(label_width / frame_width, label_height / frame_height)

                new_width = int(frame_width * scale)
                new_height = int(frame_height * scale)

                frame = cv2.resize(frame, (new_width, new_height))

                image = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(image=image)

                self.root.after(0, self.update_video_frame, photo)

        except Exception as e:
            self.root.after(0, self.video_status_var.set, f"Video error: {e}")
            self.root.after(0, self.stop_video)

    def update_video_frame(self, photo):
        self.latest_frame = photo
        self.video_label.configure(image=self.latest_frame, text="")

    def on_close(self):
        self.stop_serial()
        self.stop_video()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ESP32TelemetryGUI(root)
    root.mainloop()