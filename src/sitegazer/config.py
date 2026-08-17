"""Konfigurasi global SiteGazer.

Semua nilai bisa diubah langsung di kode ini (default), atau di-override
lewat environment variable tanpa menyentuh kode.

Contoh override:
  SITEGAZER_CAMERA=webcam python app.py
  SITEGAZER_MODEL=models/best_ppe_yolo11n.pt python app.py
"""

import json
import math
import os

# ============================
# KAMERA
# ============================
# "webcam" = kamera lokal/IP camera (CAMERA_SOURCE di bawah)
# "tello"  = DJI Tello (wajib terhubung Wi-Fi Tello, kontrol penuh dari laptop)
# "e99"    = E88 Pro/E99 (wajib terhubung Wi-Fi drone, video saja + REC/capture,
#            kontrol terbang via remote fisik bawaan)
CAMERA_TYPE = os.getenv("SITEGAZER_CAMERA", "webcam")
CAMERA_SOURCE = os.getenv("SITEGAZER_CAMERA_SOURCE", "0")

# ============================
# SISTEM
# ============================
MODEL_PATH = os.getenv("SITEGAZER_MODEL", "models/best_ppe_yolo11n.pt")
SNAPSHOT_DIR = os.getenv("SITEGAZER_SNAPSHOT_DIR", "static/snapshots")
MAX_SNAPSHOTS = int(os.getenv("SITEGAZER_MAX_SNAPSHOTS", "50"))
LOG_COOLDOWN = 3.0  # Jeda (detik) antar log pelanggaran per class agar tidak spam
LOG_LEVEL = os.getenv("SITEGAZER_LOG", "INFO")

HOST = os.getenv("SITEGAZER_HOST", "0.0.0.0")
PORT = int(os.getenv("SITEGAZER_PORT", "8000"))

# ============================
# DRONE
# ============================
PHOTO_DIR = 'captures/photos'
VIDEO_DIR = 'captures/videos'
TRIM_STEP = 3
TRIM_MAX = 30
DEADZONE = 0.15
SPEED_MODES = (30, 50, 70, 100)
HOLD_DELAY = 0.8
BATTERY_WARN = 20
BATTERY_CRITICAL = 10
CONFIG_FILE = 'config.json'


# ============================
# UTILITAS MATEMATIKA
# ============================
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def rate_curve(x):
    """Kurva eksponensial x^3: gerakan kecil halus, gerakan besar responsif."""
    return math.copysign(abs(x) ** 3, x)


# ============================
# PERSISTENSI CONFIG DRONE (trim & speed)
# ============================
def load_config():
    try:
        with open(CONFIG_FILE) as f:
            d = json.load(f)
        return d.get('trim_lr', 0), d.get('speed_idx', 3)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0, 3


def save_config(trim_lr, speed_idx):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'trim_lr': trim_lr, 'speed_idx': speed_idx}, f)
    except OSError:
        pass