"""洞见 v2 冒烟测试:config 往返、捕获有效性、放大镜动画生命周期。

真机运行(短暂闪现窗口),无外部依赖。
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_ORG = "洞见冒烟"


def test_config() -> None:
    from src.config import Config

    c = Config(_ORG, "config")
    c.set("zoom", 3.0)
    assert c.get("zoom") == 3.0 and isinstance(c.get("zoom"), float)
    c.set("right_click", False)
    assert c.get("right_click") is False
    c.set("hotkey", "ctrl+shift+z")
    c2 = Config(_ORG, "config")
    assert c2.get("zoom") == 3.0 and c2.get("right_click") is False
    assert c2.get("hotkey") == "ctrl+shift+z"
    print("  config 往返 OK")


def test_capturer() -> None:
    from src.capturer import Capturer

    pm = Capturer().grab(200, 200, 120)
    assert not pm.isNull(), "抓取结果为空"
    dpr = pm.devicePixelRatio()
    assert abs(pm.width() / dpr - 120) <= 2, f"尺寸异常: {pm.width()} dpr={dpr}"
    print(f"  capturer 抓取 OK ({pm.width()}x{pm.height()} dpr={dpr})")


def test_magnifier_lifecycle() -> None:
    from PyQt6.QtWidgets import QApplication

    from src.config import Config
    from src.magnifier import MagnifierWindow

    app = QApplication.instance() or QApplication(sys.argv)
    w = MagnifierWindow(Config(_ORG, "magnifier"))

    w.pop()
    deadline = time.time() + 0.35
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert w.isVisible(), "pop 后不可见"
    assert w.get_progress() > 0.99, f"弹出动画未完成: {w.get_progress():.2f}"
    print("  pop 动画 OK")

    w.retract()
    deadline = time.time() + 0.25
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert not w.isVisible(), "retract 后仍可见"
    assert not w.is_persistent
    print("  retract 动画 OK")


def test_hotkey() -> None:
    from src.hotkey import HotkeyManager, _to_pynput

    assert _to_pynput("ctrl+alt+m") == "<ctrl>+<alt>+m"
    assert _to_pynput("Ctrl + Shift + Z") == "<ctrl>+<shift>+z"
    assert _to_pynput("f5") == "<f5>"
    assert _to_pynput("win+1") == "<cmd>+1"
    fired = []
    mgr = HotkeyManager(lambda: fired.append(1))
    mgr.set_hotkey("ctrl+alt+m")
    mgr.stop()
    mgr.set_hotkey("")
    assert not mgr._listener
    print("  hotkey 转换与生命周期 OK")


def main() -> None:
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    test_config()
    test_capturer()
    test_hotkey()
    test_magnifier_lifecycle()
    print("SMOKE OK")


if __name__ == "__main__":
    main()
