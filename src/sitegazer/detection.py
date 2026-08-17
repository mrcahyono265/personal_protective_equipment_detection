"""Logika deteksi APD: klasifikasi status, snapshot bukti, dan proses frame."""

import logging
import os
import time
import uuid
from datetime import datetime

import cv2

from sitegazer import config

logger = logging.getLogger(__name__)


def classify(cls_name):
    """Tentukan status, warna, dan apakah pelanggaran dari nama class model.

    Pure function (tanpa side effect) sehingga mudah diuji.
    Asumsi nama class di dataset mengandung kata kunci ini.
    """
    name_lower = cls_name.lower()

    if name_lower.startswith("no") or " no" in name_lower:
        # Contoh: "No Safety Helmet", "No Safety Vest", "no_safety_helmet"
        return f"VIOLATION: {cls_name.upper()}", (0, 0, 255), True  # Merah
    if "safety" in name_lower or "helmet" in name_lower or "vest" in name_lower \
            or "hard" in name_lower or "hat" in name_lower:
        return f"SAFE: {cls_name.upper()}", (0, 255, 0), False  # Hijau
    return "UNKNOWN", (128, 128, 128), False


def save_snapshot(frame, status, snapshot_dir, max_snapshots):
    """Simpan bukti pelanggaran, kembalikan URL publiknya (atau None jika gagal)."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{status.split(':')[0]}_{timestamp}_{str(uuid.uuid4())[:4]}.jpg"
        filepath = os.path.join(snapshot_dir, filename)

        cv2.imwrite(filepath, frame)

        # Cleanup file lama
        files = sorted(
            (os.path.join(snapshot_dir, f) for f in os.listdir(snapshot_dir)),
            key=os.path.getmtime,
        )
        if len(files) > max_snapshots:
            os.remove(files[0])

        return f"/static/snapshots/{filename}"
    except Exception as e:
        logger.error(f"Snapshot error: {e}")
        return None


def process_frame(frame, model, state):
    """Inferensi YOLO + gambar box + log pelanggaran (dengan cooldown).

    `state` adalah dict app_state milik API (model, zona, log, dll).
    Mengembalikan (frame terproses, daftar log pelanggaran baru).
    """
    current_time = time.time()
    processed = frame.copy()
    detection_results = []

    # 1. Inferensi Single Model
    results = model(frame, verbose=False, conf=0.4)[0]

    # 2. Loop semua deteksi
    if results.boxes:
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id]

            # 3. Tentukan status & warna
            status, color, is_violation = classify(cls_name)

            # 4. Gambar box & label
            cv2.rectangle(processed, (x1, y1), (x2, y2), color, 2)
            cv2.putText(processed, f"{cls_name} {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # 5. Log pelanggaran dengan cooldown per class
            if is_violation:
                last_logged = state["last_log_times"].get(cls_name, 0)
                if (current_time - last_logged) > config.LOG_COOLDOWN:
                    img_url = save_snapshot(processed, "VIOLATION",
                                            config.SNAPSHOT_DIR,
                                            config.MAX_SNAPSHOTS)
                    log_entry = {
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "zone": state["current_zone"],
                        "status": status,
                        "person_id": 0,  # Tidak ada tracking ID lagi
                        "image_url": img_url,
                    }
                    state["detection_logs"].insert(0, log_entry)
                    if len(state["detection_logs"]) > 50:
                        state["detection_logs"].pop()

                    detection_results.append(log_entry)
                    state["last_log_times"][cls_name] = current_time

    # Overlay zona
    cv2.putText(processed, f"Zone: {state['current_zone']}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

    return processed, detection_results