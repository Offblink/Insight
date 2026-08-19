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
    cfg.set(cfg.ctrl_peek, False)
    assert cfg.get(cfg.ctrl_peek) is False
    cfg.set(cfg.hotkey, "ctrl+shift+z")
    assert cfg.get(cfg.hotkey) == "ctrl+shift+z"
    # 重新加载,验证 JSON 落盘
    cfg2 = load_config(file)
    assert cfg2.get(cfg2.zoom) == 3.0
    assert cfg2.get(cfg2.ctrl_peek) is False
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
    from pynput import keyboard

    from src.hotkey import InputController, _key_token, parse_hotkey

    assert parse_hotkey("ctrl+alt+m") == {"<ctrl>", "<alt>", "m"}
    assert parse_hotkey("win+1") == {"<cmd>", "1"}
    assert _key_token(keyboard.Key.ctrl_l) == "<ctrl>"
    assert _key_token(keyboard.Key.alt_r) == "<alt>"
    assert _key_token(keyboard.Key.f5) == "<f5>"
    assert _key_token(keyboard.KeyCode.from_char("M")) == "m"

    events = []
    ic = InputController(
        "ctrl+alt+m",
        lambda: events.append("peek_start"),
        lambda: events.append("peek_end"),
        lambda: events.append("toggle"),
    )
    # Ctrl 按住:边缘触发一次;pynput 重复 press 不重复触发;松开一次即收回
    ic._on_press(keyboard.Key.ctrl_l)
    ic._on_press(keyboard.Key.ctrl_l)  # 按住期间的重复 press
    ic._on_press(keyboard.Key.ctrl_l)
    assert events == ["peek_start"]
    ic._on_release(keyboard.Key.ctrl_l)
    assert events == ["peek_start", "peek_end"]
    # 双 Ctrl 键:松开一个不收回,全部松开才收回
    ic._on_press(keyboard.Key.ctrl_l)
    ic._on_press(keyboard.Key.ctrl_r)
    assert events == ["peek_start", "peek_end", "peek_start"]
    ic._on_release(keyboard.Key.ctrl_r)
    assert events == ["peek_start", "peek_end", "peek_start"]
    ic._on_release(keyboard.Key.ctrl_l)
    assert events == ["peek_start", "peek_end", "peek_start", "peek_end"]
    # 组合:ctrl+alt+m 完整按下 → toggle 一次;松开 m 再按 → 再触发
    ic._on_press(keyboard.Key.ctrl_l)
    ic._on_press(keyboard.Key.alt_l)
    ic._on_press(keyboard.KeyCode.from_char("m"))
    assert events == ["peek_start", "peek_end", "peek_start", "peek_end", "peek_start", "toggle"]
    ic._on_release(keyboard.KeyCode.from_char("m"))
    ic._on_press(keyboard.KeyCode.from_char("m"))
    assert events.count("toggle") == 2
    # 热键热替换
    ic.set_hotkey("ctrl+shift+z")
    assert ic._required == {"<ctrl>", "<shift>", "z"}
    print("  hotkey 边缘触发 OK")


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
    from src.settings_window import (
        FloatSliderCard,
        SettingsWindow,
        _hotkey_to_qseq_text,
        _qseq_to_hotkey,
        reset_all,
    )

    app = QApplication.instance() or QApplication(sys.argv)
    config = load_config(_tmp_config())

    # 热键格式互转
    assert _hotkey_to_qseq_text("ctrl+alt+m") == "Ctrl+Alt+M"
    assert _qseq_to_hotkey("Ctrl+Alt+M") == "ctrl+alt+m"
    assert _qseq_to_hotkey("Ctrl+Shift+Z") == "ctrl+shift+z"
    assert _qseq_to_hotkey("M") is None        # 无修饰键拒绝
    assert _qseq_to_hotkey("Meta+M") is None   # Win 键拒绝(系统冲突)
    assert _qseq_to_hotkey("Shift+M") is None  # Shift 裸组合拒绝(干扰打字)

    # FloatSliderCard:滑杆 → config 更新 → 卡片刷新
    card = FloatSliderCard(config.zoom, FluentIcon.ZOOM, "倍率", "1.0-8.0", 1.0, 8.0, 0.1)
    card._slider.setValue(int(2.0 / 0.1))
    app.processEvents()
    assert abs(config.get(config.zoom) - 2.0) < 1e-6, config.get(config.zoom)

    # 恢复默认:全部配置项回初始值
    config.set(config.zoom, 6.0)
    config.set(config.hotkey, "ctrl+shift+z")
    reset_all(config)
    assert abs(config.get(config.zoom) - 2.5) < 1e-6
    assert config.get(config.hotkey) == "ctrl+alt+m"
    assert config.get(config.ctrl_peek) is True

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
