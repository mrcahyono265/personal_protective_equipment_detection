            # app.py - Backend FastAPI Single Model (Fokus APD Saja)
import os
import time
import asyncio
import threading
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from ultralytics import YOLO
from contextlib import asynccontextmanager
import logging
import uuid

from drone.config import (
    TRIM_STEP, TRIM_MAX, SPEED_MODES, BATTERY_CRITICAL,
    clamp, rate_curve, load_config, save_config,
)
from drone.tello_drone import TelloDrone
from drone.e99_drone import E99Drone
from drone.input_handler import InputHandler
from drone.video_handler import VideoHandler

# ============================
# KONFIGURASI KAMERA
# ============================
# "webcam" = kamera lokal/IP camera (CAMERA_SOURCE di bawah)
# "tello"  = DJI Tello (wajib terhubung Wi-Fi Tello, kontrol penuh dari laptop)
# "e99"    = E88 Pro/E99 (wajib terhubung Wi-Fi drone, video saja + REC/capture,
#            kontrol terbang via remote fisik bawaan)
CAMERA_TYPE = "e99"
CAMERA_SOURCE = "0"

# ============================
# KONFIGURASI SISTEM
# ============================
SNAPSHOT_DIR = "templates/snapshots"
MAX_SNAPSHOTS = 50
LOG_COOLDOWN = 3.0  # Jeda waktu (detik) antar log agar tidak spam

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================
# KELAS VIDEO CAMERA (THREADED)
# ============================
class VideoCamera:
    """Buffer-less Video Capture untuk menghilangkan delay"""
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
        if self.running: return
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
        if self.stream: self.stream.release()

# ============================
# KELAS DRONE CAMERA (ADAPTER DECODER DRONE)
# ============================
class DroneCamera:
    """Adapter read() dari frame drone agar generate_frames tak berubah"""
    def __init__(self, drone):
        self._drone = drone

    def read(self):
        frame = self._drone.get_frame()
        if frame is None:
            return False, None
        return True, frame

    def stop(self):
        pass

# ============================
# STATE GLOBAL
# ============================
app_state = {
    "current_zone": "Unknown Zone",
    "detection_logs": [],
    "is_streaming": False,
    "model": None,          # Single Model
    "camera": None,
    "drone": None,
    "drone_state": {},
    "video": None,
    "last_processed": None,
    "drone_running": False,
    "last_log_times": {},   # Untuk cooldown
    "snapshot_count": 0
}

# ============================
# THREAD KONTROL DRONE
# ============================
def drone_control_loop():
    """Loop kontrol drone: keyboard + gamepad, berjalan paralel dengan server.
    Untuk drone pasif (E99, CONTROL=False) hanya foto & rekaman yang aktif."""
    inp = InputHandler()
    drone = app_state["drone"]
    video = app_state["video"]
    st_state = app_state["drone_state"]
    trim_lr, speed_idx = load_config()

    if inp.has_gamepad():
        logger.info("Gamepad detected")
    else:
        logger.info("No gamepad connected - keyboard only")

    st_state["trim"], st_state["speed"] = trim_lr, SPEED_MODES[speed_idx]
    while app_state["drone_running"]:
        st = inp.poll()

        if drone.CONTROL:
            if st.switch_mode:
                inp.switch_mode()
                st_state["mode"] = inp.mode
            if st.emergency_land and drone.is_flying:
                try:
                    drone.land()
                    logger.warning("Emergency land!")
                except Exception as e:
                    logger.error(f"Emergency land gagal: {e}")
            elif st.takeoff_land:
                try:
                    drone.toggle_flight()
                    inp.vibrate(32768, 32768, 0.2)
                except Exception as e:
                    logger.error(f"Takeoff/Land gagal: {e}")
            if st.speed_up:
                speed_idx = (speed_idx + 1) % len(SPEED_MODES)
            if st.speed_down:
                speed_idx = (speed_idx - 1) % len(SPEED_MODES)
            st_state["speed"] = SPEED_MODES[speed_idx]
            if st.trim_left:
                trim_lr = clamp(trim_lr - TRIM_STEP, -TRIM_MAX, TRIM_MAX)
            if st.trim_right:
                trim_lr = clamp(trim_lr + TRIM_STEP, -TRIM_MAX, TRIM_MAX)
            if st.trim_reset:
                trim_lr = 0
            if st.grid:
                st_state["grid"] = not st_state["grid"]
            st_state["trim"] = trim_lr

            spd = SPEED_MODES[speed_idx] / 100.0
            lr = clamp(int(rate_curve(st.lr) * 100 * spd) + trim_lr, -100, 100)
            fb = clamp(int(-rate_curve(st.fb) * 100 * spd), -100, 100)
            ud = clamp(int(-rate_curve(st.ud) * 100 * spd), -100, 100)
            yaw = clamp(int(-rate_curve(st.yaw) * 100 * spd), -100, 100)

            drone.send_rc(lr, fb, ud, yaw)

            battery = drone.get_battery()
            st_state["battery"] = battery
            st_state["lr"], st_state["fb"], st_state["ud"], st_state["yaw"] = st.lr, st.fb, st.ud, st.yaw
            st_state["flying"] = drone.is_flying
            if battery is not None and battery <= BATTERY_CRITICAL and drone.is_flying:
                try:
                    drone.land()
                    logger.warning("Auto-land: battery critical")
                except Exception as e:
                    logger.error(f"Auto-land gagal: {e}")
        else:
            st_state["battery"] = drone.get_battery()
            st_state["flying"] = drone.is_flying

        st_state["height"] = drone.get_height()
        st_state["flight_time"] = drone.get_flight_time()

        frame = app_state["last_processed"]
        if st.photo:
            if frame is not None:
                video.capture_photo(frame)
                inp.vibrate(65535, 0, 0.1)
                logger.info(f"Photo captured ({video.photo_count} total)")
        if st.record_toggle:
            if frame is not None and not video.recording:
                video.toggle_recording(frame.shape)
            elif video.recording:
                video.toggle_recording(None)
            inp.vibrate(0, 65535, 0.3)
            logger.info(f"Recording {'started' if video.recording else 'stopped'}")

        if video.recording and frame is not None:
            video.write_frame(frame)

        time.sleep(0.05)

