import time
import logging

import win32gui
import win32api
import win32con
import ctypes
import cv2
from zbl import Capture

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class HwndWindow:
    def __init__(self, hwnd: int):
        self.hwnd = hwnd

    @property
    def width(self):
        rect = win32gui.GetWindowRect(self.hwnd)
        return rect[2] - rect[0]

    @property
    def height(self):
        rect = win32gui.GetWindowRect(self.hwnd)
        return rect[3] - rect[1]

    def is_foreground(self):
        fg_hwnd = win32gui.GetForegroundWindow()
        return fg_hwnd == self.hwnd

class Interaction:
    def __init__(self, hwnd_window):
        self.hwnd_window = hwnd_window
        self.user32 = ctypes.windll.user32
        self.cursor_position = None

    @property
    def hwnd(self):
        return self.hwnd_window.hwnd

    @property
    def width(self):
        return self.hwnd_window.hwnd.width

    @property
    def height(self):
        return self.hwnd_window.hwnd.height

    def operate(self, fun, block=True):
        bg = not self.hwnd_window.is_foreground()
        result = None
        if bg:
            if block:
                self.block_input()
            self.cursor_position = win32api.GetCursorPos()
            self.activate()
        try:
            result = fun()
        except Exception as e:
            logger.error(f'操作异常', e)
        if bg:
            self.deactivate()
            time.sleep(0.02)
            win32api.SetCursorPos(self.cursor_position)
            if block:
                self.unblock_input()
        return result

    def activate(self):
        self.hwnd_window.to_handle_mute = False
        self.post(win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)

    def deactivate(self):
        self.post(win32con.WM_ACTIVATE, win32con.WA_INACTIVE, 0)
        self.hwnd_window.to_handle_mute = True

    def try_activate(self):
        if not self.hwnd_window.is_foreground():
            self.activate()

    def block_input(self):
        self.user32.BlockInput(True)

    def unblock_input(self):
        self.user32.BlockInput(False)

    def post(self, message, wParam=0, lParam=0):
        win32gui.PostMessage(self.hwnd, message, wParam, lParam)

    def click(self, x=-1, y=-1, down_time=0.02, key="left"):
        self.operate(lambda: self.do_click(x, y, down_time=down_time, key=key), block=True)

    def do_click(self, x=-1, y=-1, down_time=0.02, key="left"):
        click_pos = self.make_mouse_position(x, y)
        logger.debug(f'点击 {x}, {y}, {click_pos} {down_time}')
        if key == "left":
            btn_down = win32con.WM_LBUTTONDOWN
            btn_mk = win32con.MK_LBUTTON
            btn_up = win32con.WM_LBUTTONUP
        elif key == "middle":
            btn_down = win32con.WM_MBUTTONDOWN
            btn_mk = win32con.MK_MBUTTON
            btn_up = win32con.WM_MBUTTONUP
        else:
            btn_down = win32con.WM_RBUTTONDOWN
            btn_mk = win32con.MK_RBUTTON
            btn_up = win32con.WM_RBUTTONUP
        self.post(btn_down, btn_mk, click_pos)
        self.post(btn_up, 0, click_pos)
        time.sleep(down_time)

    def make_mouse_position(self, x, y):
        if x < 0:
            click_pos = win32api.MAKELONG(round(self.width * 0.5), round(self.height * 0.5))
        else:
            abs_point = win32gui.ClientToScreen(self.hwnd, (x, y))  # 直接转换
            abs_x, abs_y = abs_point
            click_pos = win32api.MAKELONG(x, y)
            win32api.SetCursorPos((abs_x, abs_y))
            time.sleep(0.001)
        return click_pos

    def on_visible(self, visible):
        if visible:
            self.activate()

def find_matches(source_gray, templates, threshold=0.8):
    matches = []
    for template_gray, roi, path in templates:
        x1, y1, w, h = roi
        source_roi = source_gray[y1:y1 + h, x1:x1 + w]
        if source_roi.shape[0] < template_gray.shape[0] or source_roi.shape[1] < template_gray.shape[1]:
            continue
        res = cv2.matchTemplate(source_roi, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val > threshold:
            th, tw = template_gray.shape
            center_x = max_loc[0] + tw // 2 + x1
            center_y = max_loc[1] + th // 2 + y1
            matches.append((max_val, (center_x, center_y), path))
    return matches

def main():

    title = "绝区零"

    hwnd = win32gui.FindWindow(None, title)
    if not hwnd:
        logger.error("未找到 ZZZ 窗口!")
        return
    logger.info(f"找到 HWND: {hwnd}")

    hwnd_window = HwndWindow(hwnd)

    interaction = Interaction(hwnd_window)

    # 多个模板 + ROI
    template_configs = {
        'confirm.png': {'roi': (960, 600, 300, 90)},
        'skip_btn.png': {'roi': (1622, 100, 243, 67)},
        'skip_menu.png': {'roi': (1622, 100, 243, 67)},
        'dialog_main.png': {'roi': (1420, 552, 68, 252)},
        'dialog_warn.png': {'roi': (1420, 552, 68, 252)},
        'dialog_normal.png': {'roi': (1420, 552, 68, 252)},
        'skip_dialog.png': {'roi': (1465, 977, 40, 35)},
        'skip_black.png': {'roi': (935, 565, 56, 150)}
    }

    templates = []
    for path, config in template_configs.items():
        temp = cv2.imread(path, 0)
        if temp is not None:
            templates.append((temp, config['roi'], path))
        else:
            logger.warning(f"模板 {path} 加载失败")

    # 优先级列表
    priority_order = ['confirm.png', 'skip_btn.png', 'skip_menu.png', 'dialog_main.png', 'dialog_warn.png',
                      'dialog_normal.png', 'skip_dialog.png', 'skip_black.png']

    logger.info(f"加载 {len(templates)} 个模板")

    target_fps = 10
    frame_time = 1.0 / target_fps
    last_frame_time = time.perf_counter()

    logger.info("开始捕获, Ctrl+C 停止")

    last_click_time = 0.0

    try:
        with Capture(window_name=title) as cap:
            while True:
                current_time = time.perf_counter()
                if current_time - last_frame_time < frame_time:
                    time.sleep(frame_time - (current_time - last_frame_time))
                    continue

                frame = cap.grab()
                if frame is not None and frame.size > 0:
                    source_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                    matches = find_matches(source_gray, templates)

                    if matches:
                        path_to_match = {m[2]: m for m in matches}

                        if current_time - last_click_time >= 0.5:
                            for pri_path in priority_order:
                                if pri_path in path_to_match:
                                    match = path_to_match[pri_path]
                                    score, pos, path = match
                                    interaction.click(pos[0], pos[1])
                                    logger.info(f"优先匹配 模板 {path}, 分数: {score:.3f}, 位置: {pos}")
                                    last_click_time = current_time
                                    break

                    # 可见性检查
                    current_visible = hwnd_window.is_foreground()
                    interaction.on_visible(current_visible)

                    last_frame_time = current_time  # 更新帧时间

                else:
                    logger.warning("捕获帧为空")

    except KeyboardInterrupt:
        logger.info("用户停止")


if __name__ == '__main__':
    main()