"""洞见 v2 — 圆形鼠标放大镜(托盘常驻版)。

启动即静默驻留托盘;右键按住 = 临时放大(peek),松开收回;
全局热键(默认 Ctrl+Alt+M)= 常驻跟随;托盘菜单含倍率预设与设置。
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

_REQUIREMENTS = Path(__file__).parent / "requirements.txt"

_DEP_MODULES = (
    ("PyQt6", "PyQt6"),
    ("PyQt6-Fluent-Widgets", "qfluentwidgets"),
    ("pynput", "pynput"),
)


def _ensure_deps() -> None:
    """缺失依赖自动安装后提示重启(MonaDrive 模式)。"""
    missing = [pkg for pkg, mod in _DEP_MODULES if importlib.util.find_spec(mod) is None]
    if not missing:
        return
    print(f"洞见: 检测到缺失依赖 -> {', '.join(missing)}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(_REQUIREMENTS)])
    except Exception as exc:  # noqa: BLE001 - 安装失败仅提示
        print(f"自动安装失败: {exc}\n请手动运行: python -m pip install -r requirements.txt")
        sys.exit(1)
    print("依赖安装完成,请重新启动洞见。")
    sys.exit(0)


def _run_selftest(app, magnifier) -> None:
    """DONGJIAN_SELFTEST=1:程序化 pop→retract→quit,供自动化验证。"""
    from PyQt6.QtCore import QTimer

    QTimer.singleShot(800, magnifier.pop)
    QTimer.singleShot(1600, magnifier.retract)
    QTimer.singleShot(2300, app.quit)


def main() -> None:
    import os

    from PyQt6.QtCore import QObject, Qt, QSharedMemory, pyqtSignal
    from PyQt6.QtWidgets import QApplication

    class _MouseBridge(QObject):
        """pynput 回调线程 → Qt 主线程的信号桥(queued 连接,线程安全)。"""

        right_pressed = pyqtSignal()
        right_released = pyqtSignal()
        toggle_persistent = pyqtSignal()

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("洞见")
    app.setOrganizationName("洞见")
    app.setQuitOnLastWindowClosed(False)  # 无主窗口,关窗不退出

    # ── 单实例:重复启动直接退出 ──
    shared = QSharedMemory("洞见V2Singleton")
    if shared.attach() or not shared.create(1):
        print("洞见已在运行。")
        sys.exit(0)

    from pynput import mouse
    from qfluentwidgets import Theme, qconfig

    from src.config import Config, load_config
    from src.hotkey import HotkeyManager
    from src.magnifier import MagnifierWindow
    from src.settings_window import SettingsWindow, set_autostart
    from src.tray import TrayController

    config = load_config()
    qconfig.set(qconfig.themeMode, Theme.AUTO)  # 跟随系统主题

    magnifier = MagnifierWindow(config)

    # ── 设置窗口:懒创建单实例,关窗隐藏不退出 ──
    _settings_win = {"win": None}

    def _open_settings() -> None:
        win = _settings_win["win"]
        if win is None:
            win = SettingsWindow(config)
            _settings_win["win"] = win
        win.show()
        win.raise_()
        win.activateWindow()

    tray = TrayController(config, magnifier, on_open_settings=_open_settings)
    tray.show()

    # ── 右键 peek:按下弹出并跟随,松开收回 ──
    bridge = _MouseBridge()
    bridge.right_pressed.connect(
        lambda: magnifier.pop() if config.right_click.value and not magnifier.is_persistent else None
    )
    bridge.right_released.connect(
        lambda: None if magnifier.is_persistent else magnifier.retract()
    )
    bridge.toggle_persistent.connect(
        lambda: magnifier.set_persistent(not magnifier.is_persistent)
    )

    def _on_click(_x, _y, button, pressed):
        if button == mouse.Button.right:
            (bridge.right_pressed if pressed else bridge.right_released).emit()

    listener = mouse.Listener(on_click=_on_click)
    listener.daemon = True
    listener.start()

    # ── 全局热键:切换常驻跟随 ──
    hotkey_manager = HotkeyManager(bridge.toggle_persistent.emit)
    hotkey_manager.set_hotkey(config.hotkey.value)

    # ── 配置变更实时生效 ──
    config.zoom.valueChanged.connect(lambda _v: magnifier.apply_config())
    config.size.valueChanged.connect(lambda _v: magnifier.apply_config())
    config.offset.valueChanged.connect(lambda _v: magnifier.apply_config())
    config.hotkey.valueChanged.connect(lambda _v: hotkey_manager.set_hotkey(config.hotkey.value))
    config.autostart.valueChanged.connect(lambda _v: set_autostart(bool(config.autostart.value)))

    # ── 启动项:注册表自启同步 + 启动即跟随 ──
    set_autostart(bool(config.autostart.value))
    if config.follow_on_start.value:
        magnifier.set_persistent(True)

    if os.environ.get("DONGJIAN_SELFTEST"):
        _run_selftest(app, magnifier)

    sys.exit(app.exec())


if __name__ == "__main__":
    _ensure_deps()
    main()