# ============================
# LIFECYCLE
# ============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Setup Folder
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    
    # 2. Load Single Model (PPE Only)
    logger.info("Loading Custom PPE Model...")
    # Pastikan nama file model sesuai dengan yang ada di folder Anda
    app_state["model"] = YOLO("best_ppe_yolo11n.pt") 
    
    # 3. Start Camera (Webcam, Tello, atau E88 Pro/E99)
    if CAMERA_TYPE in ("tello", "e99"):
        if CAMERA_TYPE == "tello":
            logger.info("Connecting to Tello drone...")
            drone = TelloDrone()
        else:
            logger.info("Connecting to E88 Pro/E99 drone (video only)...")
            drone = E99Drone()
        try:
            drone.connect()
            if CAMERA_TYPE == "tello":
                logger.info(f"Tello connected - battery {drone.get_battery()}%")
            else:
                logger.info("E88 Pro/E99 connected - RTSP video active")
        except Exception as e:
            logger.error(f"Drone connect failed: {e}")
            drone = None
        
        if drone is not None:
            app_state["drone"] = drone
            app_state["video"] = VideoHandler()
            app_state["drone_state"] = {
                "battery": 0, "flying": False, "mode": "keyboard",
                "trim": 0, "speed": 100, "grid": False,
                "height": 0, "flight_time": 0,
                "lr": 0.0, "fb": 0.0, "ud": 0.0, "yaw": 0.0,
            }
            app_state["camera"] = DroneCamera(drone)
            app_state["drone_running"] = True
            threading.Thread(target=drone_control_loop, daemon=True).start()
    else:
        logger.info(f"Starting Camera: {CAMERA_SOURCE}")
        app_state["camera"] = VideoCamera(CAMERA_SOURCE)
    
    yield
    
    # Cleanup
    app_state["drone_running"] = False
    if app_state["camera"]: app_state["camera"].stop()
    if app_state["drone"]:
        trim_lr = app_state["drone_state"].get("trim", 0)
        speed_idx = list(SPEED_MODES).index(app_state["drone_state"].get("speed", 100)) if app_state["drone_state"].get("speed", 100) in SPEED_MODES else 3
        save_config(trim_lr, speed_idx)
        app_state["drone"].disconnect()

app = FastAPI(lifespan=lifespan)
app.mount("/templates", StaticFiles(directory="templates"), name="templates")

