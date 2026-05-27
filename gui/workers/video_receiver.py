import threading
import time
from collections.abc import Callable

import cv2

##watek odbiera obraz z kamery esp
class VideoReceiver:

    def __init__(
        self,
        frame_callback: Callable,
        status_callback: Callable[[str], None] | None = None,
        error_callback: Callable[[str], None] | None = None,
    ):
        self.frame_callback = frame_callback
        self.status_callback = status_callback
        self.error_callback = error_callback

        self.capture = None
        self.running = False
        self.thread: threading.Thread | None = None

    def start(self, url: str) -> None:
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(
            target=self._worker,
            args=(url,),
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        self.running = False

        try:
            if self.capture:
                self.capture.release()
        except Exception:
            pass

        self.capture = None

    def _worker(self, url: str) -> None:
        try:
            if self.status_callback:
                self.status_callback(f"Video: connecting to {url}")

            self.capture = cv2.VideoCapture(url)

            if not self.capture.isOpened():
                if self.status_callback:
                    self.status_callback("Video: connection failed")
                self.stop()
                return

            if self.status_callback:
                self.status_callback("Video: connected")

            while self.running:
                ret, frame = self.capture.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.frame_callback(frame)

        except Exception as exc:
            if self.error_callback:
                self.error_callback(f"Video error: {exc}")
            self.stop()
