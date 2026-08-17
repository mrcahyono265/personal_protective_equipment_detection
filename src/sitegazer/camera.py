"""Sumber kamera: webcam/IP camera dan drone (adapter baca frame)."""

import logging
import threading
import time

import cv2

logger = logging.getLogger(__name__)


class VideoCamera:
    """Buffer-less Video Capture untuk menghilangkan delay (webcam/IP camera)."""

    def __init__(self, source: str = "0"):
        self.source = source
        self.stream = None
        self.latest_frame = None
        self.running = False
        self.lock = threading.Lock()

        self._initialize_stream()
        self.start()

    def _initialize_stream(self):
        try:
            src = int(self.source) if self.source.isdigit() else self.source
            self.stream = cv2.VideoCapture(src)
            # Paksa buffer sekecil mungkin
            if "http" in str(self.source):
                self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception as e:
            logger.error(f"Camera init error: {e}")

    def start(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._update, daemon=True).start()

    def _update(self):
        while self.running:
            if self.stream and self.stream.isOpened():
                ret, frame = self.stream.read()
                if ret:
                    with self.lock:
                        self.latest_frame = frame
                else:
                    # Auto reconnect logic simpel
                    time.sleep(1)
                    self._initialize_stream()
            else:
                time.sleep(1)

    def read(self):
        with self.lock:
            return True, self.latest_frame.copy() if self.latest_frame is not None else None

    def stop(self):
        self.running = False
        if self.stream:
            self.stream.release()


class DroneCamera:
    """Adapter read() dari frame drone agar generate_frames tak berubah."""

    def __init__(self, drone):
        self._drone = drone

    def read(self):
        frame = self._drone.get_frame()
        if frame is None:
            return False, None
        return True, frame

    def stop(self):
        pass