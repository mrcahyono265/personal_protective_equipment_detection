import time
import threading
import cv2

RTSP_URL = "rtsp://192.168.1.1:7070/webcam"
ROTATE = True


class E99Drone:
    """E88 Pro/E99 pasif: hanya video RTSP, kontrol via remote fisik bawaan"""

    CONTROL = False

    def __init__(self):
        self._cap = None
        self._frame = None
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

    @property
    def is_flying(self):
        return False

    def connect(self):
        self._running = True
        self._thread = threading.Thread(target=self._update, daemon=True)
        self._thread.start()

    def _update(self):
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                self._cap = cv2.VideoCapture(RTSP_URL)
                if not self._cap.isOpened():
                    time.sleep(1)
                    continue
            ret, frame = self._cap.read()
            if ret:
                if ROTATE:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                with self._lock:
                    self._frame = frame
            else:
                self._cap.release()
                self._cap = None
                time.sleep(1)

    def get_frame(self):
        with self._lock:
            return self._frame

    def get_battery(self):
        return None

    def get_height(self):
        return None

    def get_flight_time(self):
        return None

    def disconnect(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._cap:
            self._cap.release()