# ============================
# LOGIC UTAMA (SIMPLIFIED)
# ============================
def save_snapshot(frame, status):
    """Simpan bukti pelanggaran"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{status.split(':')[0]}_{timestamp}_{str(uuid.uuid4())[:4]}.jpg"
        filepath = os.path.join(SNAPSHOT_DIR, filename)
        
        cv2.imwrite(filepath, frame)
        
        # Cleanup file lama
        files = sorted([os.path.join(SNAPSHOT_DIR, f) for f in os.listdir(SNAPSHOT_DIR)], key=os.path.getmtime)
        if len(files) > MAX_SNAPSHOTS:
            os.remove(files[0])
            
        return f"/templates/snapshots/{filename}"
    except Exception as e:
        logger.error(f"Snapshot error: {e}")
        return None

def process_frame(frame):
    current_time = time.time()
    processed = frame.copy()
    detection_results = []
    
    # 1. Inferensi Single Model
    results = app_state["model"](frame, verbose=False, conf=0.4)[0]
    
    # 2. Loop semua deteksi
    if results.boxes:
        for box in results.boxes:
            # Ambil data bounding box
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = app_state["model"].names[cls_id] # Ambil nama class asli dari model
            
            # 3. Tentukan Status & Warna (Hardcoded Logic sesuai Dataset Rafidah)
            # Asumsi nama class di dataset mengandung kata kunci ini:
            status = "UNKNOWN"
            color = (128, 128, 128)
            is_violation = False
            
            # Logic Deteksi String (Case Insensitive)
            name_lower = cls_name.lower()
            
            if "no" in name_lower: # Contoh: "No Safety Helmet", "No Safety Vest"
                status = f"VIOLATION: {cls_name.upper()}"
                color = (0, 0, 255) # Merah
                is_violation = True
            elif "safety" in name_lower or "helmet" in name_lower or "vest" in name_lower:
                status = f"SAFE: {cls_name.upper()}"
                color = (0, 255, 0) # Hijau
            
            # 4. Gambar Box & Label
            cv2.rectangle(processed, (x1, y1), (x2, y2), color, 2)
            cv2.putText(processed, f"{cls_name} {conf:.2f}", (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # 5. Logic Logging & Cooldown (Hanya log jika Pelanggaran)
            if is_violation:
                last_logged = app_state["last_log_times"].get(cls_name, 0)
                
                if (current_time - last_logged) > LOG_COOLDOWN:
                    # Ambil snapshot
                    img_url = save_snapshot(processed, "VIOLATION")
                    
                    # Buat log entry
                    log_entry = {
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "zone": app_state["current_zone"],
                        "status": status,
                        "person_id": 0, # Tidak ada tracking ID lagi
                        "image_url": img_url
                    }
                    
                    # Simpan ke memori
                    app_state["detection_logs"].insert(0, log_entry)
                    if len(app_state["detection_logs"]) > 50:
                        app_state["detection_logs"].pop()
                    
                    detection_results.append(log_entry)
                    app_state["last_log_times"][cls_name] = current_time # Reset cooldown

    # Overlay Zone Info
    cv2.putText(processed, f"Zone: {app_state['current_zone']}", (20, 40), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
    
    return processed, detection_results

# ============================
# ENDPOINTS
# ============================
async def generate_frames():
    """Generator Streaming Efisien"""
    app_state["is_streaming"] = True
    while app_state["is_streaming"]:
        ret, frame = app_state["camera"].read()
        if not ret or frame is None:
            await asyncio.sleep(0.1)
            continue
            
        processed, _ = process_frame(frame)
        
        if app_state["drone"] is not None:
            st = app_state["drone_state"]
            processed = app_state["video"].render(
                processed, st["battery"], st["flying"], st["mode"],
                app_state["video"].recording, st["trim"], st["speed"],
                st["grid"], st["height"], st["flight_time"],
                st["lr"], st["fb"], st["ud"], st["yaw"],
            )
        app_state["last_processed"] = processed
        
        _, buffer = cv2.imencode('.jpg', processed, [cv2.IMWRITE_JPEG_QUALITY, 70])
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        await asyncio.sleep(0.01)

@app.get("/")
async def index():
    return HTMLResponse(open("templates/index.html").read())

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/get_logs")
async def get_logs():
    return JSONResponse({"logs": app_state["detection_logs"]})

@app.get("/snapshot_stats")
async def snapshot_stats():
    try:
        files = [f for f in os.listdir(SNAPSHOT_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        return {"total_snapshots": len(files)}
    except OSError:
        return {"total_snapshots": 0}

@app.post("/set_zone/{zone_name}")
async def set_zone(zone_name: str):
    app_state["current_zone"] = zone_name
    return {"status": "success", "zone": zone_name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)