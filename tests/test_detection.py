import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sitegazer.detection import classify


def test_classify_violation():
    status, color, is_violation = classify("no_safety_helmet")
    assert is_violation
    assert status.startswith("VIOLATION")
    assert color == (0, 0, 255)


def test_classify_safe():
    status, color, is_violation = classify("hard_hat")
    assert not is_violation
    assert status.startswith("SAFE")
    assert color == (0, 255, 0)


def test_classify_unknown():
    status, color, is_violation = classify("random_object")
    assert not is_violation
    assert status == "UNKNOWN"


if __name__ == "__main__":
    for fn in (test_classify_violation, test_classify_safe, test_classify_unknown):
        fn()
    print("all ok")