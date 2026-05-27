import queue
import threading
from collections.abc import Callable

## watek liczy srednia temperature, wilgotnosc i cisnienie.
class StatisticsWorker:

    def __init__(
        self,
        statistics_callback: Callable[[dict], None],
        error_callback: Callable[[str], None] | None = None,
    ):
        self.statistics_callback = statistics_callback
        self.error_callback = error_callback

        self.running = False
        self.data_queue: queue.Queue[dict | None] = queue.Queue()
        self.thread: threading.Thread | None = None

        self.measurement_count = 0
        self.temp_sum = 0.0
        self.humi_sum = 0.0
        self.pressure_sum = 0.0

    def start(self) -> None:
        if self.running:
            return

        self.data_queue = queue.Queue()
        self.measurement_count = 0
        self.temp_sum = 0.0
        self.humi_sum = 0.0
        self.pressure_sum = 0.0

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

    def _worker(self) -> None:
        while True:
            try:
                data = self.data_queue.get()

                if data is None:
                    break

                self.measurement_count += 1
                self.temp_sum += data["temp"]
                self.humi_sum += data["humi"]
                self.pressure_sum += data["pressure"]

                self.statistics_callback({
                    "count": self.measurement_count,
                    "avg_temp": self.temp_sum / self.measurement_count,
                    "avg_humi": self.humi_sum / self.measurement_count,
                    "avg_pressure": self.pressure_sum / self.measurement_count,
                })

            except Exception as exc:
                if self.error_callback:
                    self.error_callback(f"Statistics error: {exc}")
                break
