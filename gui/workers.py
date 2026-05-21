import threading
import time
import queue
import urllib.request
import numpy as np

import cv2
import serial


class SerialReceiver:
    def __init__(self, baudrate, line_callback, error_callback=None):
        self.baudrate = baudrate
        self.line_callback = line_callback
        self.error_callback = error_callback

        self.serial_conn = None
        self.running = False
        self.thread = None

    def start(self, port):
        if self.running:
            return

        self.serial_conn = serial.Serial(port, self.baudrate, timeout=1)
        time.sleep(2)

        self.running = True
        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
        except Exception:
            pass

        self.serial_conn = None

    def worker(self):
        while self.running:
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    line = self.serial_conn.readline().decode(errors="ignore").strip()

                    if line:
                        self.line_callback(line)

            except Exception as e:
                if self.error_callback:
                    self.error_callback(f"Serial error: {e}")
                break


class TelemetryLogger:
    def __init__(self, file_name, error_callback=None):
        self.file_name = file_name
        self.error_callback = error_callback

        self.running = False
        self.queue = queue.Queue()
        self.thread = None

    def start(self):
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.running:
            return

        self.running = False
        self.queue.put(None)

    def put(self, data):
        self.queue.put(data)

    def create_file_if_needed(self):
        try:
            with open(self.file_name, "x", encoding="utf-8-sig") as file:
                file.write(
                    f"{'timestamp':<22}"
                    f"{'packet_counter':<18}"
                    f"{'temperature_C':<18}"
                    f"{'humidity_percent':<20}"
                    f"{'pressure_hPa':<15}\n"
                )
                file.write("-" * 93 + "\n")
        except FileExistsError:
            pass

    def worker(self):
        try:
            self.create_file_if_needed()

            while self.running:
                try:
                    data = self.queue.get(timeout=1)

                    if data is None:
                        break

                    line = (
                        f"{data['timestamp']:<22}"
                        f"{data['counter']:<18}"
                        f"{data['temp']:<18.2f}"
                        f"{data['humi']:<20.2f}"
                        f"{data['pressure']:<15.2f}\n"
                    )

                    with open(self.file_name, "a", encoding="utf-8-sig") as file:
                        file.write(line)

                except queue.Empty:
                    continue

        except Exception as e:
            if self.error_callback:
                self.error_callback(f"Logger error: {e}")


class VideoReceiver:
    def __init__(self, frame_callback, status_callback=None, error_callback=None):
        self.frame_callback = frame_callback
        self.status_callback = status_callback
        self.error_callback = error_callback

        self.stream = None
        self.running = False
        self.thread = None

    def start(self, url):
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self.worker, args=(url,), daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        
        try:
            if self.stream:
                self.stream.close()
        except Exception:
            pass
            
        self.stream = None

    def worker(self, url):
        try:
            if self.status_callback:
                self.status_callback(f"Video: connecting to {url}")

            self.stream = urllib.request.urlopen(url, timeout=5)
            bytes_data = b''

            if self.status_callback:
                self.status_callback("Video: connected")

            while self.running:
                chunk = self.stream.read(16384)
                if not chunk:
                    break
                    
                bytes_data += chunk
                latest_frame = None
                
                while True:
                    a = bytes_data.find(b'\xff\xd8')
                    b = bytes_data.find(b'\xff\xd9')
                    
                    if a != -1 and b != -1:
                        if a < b:
                            jpg = bytes_data[a:b+2]
                            bytes_data = bytes_data[b+2:]
                            
                            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                            if frame is not None:
                                latest_frame = frame
                        else:
                            bytes_data = bytes_data[a:]
                    else:
                        break
                        
                if latest_frame is not None:
                    latest_frame = cv2.cvtColor(latest_frame, cv2.COLOR_BGR2RGB)
                    self.frame_callback(latest_frame)
                    
                if len(bytes_data) > 524288:
                    bytes_data = b''

        except Exception as e:
            if self.running and self.error_callback:
                self.error_callback(f"Video error: {e}")
            if self.status_callback:
                self.status_callback("Video: error occurred")
            self.stop()