# Design: 洞见 v2 — 圆形鼠标放大镜(托盘常驻版)

## Problem

v1(`洞见.pyw`)启动即显示放大镜 + 控制台窗口,无托盘、无快捷键、只支持主屏、无全局鼠标钩子。
v2 目标:无主窗口、静默托盘常驻、右键即弹圆形放大镜、弹出/收回顺滑动画、
PyQt6 + PyQt-Fluent-Widgets 重写,作为"洞见"的 v2 版。

## Context

- v1 参考:圆形窗口(`QRegion.Ellipse` + `WA_TranslucentBackground`)、
  `QScreen.grabWindow` 捕获 + `SmoothTransformation` 放大、
  `QPropertyAnimation` 透明度动画、控制台窗口调参。
- MonaDrive 参考:单实例(`QSharedMemory` + `QLocalSocket`)、依赖自检自动安装
  (`_ensure_deps`)、`load_fonts`、托盘模式、`setQuitOnLastWindowClosed(False)`。
- 技术栈:PyQt6 + PyQt-Fluent-Widgets(qfluentwidgets)、pynput(全局鼠标钩子)、
  QSettings 持久化。
- 约束:Windows 11,Python 3.14(本机环境),无主窗口,静默启动。

## Options Considered

### 交互:触发方式

**A. 右键按下 = 弹出(圆心对准光标),按住 = 跟随,松开 = 收回**
- 优点:手势自然,零学习成本,符合"右键哪儿放大哪"。
- 缺点:右键按下也会触发目标应用的上下文菜单(多数应用在松键时弹);
  放大镜需在松键瞬间快速收回,且被放大镜遮挡处菜单不可见,可能造成困惑。
- 风险:与某些应用(按下即弹菜单)行为冲突。

**B. 纯热键切换跟随模式(ZoomIt 式)**
- 优点:完全不干扰系统右键。
- 缺点:有学习成本,不如"顺手"。

**C. A + B 组合:右键按住 = 临时放大镜(peek),全局热键 = 切换常驻跟随模式**
- 优点:peek 覆盖高频"瞄一眼"场景,热键覆盖"边看边移"场景;
  设置里可关闭右键触发,规避冲突。
- 缺点:多一个热键要记忆,实现略复杂。
- 风险:低。

### 设置入口

**A. 托盘菜单 = 动作,独立设置窗口 = 参数(推荐)**
- 托盘菜单:快捷倍率预设(1.5x / 2x / 3x / 5x)、启用/暂停、设置…、退出;
  双击托盘 = 切换常驻跟随。
- 设置窗口:`FramelessWindow` + `SettingCardGroup`(Windows 11 设置页质感),
  包含倍率、大小、触发方式、热键、跟随模式、开机自启等。
- 理由:滑杆/开关需要空间;托盘菜单保持轻量;qfluentwidgets 组件为此而生。

**B. 全塞托盘菜单**
- 缺点:放不下滑杆,交互差,违背 Fluent 设计语言。

### 渲染与捕获

**A. `QScreen.grabWindow` + QPainter 圆形裁剪(推荐起步)**
- `grabWindow(0, x, y, w, h)` 使用虚拟桌面坐标,天然支持多屏(含负坐标),
  修复 v1 只抓主屏的 bug。
- 性能:小区域 30–60fps 可行;动画期间只抓一次,缩放走 pixmap 变换。
- 抽象 `Capturer` 接口,性能不足时换 B。

**B. `mss` 库(Windows 上更快的 BitBlt)**
- 备选,仅当 A 实测不够时启用。

### 设置窗口形态

**A. `FramelessWindow` + `SettingCardGroup`(推荐)**
- 单页设置,Windows 11 设置风格,无导航开销。

**B. `FluentWindow` 带导航**
- 单页场景过重,不采用。

## Recommended

- 交互 **C**:右键按住 = peek + 跟随,全局热键 = 常驻跟随;设置可关右键触发。
- 动画:pop = scale 0.6→1.0 + opacity 0→1,`OutBack` 约 220ms;
  retract = scale→0.6 + opacity→0,`InCubic` 约 150ms。
- 结构:
  ```
  v2/
    main.pyw            入口:单实例、依赖自检、托盘、事件循环
    requirements.txt
    src/
      __init__.py
      config.py         QSettings 读写(倍率/大小/触发/热键/跟随)
      capturer.py       Capturer 接口 + grabWindow 实现(多屏/HiDPI 校正)
      magnifier.py      圆形放大镜窗口(动画、绘制、peek/跟随)
      hotkey.py         全局热键(pynput 或 win32 RegisterHotKey)
      tray.py           托盘(图标、菜单、双击)
      settings_window.py FramelessWindow + SettingCardGroup
  ```
- 配置:QSettings(OrganizationName=洞见, ApplicationName=洞见)。
- 细节:
  - 多屏支持(修复 v1 只抓主屏 bug);
  - HiDPI(`devicePixelRatio` 校正抓取区域);
  - 十字准星 + 主题色圆环(替代 v1 黑色粗边框);
  - 光标绘制(中心显示当前光标形状,增强真实感);
  - 开机自启(注册表 `Run` 键)。

## Open Questions

1. 触发方式:C 组合(右键 peek + 热键常驻)是否 OK?热键默认值?
2. 项目位置:`洞见/v2/` 子目录(保留 v1)还是覆盖 v1?
3. 默认倍率/大小(建议 2.5x / 220px,范围 1–8x / 120–400px)?

## 变更记录(实测后调整)

- 触发方式:右键 → **Ctrl 按住**。右键与系统上下文菜单冲突(松键弹菜单),Ctrl 按住无冲突且更顺手;设置项 `right_click` → `ctrl_peek`。
- 配置持久化:QSettings → **qfluentwidgets QConfig**(JSON,`config.json`),设置卡片原生绑定 ConfigItem,`qconfig.load()` 注册全局目标。
- 新增:启动系统通知(QSystemTrayIcon.showMessage)、设置窗口"恢复默认"按钮(逐项回 defaultValue)、热键键入感应(QKeySequenceEdit 捕获组合键)。
- 已知:QCursor.pixmap() 覆盖层在退出时确定性崩溃(exit 9),已移除;放大内容本身含光标(grabWindow 抓桌面 DC)。

