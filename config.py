from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = PROJECT_ROOT / "assets" / "templates"

WINDOW_TITLE = "绝区零"
TARGET_FPS = 10
MATCH_THRESHOLD = 0.95
MIN_CLICK_INTERVAL_SECONDS = 0.5


@dataclass(frozen=True)
class TemplateConfig:
    filename: str
    roi: tuple[int, int, int, int]

    @property
    def path(self) -> Path:
        return TEMPLATE_DIR / self.filename


TEMPLATE_CONFIGS = (
    TemplateConfig("confirm.png", (960, 600, 300, 140)),
    TemplateConfig("skip_btn.png", (1622, 30, 243, 137)),
    TemplateConfig("skip_menu.png", (1622, 100, 243, 67)),
    TemplateConfig("auto_btn.png", (1622, 100, 243, 67)),
    TemplateConfig("dialog_main.png", (1420, 552, 68, 252)),
    TemplateConfig("dialog_warn.png", (1420, 552, 68, 252)),
    TemplateConfig("dialog_normal.png", (1420, 552, 68, 252)),
    TemplateConfig("skip_dialog.png", (1465, 977, 40, 35)),
    TemplateConfig("skip_black.png", (935, 550, 56, 186)),
)

PRIORITY_ORDER = tuple(config.filename for config in TEMPLATE_CONFIGS)
