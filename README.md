# Insight（洞见）

> 一个轻快、顺滑的圆形屏幕放大镜，Windows 系统托盘常驻。

按住 **Ctrl** 即可在光标处弹出圆形放大镜，松开收回；全局热键 **Ctrl+Alt+M** 切换常驻跟随。无主窗口，启动即静默驻留托盘。

## 特性

- **Ctrl 即看即走**：按住 Ctrl 弹出圆形放大镜并跟随光标，松开收回；OutBack 弹性动画，顺滑不抢眼
- **常驻跟随**：全局热键（默认 Ctrl+Alt+M）切换跟随模式，边移动边放大
- **托盘常驻**：倍率预设（1.5x–5x）、跟随模式开关、设置、退出；双击托盘切换跟随
- **多屏 + HiDPI**：虚拟桌面坐标抓取，副屏（含负坐标）与 150%/200% 缩放正确
- **Fluent 设置窗口**：倍率/大小/偏移实时生效；热键点击后直接按键录入；开机自启；一键恢复默认
- **细节**：单实例（重复启动弹系统通知提醒）、缺失依赖自动安装、配置 JSON 持久化、启动系统通知

## 快速开始

需要 Python 3.13+:

```bash
pip install -r requirements.txt
python main.pyw         # 或 pythonw main.pyw（无控制台窗口）
```

## 使用

| 操作 | 效果 |
| --- | --- |
| 按住 Ctrl | 光标处弹出放大镜并跟随，松开收回 |
| Ctrl + Alt + M | 切换常驻跟随模式 |
| 托盘 · 倍率预设 | 快捷切换 1.5x / 2x / 2.5x / 3x / 5x |
| 双击托盘图标 | 切换常驻跟随模式 |
| 托盘 · 设置… | 打开设置窗口 |

## 设置

| 项 | 说明 |
| --- | --- |
| 放大倍数 | 1.0 – 8.0x |
| 窗口大小 | 120 – 400 px |
| 偏移距离 | 放大镜相对光标偏移 0 – 60 px（边缘自动翻转） |
| Ctrl 触发 | 开关 Ctrl peek |
| 常驻热键 | 点击卡片后直接按新组合键录入（须含 Ctrl/Alt） |
| 启动时跟随 | 启动后直接进入常驻跟随 |
| 开机自启 | 写入 HKCU Run 键，登录自动静默启动 |

配置保存在应用目录 `config.json`，删除即恢复默认。

## 开发

```bash
python tests/smoke.py             # 冒烟测试（config/捕获/热键/托盘/设置/动画）
DONGJIAN_SELFTEST=1 python main.pyw  # 自动化自测：弹出→收回→退出
```

## 结构

```
main.pyw              入口：单实例、依赖自检、组装
src/config.py         QConfig 配置（JSON 持久化）
src/capturer.py       多屏 + HiDPI 屏幕捕获
src/magnifier.py      圆形放大镜窗口（弹性动画、30fps 跟随）
src/hotkey.py         全局键盘监听（Ctrl peek + 组合热键）
src/tray.py           托盘（图标、菜单、双击）
src/settings_window.py Fluent 设置窗口 + 开机自启
tests/smoke.py        冒烟测试
```

## 技术栈

PyQt6 · PyQt-Fluent-Widgets(qfluentwidgets)· pynput

## 许可

MIT
