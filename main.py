from __future__ import annotations

import logging
import time

import cv2
import win32gui
from zbl import Capture

from config import (
    MATCH_THRESHOLD,
    MIN_CLICK_INTERVAL_SECONDS,
    PRIORITY_ORDER,
    TARGET_FPS,
    TEMPLATE_CONFIGS,
    WINDOW_TITLE,
)
from template_matching import TemplateMatch, find_matches, load_templates
from windowing import HwndWindow, Interaction


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def pick_match_by_priority(matches: list[TemplateMatch]) -> TemplateMatch | None:
    matches_by_name = {match.template_name: match for match in matches}
    for template_name in PRIORITY_ORDER:
        match = matches_by_name.get(template_name)
        if match is not None:
            return match
    return None


def main() -> None:
    hwnd = win32gui.FindWindow(None, WINDOW_TITLE)
    if not hwnd:
        logger.error("Could not find ZZZ window: %s", WINDOW_TITLE)
        return
    logger.info("Found HWND: %s", hwnd)

    hwnd_window = HwndWindow(hwnd)
    interaction = Interaction(hwnd_window)
    templates = load_templates(TEMPLATE_CONFIGS)
    logger.info("Loaded %s templates", len(templates))
    logger.info("Capture started. Press Ctrl+C to stop.")

    frame_time = 1.0 / TARGET_FPS
    last_frame_time = time.perf_counter()
    last_click_time = 0.0

    try:
        with Capture(window_handle=hwnd) as capture:
            while True:
                current_time = time.perf_counter()
                elapsed = current_time - last_frame_time
                if elapsed < frame_time:
                    time.sleep(frame_time - elapsed)
                    continue

                frame = capture.grab()
                if frame is None or frame.size <= 0:
                    logger.warning("Captured an empty frame")
                    continue

                source_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                matches = find_matches(source_gray, templates, threshold=MATCH_THRESHOLD)
                selected_match = pick_match_by_priority(matches)

                if (
                    selected_match is not None
                    and current_time - last_click_time >= MIN_CLICK_INTERVAL_SECONDS
                ):
                    interaction.click(*selected_match.position)
                    logger.info(
                        "Matched template %s, score=%.3f, position=%s",
                        selected_match.template_name,
                        selected_match.score,
                        selected_match.position,
                    )
                    last_click_time = current_time

                interaction.on_visible(hwnd_window.is_foreground())
                last_frame_time = current_time
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        interaction.close()


if __name__ == "__main__":
    main()
