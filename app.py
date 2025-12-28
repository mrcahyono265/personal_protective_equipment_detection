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

# ============================
# KONFIGURASI KAMERA
# ============================
# Ganti dengan URL DroidCam Anda
CAMERA_SOURCE = "2" 

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
# STATE GLOBAL
# ============================
app_state = {
    "current_zone": "Unknown Zone",
    "detection_logs": [],
    "is_streaming": False,
    "model": None,          # Single Model
    "camera": None,
    "last_log_times": {},   # Untuk cooldown
    "snapshot_count": 0
}

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
    
    # 3. Start Camera
    logger.info(f"Starting Camera: {CAMERA_SOURCE}")
    app_state["camera"] = VideoCamera(CAMERA_SOURCE)
    
    yield
    
    # Cleanup
    if app_state["camera"]: app_state["camera"].stop()

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

@app.post("/set_zone/{zone_name}")
async def set_zone(zone_name: str):
    app_state["current_zone"] = zone_name
    return {"status": "success", "zone": zone_name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)