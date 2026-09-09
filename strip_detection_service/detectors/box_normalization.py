import math
from collections.abc import Sequence

import numpy as np

from strip_detection_service.detectors.base import DetectedBox


def _place_box(center: float, size: int, limit: int) -> int:
    return min(
        max(0, int(round(center - size / 2))),
        max(0, limit - size),
    )


def _layout_boxes(
    boxes: Sequence[DetectedBox],
    width: int,
    height: int,
    image_width: int,
    image_height: int,
) -> list[DetectedBox]:
    return [
        DetectedBox(
            x=_place_box(
                box.x + box.width / 2,
                width,
                image_width,
            ),
            y=_place_box(
                box.y + box.height / 2,
                height,
                image_height,
            ),
            width=width,
            height=height,
            confidence=box.confidence,
        )
        for box in boxes
    ]


def _has_horizontal_overlap(boxes: Sequence[DetectedBox]) -> bool:
    ordered = sorted(boxes, key=lambda box: box.x + box.width / 2)
    return any(
        left.x + left.width > right.x
        for left, right in zip(ordered, ordered[1:])
    )


def normalize_detection_box_sizes(
    boxes: Sequence[DetectedBox],
    image_shape: tuple[int, ...],
) -> list[DetectedBox]:
    if len(boxes) < 2:
        return list(boxes)

    image_height, image_width = image_shape[:2]
    centers_x = sorted(box.x + box.width / 2 for box in boxes)
    minimum_gap = min(
        right - left
        for left, right in zip(centers_x, centers_x[1:])
    )
    p75_width = math.ceil(
        float(np.percentile([box.width for box in boxes], 75))
    )
    p75_height = math.ceil(
        float(np.percentile([box.height for box in boxes], 75))
    )
    common_width = min(
        image_width,
        p75_width,
        max(1, math.floor(minimum_gap * 0.90)),
    )
    common_height = min(image_height, p75_height)

    for candidate_width in range(common_width, 0, -1):
        result = _layout_boxes(
            boxes,
            candidate_width,
            common_height,
            image_width,
            image_height,
        )
        if not _has_horizontal_overlap(result):
            return result

    raise AssertionError("A one-pixel common width must fit distinct boxes")
