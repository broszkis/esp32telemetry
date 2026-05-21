import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import serial.tools.list_ports
from PIL import Image, ImageTk

from config import (
    SERIAL_BAUDRATE,
    LOG_FILE_NAME,
    SAVE_EVERY_N_PACKETS,
    DEFAULT_VIDEO_URL
)
from telemetry_utils import parse_telemetry_line
from workers import SerialReceiver, TelemetryLogger, VideoReceiver

class ESP32TelemetryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 Telemetry & Video Stream System")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)

        self.serial_receiver = None
        self.video_receiver = None

        self.logger = TelemetryLogger(
            file_name=LOG_FILE_NAME,
            error_callback=self.thread_safe_log
        )

        self.received_packet_count = 0
        self.latest_frame = None

        self.temp_var = tk.StringVar(value="-- °C")
        self.humi_var = tk.StringVar(value="-- %")
        self.pressure_var = tk.StringVar(value="-- hPa")
        self.counter_var = tk.StringVar(value="#--")

        self.serial_status_var = tk.StringVar(value="Serial: disconnected")
        self.video_status_var = tk.StringVar(value="Video: disconnected")
        self.logging_status_var = tk.StringVar(value="Logging: stopped")

        self.create_widgets()
        self.refresh_serial_ports()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------
    # GUI
    # ------------------------------------------------------------

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

        ttk.Label(controls, text="Receiver COM port:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )

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

        ttk.Label(controls, text="ESP32 video URL:").grid(
            row=1, column=0, sticky="w", padx=5, pady=5
        )

        self.video_url_entry = ttk.Entry(controls, width=35)
        self.video_url_entry.insert(0, DEFAULT_VIDEO_URL)
        self.video_url_entry.grid(
            row=1, column=1, columnspan=2, sticky="we", padx=5, pady=5
        )

        self.video_button = ttk.Button(
            controls,
            text="Connect Video",
            command=self.toggle_video
        )
        self.video_button.grid(row=1, column=3, sticky="w", padx=5, pady=5)

        controls.columnconfigure(2, weight=1)

        status_frame = ttk.Frame(main)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(status_frame, textvariable=self.serial_status_var).pack(
            side=tk.LEFT, padx=(0, 20)
        )
        ttk.Label(status_frame, textvariable=self.video_status_var).pack(
            side=tk.LEFT, padx=(0, 20)
        )
        ttk.Label(status_frame, textvariable=self.logging_status_var).pack(
            side=tk.LEFT
        )

        content = ttk.Frame(main)
        content.pack(fill=tk.BOTH, expand=True)

        video_frame = ttk.LabelFrame(content, text="Live video stream", padding=10)
        video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.video_label = ttk.Label(video_frame, text="No video", anchor="center", width=90)
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

    # ------------------------------------------------------------
    # THREAD-SAFE CALLBACKS
    # ------------------------------------------------------------

    def thread_safe_log(self, text):
        self.root.after(0, self.add_log, text)

    def thread_safe_video_status(self, text):
        self.root.after(0, self.video_status_var.set, text)

    def thread_safe_line_received(self, line):
        self.root.after(0, self.handle_telemetry_line, line)

    def thread_safe_frame_received(self, frame):
        self.root.after(0, self.update_video_frame, frame)

    # ------------------------------------------------------------
    # SERIAL PORTS
    # ------------------------------------------------------------

    def refresh_serial_ports(self):
        ports = list(serial.tools.list_ports.comports())
        port_names = [port.device for port in ports]

        self.port_combo["values"] = port_names

        if port_names:
            self.port_combo.current(0)
        else:
            self.port_combo.set("")

    # ------------------------------------------------------------
    # SERIAL
    # ------------------------------------------------------------

    def toggle_serial(self):
        if self.serial_receiver and self.serial_receiver.running:
            self.stop_serial()
        else:
            self.start_serial()

    def start_serial(self):
        port = self.port_combo.get()

        if not port:
            messagebox.showerror("Serial error", "Select receiver COM port first.")
            return

        try:
            self.serial_receiver = SerialReceiver(
                baudrate=SERIAL_BAUDRATE,
                line_callback=self.thread_safe_line_received,
                error_callback=self.thread_safe_log
            )

            self.serial_receiver.start(port)

            self.start_logger()

            self.serial_button.configure(text="Disconnect Serial")
            self.serial_status_var.set(f"Serial: connected to {port}")

        except Exception as e:
            messagebox.showerror("Serial error", str(e))
            self.serial_status_var.set("Serial: connection failed")

    def stop_serial(self):
        if self.serial_receiver:
            self.serial_receiver.stop()

        self.serial_button.configure(text="Connect Serial")
        self.serial_status_var.set("Serial: disconnected")
        self.stop_logger()

    # ------------------------------------------------------------
    # TELEMETRY
    # ------------------------------------------------------------

    def handle_telemetry_line(self, line):
        self.add_log(line)

        data = parse_telemetry_line(line)

        self.update_telemetry(
            data["temp"],
            data["humi"],
            data["pressure"],
            data["counter"]
        )

        if data["temp"] is None or data["humi"] is None or data["pressure"] is None:
            return

        self.received_packet_count += 1

        if self.received_packet_count % SAVE_EVERY_N_PACKETS == 0:
            log_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "counter": data["counter"] if data["counter"] is not None else self.received_packet_count,
                "temp": data["temp"],
                "humi": data["humi"],
                "pressure": data["pressure"]
            }

            self.logger.put(log_data)
            self.add_log(f"Saved packet #{log_data['counter']} to {LOG_FILE_NAME}")

    def update_telemetry(self, temp, humi, pressure, counter):
        if temp is not None:
            self.temp_var.set(f"{temp:.2f} °C")

        if humi is not None:
            self.humi_var.set(f"{humi:.2f} %")

        if pressure is not None:
            self.pressure_var.set(f"{pressure:.2f} hPa")

        if counter is not None:
            self.counter_var.set(f"#{counter}")

    def add_log(self, text):
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    # ------------------------------------------------------------
    # LOGGER
    # ------------------------------------------------------------

    def start_logger(self):
        self.logger.start()
        self.logging_status_var.set(f"Logging: active, every {SAVE_EVERY_N_PACKETS} packets")

    def stop_logger(self):
        self.logger.stop()
        self.logging_status_var.set("Logging: stopped")

    # ------------------------------------------------------------
    # VIDEO
    # ------------------------------------------------------------

    def toggle_video(self):
        if self.video_receiver and self.video_receiver.running:
            self.stop_video()
        else:
            self.start_video()

    def start_video(self):
        url = self.video_url_entry.get().strip()

        if not url:
            messagebox.showerror("Video error", "Enter ESP32 video URL first.")
            return

        self.video_receiver = VideoReceiver(
            frame_callback=self.thread_safe_frame_received,
            status_callback=self.thread_safe_video_status,
            error_callback=self.thread_safe_log
        )

        self.video_receiver.start(url)

        self.video_button.configure(text="Disconnect Video")

    def stop_video(self):
        if self.video_receiver:
            self.video_receiver.stop()

        self.video_button.configure(text="Connect Video")
        self.video_status_var.set("Video: disconnected")
        self.video_label.configure(image="", text="No video")

    def update_video_frame(self, frame):
        target_width = 640
        target_height = 480

        frame_height, frame_width, _ = frame.shape

        scale = min(
            target_width / frame_width,
            target_height / frame_height
        )

        new_width = int(frame_width * scale)
        new_height = int(frame_height * scale)

        image = Image.fromarray(frame)
        image = image.resize((new_width, new_height))

        photo = ImageTk.PhotoImage(image=image)

        self.latest_frame = photo
        self.video_label.configure(image=self.latest_frame, text="")

    # ------------------------------------------------------------
    # CLOSE
    # ------------------------------------------------------------

    def on_close(self):
        self.stop_serial()
        self.stop_logger()
        self.stop_video()
        self.root.destroy()
