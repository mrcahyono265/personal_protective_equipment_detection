"""API FastAPI SiteGazer: lifespan, streaming, endpoint, entry point."""

import asyncio
import logging
import os
import threading
from contextlib import asynccontextmanager

import cv2
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO

from sitegazer import config
from sitegazer.camera import DroneCamera, VideoCamera
from sitegazer.controller import drone_control_loop
from sitegazer.detection import process_frame
from sitegazer.drone.e99_drone import E99Drone
from sitegazer.drone.tello_drone import TelloDrone
from sitegazer.drone.video_handler import VideoHandler

logger = logging.getLogger(__name__)

# ============================
# STATE GLOBAL
# ============================
app_state = {
    "current_zone": "Unknown Zone",
    "detection_logs": [],
    "is_streaming": False,
    "model": None,
    "camera": None,
    "drone": None,
    "drone_state": {},
    "video": None,
    "last_processed": None,
    "drone_running": False,
    "last_log_times": {},
}


# ============================
# LIFECYCLE
# ============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Setup folder
    os.makedirs(config.SNAPSHOT_DIR, exist_ok=True)

    # 2. Load model
    logger.info(f"Loading model: {config.MODEL_PATH}")
    app_state["model"] = YOLO(config.MODEL_PATH)

    # 3. Start camera (webcam, Tello, atau E88 Pro/E99)
    if config.CAMERA_TYPE in ("tello", "e99"):
        if config.CAMERA_TYPE == "tello":
            logger.info("Connecting to Tello drone...")
            drone = TelloDrone()
        else:
            logger.info("Connecting to E88 Pro/E99 drone (video only)...")
            drone = E99Drone()
        try:
            drone.connect()
            if config.CAMERA_TYPE == "tello":
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
            threading.Thread(
                target=drone_control_loop, args=(app_state,), daemon=True
            ).start()
    else:
        logger.info(f"Starting Camera: {config.CAMERA_SOURCE}")
        app_state["camera"] = VideoCamera(config.CAMERA_SOURCE)

    yield

    # Cleanup
    app_state["drone_running"] = False
    if app_state["camera"]:
        app_state["camera"].stop()
    if app_state["drone"]:
        trim_lr = app_state["drone_state"].get("trim", 0)
        speed = app_state["drone_state"].get("speed", 100)
        speed_idx = list(config.SPEED_MODES).index(speed) if speed in config.SPEED_MODES else 3
        config.save_config(trim_lr, speed_idx)
        app_state["drone"].disconnect()


app = FastAPI(lifespan=lifespan)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ============================
# STREAMING & ENDPOINT
# ============================
async def generate_frames():
    """Generator streaming efisien: deteksi APD + HUD drone + encode JPEG."""
    app_state["is_streaming"] = True
    while app_state["is_streaming"]:
        ret, frame = app_state["camera"].read()
        if not ret or frame is None:
            await asyncio.sleep(0.1)
            continue

        processed, _ = process_frame(frame, app_state["model"], app_state)

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
    with open("templates/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(),
                             media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/get_logs")
async def get_logs():
    return JSONResponse({"logs": app_state["detection_logs"]})


@app.get("/current_zone")
async def current_zone():
    return JSONResponse({"current_zone": app_state["current_zone"]})


@app.get("/snapshot_stats")
async def snapshot_stats():
    try:
        files = [f for f in os.listdir(config.SNAPSHOT_DIR)
                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        return {"total_snapshots": len(files)}
    except OSError:
        return {"total_snapshots": 0}


@app.post("/set_zone/{zone_name}")
async def set_zone(zone_name: str):
    app_state["current_zone"] = zone_name
    return {"status": "success", "zone": zone_name}


def main():
    import uvicorn

    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    )
    uvicorn.run(app, host=config.HOST, port=config.PORT)