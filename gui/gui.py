import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

import serial.tools.list_ports
from PIL import Image, ImageTk

from config import (
    DEFAULT_VIDEO_URL,
    LOG_FILE_NAME,
    SAVE_EVERY_N_PACKETS,
    SERIAL_BAUDRATE,
)
from telemetry_utils import parse_telemetry_line

from workers.serial_receiver import SerialReceiver
from workers.telemetry_logger import TelemetryLogger
from workers.statistics_worker import StatisticsWorker
from workers.video_receiver import VideoReceiver


class ESP32TelemetryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 Telemetry & Video Stream System")
        self.root.geometry("1250x800")
        self.root.minsize(1000, 650)

        self.serial_receiver = None
        self.video_receiver = None

        self.logger = TelemetryLogger(
            file_name=LOG_FILE_NAME,
            error_callback=self.thread_safe_log,
        )
        self.statistics_worker = StatisticsWorker(
            statistics_callback=self.thread_safe_statistics_received,
            error_callback=self.thread_safe_log,
        )

        self.received_packet_count = 0
        self.latest_frame = None

        self.temp_var = tk.StringVar(value="-- °C")
        self.humi_var = tk.StringVar(value="-- %")
        self.pressure_var = tk.StringVar(value="-- hPa")
        self.counter_var = tk.StringVar(value="#--")

        self.avg_temp_var = tk.StringVar(value="-- °C")
        self.avg_humi_var = tk.StringVar(value="-- %")
        self.avg_pressure_var = tk.StringVar(value="-- hPa")
        self.measurements_var = tk.StringVar(value="0")

        self.serial_status_var = tk.StringVar(value="Serial: disconnected")
        self.video_status_var = tk.StringVar(value="Video: disconnected")
        self.logging_status_var = tk.StringVar(value="Logging: stopped")
        self.statistics_status_var = tk.StringVar(value="Statistics: stopped")

        self.create_widgets()
        self.refresh_serial_ports()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------
    # GUI LAYOUT
    # ------------------------------------------------------------

    def create_widgets(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Tylko część środkowa zmienia wysokość. Log pozostaje zawsze na dole.
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1, minsize=0)

        title = ttk.Label(
            main,
            text="ESP32 Telemetry & Video Stream System",
            font=("Segoe UI", 20, "bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 10))

        controls = ttk.LabelFrame(main, text="Connection settings", padding=10)
        controls.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(controls, text="Receiver COM port:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )

        self.port_combo = ttk.Combobox(controls, width=18, state="readonly")
        self.port_combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Button(
            controls, text="Refresh ports", command=self.refresh_serial_ports
        ).grid(row=0, column=2, sticky="w", padx=5, pady=5)

        self.serial_button = ttk.Button(
            controls, text="Connect Serial", command=self.toggle_serial
        )
        self.serial_button.grid(row=0, column=3, sticky="w", padx=5, pady=5)

        ttk.Label(controls, text="ESP32 video URL:").grid(
            row=1, column=0, sticky="w", padx=5, pady=5
        )

        self.video_url_entry = ttk.Entry(controls, width=42)
        self.video_url_entry.insert(0, DEFAULT_VIDEO_URL)
        self.video_url_entry.grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=5, pady=5
        )

        self.video_button = ttk.Button(
            controls, text="Connect Video", command=self.toggle_video
        )
        self.video_button.grid(row=1, column=3, sticky="w", padx=5, pady=5)
        controls.columnconfigure(2, weight=1)

        status_frame = ttk.Frame(main)
        status_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(status_frame, textvariable=self.serial_status_var).pack(
            side=tk.LEFT, padx=(0, 18)
        )
        ttk.Label(status_frame, textvariable=self.video_status_var).pack(
            side=tk.LEFT, padx=(0, 18)
        )
        ttk.Label(status_frame, textvariable=self.logging_status_var).pack(
            side=tk.LEFT, padx=(0, 18)
        )
        ttk.Label(status_frame, textvariable=self.statistics_status_var).pack(
            side=tk.LEFT
        )

        content = ttk.Frame(main)
        content.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        video_frame = ttk.LabelFrame(content, text="Live video stream", padding=10)
        video_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.video_label = ttk.Label(video_frame, text="No video", anchor="center")
        self.video_label.pack(fill=tk.BOTH, expand=True)

        right_panel = ttk.Frame(content)
        right_panel.grid(row=0, column=1, sticky="ns")

        current_frame = ttk.LabelFrame(right_panel, text="Current telemetry", padding=8)
        current_frame.pack(fill=tk.X, pady=(0, 8))

        self.create_telemetry_card(current_frame, "Temperature", self.temp_var)
        self.create_telemetry_card(current_frame, "Humidity", self.humi_var)
        self.create_telemetry_card(current_frame, "Pressure", self.pressure_var)
        self.create_telemetry_card(current_frame, "Packet counter", self.counter_var)

        avg_frame = ttk.LabelFrame(right_panel, text="Average values", padding=8)
        avg_frame.pack(fill=tk.X)

        self.create_telemetry_card(avg_frame, "Average temperature", self.avg_temp_var)
        self.create_telemetry_card(avg_frame, "Average humidity", self.avg_humi_var)
        self.create_telemetry_card(avg_frame, "Average pressure", self.avg_pressure_var)
        self.create_telemetry_card(avg_frame, "Measurements", self.measurements_var)

        log_frame = ttk.LabelFrame(main, text="Serial log", padding=10)
        log_frame.grid(row=4, column=0, sticky="ew")

        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def create_telemetry_card(self, parent, title, variable):
        frame = ttk.Frame(parent, padding=(6, 2))
        frame.pack(fill=tk.X, pady=1)

        ttk.Label(frame, text=title, font=("Segoe UI", 9)).pack(anchor="w")
        ttk.Label(
            frame, textvariable=variable, font=("Segoe UI", 14, "bold")
        ).pack(anchor="w")

    # ------------------------------------------------------------
    # CALLBACKS FROM WORKER THREADS
    # ------------------------------------------------------------

    def thread_safe_log(self, text):
        self.root.after(0, self.add_log, text)

    def thread_safe_video_status(self, text):
        self.root.after(0, self.video_status_var.set, text)

    def thread_safe_line_received(self, line):
        self.root.after(0, self.handle_telemetry_line, line)

    def thread_safe_frame_received(self, frame):
        self.root.after(0, self.update_video_frame, frame)

    def thread_safe_statistics_received(self, statistics):
        self.root.after(0, self.update_statistics, statistics)

    # ------------------------------------------------------------
    # SERIAL
    # ------------------------------------------------------------

    def refresh_serial_ports(self):
        port_names = [
            port.device for port in serial.tools.list_ports.comports()
        ]
        self.port_combo["values"] = port_names

        if port_names:
            self.port_combo.current(0)
        else:
            self.port_combo.set("")

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
                error_callback=self.thread_safe_log,
            )

            self.received_packet_count = 0
            self.reset_displayed_statistics()

            self.serial_receiver.start(port)
            self.logger.start()
            self.statistics_worker.start()

            self.serial_button.configure(text="Disconnect Serial")
            self.serial_status_var.set(f"Serial: connected to {port}")
            self.logging_status_var.set(
                f"Logging: active, every {SAVE_EVERY_N_PACKETS} packets"
            )
            self.statistics_status_var.set("Statistics: active")

        except Exception as exc:
            messagebox.showerror("Serial error", str(exc))
            self.serial_status_var.set("Serial: connection failed")

    def stop_serial(self):
        if self.serial_receiver:
            self.serial_receiver.stop()

        self.logger.stop()
        self.statistics_worker.stop()

        self.serial_button.configure(text="Connect Serial")
        self.serial_status_var.set("Serial: disconnected")
        self.logging_status_var.set("Logging: stopped")
        self.statistics_status_var.set("Statistics: stopped")

    # ------------------------------------------------------------
    # TELEMETRY PROCESSING
    # ------------------------------------------------------------

    def handle_telemetry_line(self, line):
        self.add_log(line)
        data = parse_telemetry_line(line)

        self.update_telemetry(
            data["temp"],
            data["humi"],
            data["pressure"],
            data["counter"],
        )

        if any(data[key] is None for key in ("temp", "humi", "pressure")):
            return

        self.received_packet_count += 1

        self.statistics_worker.put({
            "temp": data["temp"],
            "humi": data["humi"],
            "pressure": data["pressure"],
        })

        if self.received_packet_count % SAVE_EVERY_N_PACKETS == 0:
            log_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "counter": (
                    data["counter"]
                    if data["counter"] is not None
                    else self.received_packet_count
                ),
                "temp": data["temp"],
                "humi": data["humi"],
                "pressure": data["pressure"],
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

    def update_statistics(self, statistics):
        self.avg_temp_var.set(f"{statistics['avg_temp']:.2f} °C")
        self.avg_humi_var.set(f"{statistics['avg_humi']:.2f} %")
        self.avg_pressure_var.set(f"{statistics['avg_pressure']:.2f} hPa")
        self.measurements_var.set(str(statistics["count"]))

    def reset_displayed_statistics(self):
        self.avg_temp_var.set("-- °C")
        self.avg_humi_var.set("-- %")
        self.avg_pressure_var.set("-- hPa")
        self.measurements_var.set("0")

    def add_log(self, text):
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

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
            error_callback=self.thread_safe_log,
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
        label_width = self.video_label.winfo_width()
        label_height = self.video_label.winfo_height()

        # Przy pierwszym renderowaniu widget może jeszcze nie mieć wymiarów.
        if label_width <= 1:
            label_width = 640
        if label_height <= 1:
            label_height = 360

        frame_height, frame_width, _ = frame.shape
        scale = min(label_width / frame_width, label_height / frame_height)

        new_width = max(1, int(frame_width * scale))
        new_height = max(1, int(frame_height * scale))

        image = Image.fromarray(frame).resize((new_width, new_height))
        photo = ImageTk.PhotoImage(image=image)

        self.latest_frame = photo
        self.video_label.configure(image=self.latest_frame, text="")

    # ------------------------------------------------------------
    # CLOSING
    # ------------------------------------------------------------

    def on_close(self):
        self.stop_serial()
        self.stop_video()
        self.root.destroy()
