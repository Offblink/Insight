"""配置持久化:QSettings 封装。

默认值见 DEFAULTS;set() 后发 changed(key) 信号,供各模块实时响应。
"""

from PyQt6.QtCore import QObject, QSettings, pyqtSignal


class Config(QObject):
    """应用配置单例(QSettings 持久化)。"""

    changed = pyqtSignal(str)  # 变更的 key

    DEFAULTS: dict = {
        "zoom": 2.5,          # 放大倍数 1.0–8.0
        "size": 220,          # 圆形直径 px 120–400
        "offset": 15,         # 圆心相对光标的偏移 px 0–60
        "right_click": True,  # 右键 peek 触发开关
        "hotkey": "ctrl+alt+m",  # 常驻跟随热键
        "follow_on_start": False,  # 启动即常驻跟随
        "autostart": False,   # 开机自启
    }

    def __init__(self, org: str = "洞见", app: str = "洞见"):
        super().__init__()
        self._settings = QSettings(org, app)
        for key, value in self.DEFAULTS.items():
            if not self._settings.contains(key):
                self._settings.setValue(key, value)
        self._settings.sync()

    def get(self, key: str):
        """按默认值类型强转读取。"""
        value = self._settings.value(key)
        default = self.DEFAULTS[key]
        if isinstance(default, bool):
            return str(value).strip().lower() in ("true", "1", "yes", "on")
        if isinstance(default, int):
            return int(value)
        if isinstance(default, float):
            return float(value)
        return str(value)

    def set(self, key: str, value) -> None:
        """写入并广播变更。"""
        self._settings.setValue(key, value)
        self._settings.sync()
        self.changed.emit(key)
