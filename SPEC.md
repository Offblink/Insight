# Implementation Plan: 洞见 v2 — 圆形鼠标放大镜

## Design Reference
`DESIGN.md`(同目录)，已批准:触发 = 右键 peek + 全局热键常驻;位置 = `洞见/v2/`。

## Component Map

```
NEW FILES:
- main.pyw                 入口:依赖自检、单实例、QApplication、组装、事件循环
- requirements.txt         PyQt6 / PyQt6-Fluent-Widgets / pynput
- src/__init__.py
- src/config.py            QSettings 封装(默认值 + 类型转换 + 变更信号)
- src/capturer.py          屏幕捕获:多屏 clamp、HiDPI 校正、QScreen.grabWindow
- src/magnifier.py         圆形放大镜窗口:动画(pop/retract)、绘制、peek/常驻跟随
- src/hotkey.py            全局热键(pynput GlobalHotKeys)，切换常驻跟随
- src/tray.py              托盘:图标(运行时绘制)、菜单、双击
- src/settings_window.py   设置窗口:FramelessWindow + SettingCardGroup
- tests/smoke.py           自测脚本(离屏逻辑 + 真机冒烟)
```

## Tasks

### Task 1: 脚手架与静默托盘启动
**What:** 应用可启动、单实例、托盘图标出现、无窗口。
**Files:** `main.pyw`, `requirements.txt`, `src/__init__.py`, `src/config.py`
**Acceptance:**
- [ ] `python main.pyw` 启动无报错，3 秒内无异常输出
- [ ] 再次启动第二个实例立即退出(单实例门)
- [ ] 托盘出现"洞见"图标(运行时绘制的放大镜图标)
- [ ] `config.py` 读写往返正确(临时 QSettings 路径)

### Task 2: 放大镜核心 + 右键 peek
**Files:** `src/capturer.py`, `src/magnifier.py`, `main.pyw`(挂载 pynput 鼠标钩子)
**Acceptance:**
- [ ] 右键按下 → 光标处弹出圆形放大镜(OutBack 弹性 220ms)
- [ ] 按住拖动 → 跟随鼠标，内容实时放大(30fps)
- [ ] 松开 → InCubic 150ms 收回
- [ ] 多屏:副屏(含负坐标)抓取正确;HiDPI 下无模糊错位
- [ ] 冒烟:程序化触发 pop→retract→quit，无异常，抓取 pixmap 非空

### Task 3: 全局热键常驻跟随
**Files:** `src/hotkey.py`, `main.pyw`
**Acceptance:**
- [ ] 默认 `Ctrl+Alt+M` 切换常驻跟随模式(显示 + 跟随，与鼠标键无关)
- [ ] 再按一次收回
- [ ] 热键字符串可配置，监听器随配置重启

### Task 4: 托盘完整菜单
**Files:** `src/tray.py`, `main.pyw`
**Acceptance:**
- [ ] 菜单:倍率预设(1.5x/2x/2.5x/3x/5x)、跟随模式(勾选)、设置…、退出
- [ ] 双击托盘 = 切换常驻跟随
- [ ] 倍率预设立即生效并同步 config
- [ ] 退出真正结束进程

### Task 5: 设置窗口
**Files:** `src/settings_window.py`, `main.pyw`(托盘"设置…"打开)
**Acceptance:**
- [ ] FramelessWindow + SettingCardGroup，Windows 11 设置质感
- [ ] 倍率 1.0–8.0、大小 120–400、偏移 0–60 滑杆，改动实时生效
- [ ] 右键触发开关、常驻热键输入、启动时跟随开关
- [ ] 开机自启(注册表 Run)开关
- [ ] 关窗隐藏不退出;从托盘可重新打开(单实例设置窗口)

### Task 6: 打磨与收尾
**Files:** 相关模块
**Acceptance:**
- [ ] 光标图标绘制在放大镜中心;十字准星样式统一为主题色
- [ ] 全量冒烟通过，无未提交改动
- [ ] 提交信息清晰

## Execution Strategy
- 顺序执行 1→6(每步依赖上一步)。
- 每 Task 完成后:`python main.pyw` 或自测脚本验证 → git commit。
- Checkpoint:Task 4 完成后请用户真机体验托盘/热键/peek，再进 Task 5。

## Global Constraints

### Style
- Python 3.13，PyQt6;类型注解;docstring 中文。
- 模块职责单一;不引入未在 spec 中的抽象。
- 修复 v1 缺陷(多屏、HiDPI)时不改 v1 文件。

### Testing
- 自测:`tests/smoke.py`(config 往返、动画属性、pop/retract 冒烟)。
- GUI 交互(托盘点击、右键手感)以真机运行验证，代码走查兜底。

### Boundaries
- 每次 commit 前必须能启动无报错。
- ASK FIRST:加依赖、改接口、动 DESIGN.md。
- NEVER:提交 secrets、删除 v1 文件、添加 spec 外功能。

### Interface Contracts
- `config.py`:`Config` 单例，`get/set(key, value)`，变更发 `changed(str key)` 信号(线程安全:信号跨线程 queued)。
- `capturer.py`:`Capturer.grab(cx, cy, grab_size) -> QPixmap`(逻辑坐标，已按 DPR 缩放)。
- `magnifier.py`:`pop() / retract() / set_persistent(bool) / apply_config(config)`。
- `hotkey.py`:`HotkeyManager(callback) / set_hotkey(str) / start() / stop()`。
- `tray.py`:`TrayController(config, magnifier, open_settings, quit)`。
- 跨线程:pynput 回调线程 → Qt 主线程一律经信号，禁止直接操作 widget。
