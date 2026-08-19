"""全局热键:pynput GlobalHotKeys,切换常驻跟随模式。

回调运行在 pynput 监听线程;调用方需自行桥接到 Qt 主线程(经信号)。
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


def _to_pynput(hotkey: str) -> str:
    """'ctrl+alt+m' → '<ctrl>+<alt>+m'(pynput 语法)。"""
    parts = []
    for token in hotkey.lower().split("+"):
        token = token.strip()
        if token in _SPECIAL:
            parts.append(_SPECIAL[token])
        elif _FKEY.match(token):
            parts.append(f"<{token}>")
        else:
            parts.append(token)
    return "+".join(parts)


class HotkeyManager:
    """管理单个全局热键;set_hotkey 会重启监听器。"""

    def __init__(self, callback):
        self._callback = callback
        self._listener: keyboard.GlobalHotKeys | None = None

    def set_hotkey(self, hotkey: str) -> None:
        self.stop()
        hotkey = (hotkey or "").strip()
        if not hotkey:
            return
        self._listener = keyboard.GlobalHotKeys({_to_pynput(hotkey): self._callback})
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
