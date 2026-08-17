import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sitegazer import config


def test_clamp():
    assert config.clamp(150, -100, 100) == 100
    assert config.clamp(-150, -100, 100) == -100
    assert config.clamp(42, -100, 100) == 42


def test_rate_curve():
    assert config.rate_curve(0.5) == 0.125
    assert config.rate_curve(-0.5) == -0.125
    assert config.rate_curve(0) == 0


def test_trim_stays_in_bounds():
    assert config.clamp(config.TRIM_MAX + config.TRIM_STEP, -config.TRIM_MAX, config.TRIM_MAX) == config.TRIM_MAX
    assert config.clamp(-config.TRIM_MAX - config.TRIM_STEP, -config.TRIM_MAX, config.TRIM_MAX) == -config.TRIM_MAX


def test_speed_modes_valid():
    assert all(0 < s <= 100 for s in config.SPEED_MODES)
    assert config.BATTERY_WARN > config.BATTERY_CRITICAL > 0


def test_camera_type_valid():
    assert config.CAMERA_TYPE in ("webcam", "tello", "e99")


if __name__ == "__main__":
    for fn in (test_clamp, test_rate_curve, test_trim_stays_in_bounds,
               test_speed_modes_valid, test_camera_type_valid):
        fn()
    print("all ok")