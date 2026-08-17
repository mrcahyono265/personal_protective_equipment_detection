import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drone.config import (
    clamp, rate_curve, TRIM_MAX, TRIM_STEP,
    SPEED_MODES, BATTERY_WARN, BATTERY_CRITICAL,
)


def test_clamp():
    assert clamp(150, -100, 100) == 100
    assert clamp(-150, -100, 100) == -100
    assert clamp(42, -100, 100) == 42


def test_rate_curve():
    assert rate_curve(0.5) == 0.125
    assert rate_curve(-0.5) == -0.125
    assert rate_curve(0) == 0


def test_trim_stays_in_bounds():
    assert clamp(TRIM_MAX + TRIM_STEP, -TRIM_MAX, TRIM_MAX) == TRIM_MAX
    assert clamp(-TRIM_MAX - TRIM_STEP, -TRIM_MAX, TRIM_MAX) == -TRIM_MAX


def test_speed_modes_valid():
    assert all(0 < s <= 100 for s in SPEED_MODES)
    assert BATTERY_WARN > BATTERY_CRITICAL > 0


if __name__ == "__main__":
    for fn in (test_clamp, test_rate_curve, test_trim_stays_in_bounds, test_speed_modes_valid):
        fn()
    print("all ok")