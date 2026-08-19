"""配置:qfluentwidgets QConfig，JSON 持久化于应用目录。

设置卡片经全局 `qconfig.set(item, value)` 回写，因此必须用 `load_config()`
把 Config 实例注册到 qconfig(否则会存到 cwd 下的默认路径)。
"""

from pathlib import Path

from qfluentwidgets import (
    BoolValidator,
    ConfigItem,
    OptionsConfigItem,
    QConfig,
    RangeConfigItem,
    RangeValidator,
    qconfig,
)

DEFAULT_FILE = Path(__file__).resolve().parent.parent / "config.json"


class Config(QConfig):
    """应用配置项(类属性共享，JSON 持久化)。"""

    # 放大
    zoom = RangeConfigItem("放大", "zoom", 2.5, RangeValidator(1.0, 8.0))
    size = RangeConfigItem("放大", "size", 220, RangeValidator(120, 400))
    offset = RangeConfigItem("放大", "offset", 15, RangeValidator(0, 60))
    # 交互
    ctrl_peek = OptionsConfigItem("交互", "ctrl_peek", True, BoolValidator())
    hotkey = ConfigItem("交互", "hotkey", "ctrl+alt+m")
    follow_on_start = OptionsConfigItem("交互", "follow_on_start", False, BoolValidator())
    # 常规
    autostart = OptionsConfigItem("常规", "autostart", False, BoolValidator())


def load_config(file: str | Path | None = None) -> Config:
    """创建配置并注册到全局 qconfig;file 缺省为应用目录 config.json。"""
    cfg = Config()
    qconfig.load(str(file) if file is not None else str(DEFAULT_FILE), cfg)
    return cfg
