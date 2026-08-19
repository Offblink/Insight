"""洞见 v2 冒烟测试:config 持久化、捕获、热键、托盘、设置窗口、动画生命周期。

真机运行(短暂闪现窗口),无外部依赖。
"""

import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _tmp_config() -> Path:
    return Path(tempfile.gettempdir()) / f"dongjian_smoke_{os.getpid()}.json"


def test_config() -> None:
    from src.config import load_config

    file = _tmp_config()
    cfg = load_config(file)
    cfg.set(cfg.zoom, 3.0)
    assert cfg.get(cfg.zoom) == 3.0
    cfg.set(cfg.right_click, False)
    assert cfg.get(cfg.right_click) is False
    cfg.set(cfg.hotkey, "ctrl+shift+z")
    assert cfg.get(cfg.hotkey) == "ctrl+shift+z"
    # 重新加载,验证 JSON 落盘
    cfg2 = load_config(file)
    assert cfg2.get(cfg2.zoom) == 3.0
    assert cfg2.get(cfg2.right_click) is False
    assert cfg2.get(cfg2.hotkey) == "ctrl+shift+z"
    print("  config 持久化 OK")


def test_capturer() -> None:
    from src.capturer import Capturer

    pm = Capturer().grab(200, 200, 120)
    assert not pm.isNull(), "抓取结果为空"
    dpr = pm.devicePixelRatio()
    assert abs(pm.width() / dpr - 120) <= 2, f"尺寸异常: {pm.width()} dpr={dpr}"
    print(f"  capturer 抓取 OK ({pm.width()}x{pm.height()} dpr={dpr})")


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


def test_tray() -> None:
    from src.config import load_config
    from src.magnifier import MagnifierWindow
    from src.tray import TrayController

    config = load_config(_tmp_config())
    magnifier = MagnifierWindow(config)
    opened = []
    tray = TrayController(config, magnifier, on_open_settings=lambda: opened.append(1))

    texts = [a.text() for a in tray._menu.actions()]
    assert any("倍率预设" in t for t in texts)
    assert any("跟随模式" in t for t in texts)
    assert any("设置…" in t for t in texts)
    assert any("退出" in t for t in texts)
    assert len(tray._zoom_actions) == 5

    # 倍率预设触发 → config 更新
    for preset, action in tray._zoom_actions.items():
        if abs(preset - 3.0) < 1e-6:
            action.trigger()
    assert abs(config.get(config.zoom) - 3.0) < 1e-6
    print("  tray 菜单结构 OK")


def test_settings() -> None:
    from PyQt6.QtWidgets import QApplication
    from qfluentwidgets import FluentIcon

    from src.config import load_config
    from src.settings_window import FloatSliderCard, SettingsWindow, set_autostart

    app = QApplication.instance() or QApplication(sys.argv)
    config = load_config(_tmp_config())

    # FloatSliderCard:滑杆 → config 更新 → 卡片刷新
    card = FloatSliderCard(config.zoom, FluentIcon.ZOOM, "倍率", "1.0-8.0", 1.0, 8.0, 0.1)
    card._slider.setValue(int(2.0 / 0.1))
    app.processEvents()
    assert abs(config.get(config.zoom) - 2.0) < 1e-6, config.get(config.zoom)

    win = SettingsWindow(config)
    win.show()
    app.processEvents()
    assert win.isVisible()
    win.close()
    app.processEvents()
    assert not win.isVisible(), "关窗应隐藏"
    print("  设置卡片与窗口 OK")


def test_magnifier_lifecycle() -> None:
    from PyQt6.QtWidgets import QApplication

    from src.config import load_config
    from src.magnifier import MagnifierWindow

    app = QApplication.instance() or QApplication(sys.argv)
    w = MagnifierWindow(load_config(_tmp_config()))

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


def main() -> None:
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    test_config()
    test_capturer()
    test_hotkey()
    test_tray()
    test_settings()
    test_magnifier_lifecycle()
    print("SMOKE OK")


if __name__ == "__main__":
    main()
