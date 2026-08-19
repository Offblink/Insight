"""全局键盘输入:单一监听器，同时处理 Ctrl 按住 peek 与热键组合切换常驻。

回调运行在 pynput 监听线程;调用方需自行桥接到 Qt 主线程(经信号)。
边缘触发:Ctrl 从无到有 = peek_start(重复按下不重复触发)，全部释放 = peek_end;
组合键首次完整按下 = toggle。
"""

import re

from pynput import keyboard

_SPECIAL = {
    "ctrl": "<ctrl>", "control": "<ctrl>",
    "alt": "<alt>",
    "shift": "<shift>",
    "win": "<cmd>", "super": "<cmd>", "cmd": "<cmd>", "windows": "<cmd>",
    "esc": "<esc>", "tab": "<tab>", "space": "<space>",
    "enter": "<enter>", "return": "<enter>",
    "insert": "<insert>", "delete": "<delete>", "backspace": "<backspace>",
    "home": "<home>", "end": "<end>", "pageup": "<page_up>", "pagedown": "<page_down>",
    "up": "<up>", "down": "<down>", "left": "<left>", "right": "<right>",
    "capslock": "<caps_lock>",
}

_FKEY = re.compile(r"^f([1-9]|1[0-9]|2[0-4])$")


def _normalize_token(token: str) -> str:
    """'ctrl' → '<ctrl>','m' → 'm','f5' → '<f5>'。"""
    token = token.strip().lower()
    if token in _SPECIAL:
        return _SPECIAL[token]
    if _FKEY.match(token):
        return f"<{token}>"
    return token


def parse_hotkey(hotkey: str) -> set[str]:
    """'ctrl+alt+m' → {'<ctrl>', '<alt>', 'm'}。"""
    return {_normalize_token(t) for t in (hotkey or "").split("+") if t.strip()}


def _key_token(key) -> str:
    """pynput key 事件 → 归一化 token;不支持/忽略的键返回 ''。"""
    if isinstance(key, keyboard.KeyCode):
        ch = key.char
        return ch.lower() if ch and ch.isprintable() else ""
    name = key.name
    if name in ("ctrl_l", "ctrl_r"):
        return "<ctrl>"
    if name in ("alt_l", "alt_r", "alt_gr"):
        return "<alt>"
    if name in ("shift", "shift_l", "shift_r"):
        return "<shift>"
    if name in ("cmd", "cmd_l", "cmd_r"):
        return "<cmd>"
    if name.startswith("f") and name[1:].isdigit():
        return f"<{name}>"
    return ""


class InputController:
    """统一键盘监听:Ctrl 按住 = peek，热键组合 = 常驻跟随。"""

    def __init__(self, hotkey: str, on_peek_start, on_peek_end, on_toggle):
        self._required = parse_hotkey(hotkey)
        self._pressed: set[str] = set()
        self._combo_done = False
        self._ctrl_keys: set = set()  # 实际按住的 Ctrl 键对象(去重，防按住重复 press)
        self._peek_active = False
        self.on_peek_start = on_peek_start
        self.on_peek_end = on_peek_end
        self.on_toggle = on_toggle
        self._listener = None

    def start(self) -> None:
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def set_hotkey(self, hotkey: str) -> None:
        self._required = parse_hotkey(hotkey)
        self._combo_done = False

    # ── 事件(可直调用于测试)──
    def _on_press(self, key) -> None:
        token = _key_token(key)
        if not token:
            return
        if token == "<ctrl>":
            if not self._ctrl_keys:  # 首次按下才触发，重复 press 不重复弹
                self._peek_active = True
                self.on_peek_start()
            self._ctrl_keys.add(key)
        self._pressed.add(token)
        if self._required and self._required <= self._pressed and not self._combo_done:
            self._combo_done = True
            self.on_toggle()

    def _on_release(self, key) -> None:
        token = _key_token(key)
        if not token:
            return
        if token == "<ctrl>":
            self._ctrl_keys.discard(key)
            if not self._ctrl_keys and self._peek_active:  # 全部 Ctrl 松开才收回
                self._peek_active = False
                self.on_peek_end()
        self._pressed.discard(token)
        if not (self._required <= self._pressed):
            self._combo_done = False
