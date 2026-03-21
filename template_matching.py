from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import cv2

from config import TemplateConfig


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Template:
    name: str
    roi: tuple[int, int, int, int]
    image: Any


@dataclass(frozen=True)
class TemplateMatch:
    score: float
    position: tuple[int, int]
    template_name: str


def load_templates(template_configs: tuple[TemplateConfig, ...]) -> list[Template]:
    templates: list[Template] = []
    for config in template_configs:
        image = cv2.imread(str(config.path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            logger.warning("Failed to load template: %s", config.path)
            continue
        templates.append(Template(name=config.filename, roi=config.roi, image=image))
    return templates


def find_matches(
    source_gray: Any,
    templates: list[Template],
    threshold: float,
) -> list[TemplateMatch]:
    matches: list[TemplateMatch] = []
    for template in templates:
        x1, y1, width, height = template.roi
        source_roi = source_gray[y1 : y1 + height, x1 : x1 + width]
        if (
            source_roi.shape[0] < template.image.shape[0]
            or source_roi.shape[1] < template.image.shape[1]
        ):
            continue

        result = cv2.matchTemplate(source_roi, template.image, cv2.TM_CCOEFF_NORMED)
        _, max_value, _, max_location = cv2.minMaxLoc(result)
        if max_value <= threshold:
            continue

        template_height, template_width = template.image.shape
        center_x = max_location[0] + template_width // 2 + x1
        center_y = max_location[1] + template_height // 2 + y1
        matches.append(
            TemplateMatch(
                score=max_value,
                position=(center_x, center_y),
                template_name=template.name,
            )
        )
    return matches
