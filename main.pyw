"""洞见 v2 — 圆形鼠标放大镜(托盘常驻版)。

启动即静默驻留托盘;右键按住 = 临时放大(peek),全局热键 = 常驻跟随。
Task 1:脚手架、单实例、托盘图标;放大镜逻辑在 Task 2 接入。
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


def main() -> None:
    from PyQt6.QtCore import Qt, QSharedMemory
    from PyQt6.QtWidgets import QApplication

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

    from src.config import Config
    from src.tray import TrayController

    config = Config()
    tray = TrayController(config)
    tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    _ensure_deps()
    main()
