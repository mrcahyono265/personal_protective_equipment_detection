"""Thread kontrol drone: keyboard + gamepad, berjalan paralel dengan server.

Untuk drone pasif (E99, CONTROL=False) hanya foto & rekaman yang aktif;
kontrol terbang, trim, speed, dan auto-land di-skip otomatis.
"""

import logging
import time

from sitegazer import config
from sitegazer.drone.input_handler import InputHandler

logger = logging.getLogger(__name__)


def drone_control_loop(state):
    """Loop utama kontrol drone. `state` adalah dict app_state milik API."""
    inp = InputHandler()
    drone = state["drone"]
    video = state["video"]
    st_state = state["drone_state"]
    trim_lr, speed_idx = config.load_config()

    if inp.has_gamepad():
        logger.info("Gamepad detected")
    else:
        logger.info("No gamepad connected - keyboard only")

    st_state["trim"], st_state["speed"] = trim_lr, config.SPEED_MODES[speed_idx]
    while state["drone_running"]:
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
                speed_idx = (speed_idx + 1) % len(config.SPEED_MODES)
            if st.speed_down:
                speed_idx = (speed_idx - 1) % len(config.SPEED_MODES)
            st_state["speed"] = config.SPEED_MODES[speed_idx]
            if st.trim_left:
                trim_lr = config.clamp(trim_lr - config.TRIM_STEP, -config.TRIM_MAX, config.TRIM_MAX)
            if st.trim_right:
                trim_lr = config.clamp(trim_lr + config.TRIM_STEP, -config.TRIM_MAX, config.TRIM_MAX)
            if st.trim_reset:
                trim_lr = 0
            if st.grid:
                st_state["grid"] = not st_state["grid"]
            st_state["trim"] = trim_lr

            spd = config.SPEED_MODES[speed_idx] / 100.0
            lr = config.clamp(int(config.rate_curve(st.lr) * 100 * spd) + trim_lr, -100, 100)
            fb = config.clamp(int(-config.rate_curve(st.fb) * 100 * spd), -100, 100)
            ud = config.clamp(int(-config.rate_curve(st.ud) * 100 * spd), -100, 100)
            yaw = config.clamp(int(-config.rate_curve(st.yaw) * 100 * spd), -100, 100)

            drone.send_rc(lr, fb, ud, yaw)

            battery = drone.get_battery()
            st_state["battery"] = battery
            st_state["lr"], st_state["fb"], st_state["ud"], st_state["yaw"] = st.lr, st.fb, st.ud, st.yaw
            st_state["flying"] = drone.is_flying
            if battery is not None and battery <= config.BATTERY_CRITICAL and drone.is_flying:
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

        frame = state["last_processed"]
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