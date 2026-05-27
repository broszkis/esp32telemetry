import queue
import threading
from collections.abc import Callable

##watek zapisuje dane w pliku txt
class TelemetryLogger:

    def __init__(
        self,
        file_name: str,
        error_callback: Callable[[str], None] | None = None,
    ):
        self.file_name = file_name
        self.error_callback = error_callback

        self.running = False
        self.data_queue: queue.Queue[dict | None] = queue.Queue()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.running:
            return

        self.data_queue = queue.Queue()
        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if not self.running:
            return

        self.running = False
        self.data_queue.put(None)

    def put(self, data: dict) -> None:
        if self.running:
            self.data_queue.put(data)

    def _create_file_if_needed(self) -> None:
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

    def _worker(self) -> None:
        try:
            self._create_file_if_needed()

            while True:
                data = self.data_queue.get()

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

        except Exception as exc:
            if self.error_callback:
                self.error_callback(f"Logger error: {exc}")
