import threading
import time
from collections.abc import Callable

import serial

##watek odbiera linie tekstowe z porty COM podlaczeonego esp
class SerialReceiver:

    def __init__(
        self,
        baudrate: int,
        line_callback: Callable[[str], None],
        error_callback: Callable[[str], None] | None = None,
    ):
        self.baudrate = baudrate
        self.line_callback = line_callback
        self.error_callback = error_callback

        self.serial_conn: serial.Serial | None = None
        self.running = False
        self.thread: threading.Thread | None = None

    def start(self, port: str) -> None:
        if self.running:
            return

        self.serial_conn = serial.Serial(port, self.baudrate, timeout=1)
        time.sleep(2)  # ESP32 może zresetować się po otwarciu portu COM.

        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False

        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
        except Exception:
            pass

        self.serial_conn = None

    def _worker(self) -> None:
        while self.running:
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    line = self.serial_conn.readline().decode(errors="ignore").strip()
                    if line:
                        self.line_callback(line)
            except Exception as exc:
                self.running = False
                if self.error_callback:
                    self.error_callback(f"Serial error: {exc}")
                break
