from __future__ import annotations

import ctypes
import logging
import time
from ctypes import wintypes
from typing import Callable, TypeVar

import win32api
import win32con
import win32gui


logger = logging.getLogger(__name__)
T = TypeVar("T")


class HwndWindow:
    def __init__(self, hwnd: int):
        self.hwnd = hwnd

    @property
    def width(self) -> int:
        rect = win32gui.GetWindowRect(self.hwnd)
        return rect[2] - rect[0]

    @property
    def height(self) -> int:
        rect = win32gui.GetWindowRect(self.hwnd)
        return rect[3] - rect[1]

    def is_foreground(self) -> bool:
        return win32gui.GetForegroundWindow() == self.hwnd


class Interaction:
    def __init__(self, hwnd_window: HwndWindow):
        self.hwnd_window = hwnd_window
        self.user32 = ctypes.windll.user32
        self.gdi32 = ctypes.windll.gdi32
        self.cursor_position: tuple[int, int] | None = None
        self.empty_cursor = self._create_empty_cursor()
        self.cursor_ids = [
            32512,
            32513,
            32514,
            32515,
            32516,
            32640,
            32641,
            32642,
            32643,
            32644,
            32645,
            32646,
            32648,
            32649,
            32650,
            32651,
            32671,
            32672,
            32673,
            32674,
            32675,
            32676,
            32677,
            32678,
            32679,
            32680,
        ]

    @property
    def hwnd(self) -> int:
        return self.hwnd_window.hwnd

    @property
    def width(self) -> int:
        return self.hwnd_window.width

    @property
    def height(self) -> int:
        return self.hwnd_window.height

    def _create_empty_cursor(self) -> int:
        bitmap = self.gdi32.CreateBitmap(1, 1, 1, 1, None)
        mask = self.gdi32.CreateBitmap(1, 1, 1, 1, None)
        cursor = self.user32.CreateCursor(
            0,
            0,
            0,
            1,
            1,
            ctypes.cast(
                ctypes.byref(ctypes.c_void_p(bitmap)),
                ctypes.POINTER(wintypes.LPBYTE),
            ),
            ctypes.cast(
                ctypes.byref(ctypes.c_void_p(mask)),
                ctypes.POINTER(wintypes.LPBYTE),
            ),
        )
        self.gdi32.DeleteObject(bitmap)
        self.gdi32.DeleteObject(mask)
        return cursor

    def operate(self, action: Callable[[], T]) -> T | None:
        is_background = not self.hwnd_window.is_foreground()
        result: T | None = None
        if is_background:
            self.hide_cursor()
            self.block_input()
            self.cursor_position = win32api.GetCursorPos()
            self.activate()
            time.sleep(0.02)

        try:
            result = action()
        except Exception:
            logger.exception("Interaction failed")
        finally:
            if is_background:
                self.deactivate()
                if self.cursor_position is not None:
                    win32api.SetCursorPos(self.cursor_position)
                self.unblock_input()
                self.show_cursor()
        return result

    def activate(self) -> None:
        self.post(win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)

    def deactivate(self) -> None:
        self.post(win32con.WM_ACTIVATE, win32con.WA_INACTIVE, 0)

    def block_input(self) -> None:
        self.user32.BlockInput(True)

    def unblock_input(self) -> None:
        self.user32.BlockInput(False)

    def post(self, message: int, w_param: int = 0, l_param: int = 0) -> None:
        win32gui.PostMessage(self.hwnd, message, w_param, l_param)

    def click(
        self,
        x: int = -1,
        y: int = -1,
        down_time: float = 0.02,
        key: str = "left",
    ) -> None:
        self.operate(lambda: self._do_click(x, y, down_time=down_time, key=key))

    def _do_click(
        self,
        x: int = -1,
        y: int = -1,
        down_time: float = 0.02,
        key: str = "left",
    ) -> None:
        click_position = self._make_mouse_position(x, y)
        logger.debug(
            "Click at x=%s, y=%s, l_param=%s, down_time=%s",
            x,
            y,
            click_position,
            down_time,
        )

        if key == "left":
            button_down = win32con.WM_LBUTTONDOWN
            button_mask = win32con.MK_LBUTTON
            button_up = win32con.WM_LBUTTONUP
        elif key == "middle":
            button_down = win32con.WM_MBUTTONDOWN
            button_mask = win32con.MK_MBUTTON
            button_up = win32con.WM_MBUTTONUP
        else:
            button_down = win32con.WM_RBUTTONDOWN
            button_mask = win32con.MK_RBUTTON
            button_up = win32con.WM_RBUTTONUP

        self.post(button_down, button_mask, click_position)
        self.post(button_up, 0, click_position)
        time.sleep(down_time)

    def _make_mouse_position(self, x: int, y: int) -> int:
        if x < 0:
            return win32api.MAKELONG(round(self.width * 0.5), round(self.height * 0.5))

        absolute_x, absolute_y = win32gui.ClientToScreen(self.hwnd, (x, y))
        click_position = win32api.MAKELONG(x, y)
        win32api.SetCursorPos((absolute_x, absolute_y))
        time.sleep(0.001)
        return click_position

    def on_visible(self, visible: bool) -> None:
        if visible:
            self.activate()

    def hide_cursor(self) -> None:
        for cursor_id in self.cursor_ids:
            cursor_copy = self.user32.CopyIcon(self.empty_cursor)
            self.user32.SetSystemCursor(cursor_copy, cursor_id)

    def show_cursor(self) -> None:
        self.user32.SystemParametersInfoW(0x0057, 0, None, 0)

    def close(self) -> None:
        self.user32.DestroyCursor(self.empty_cursor)
