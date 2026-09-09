from dataclasses import dataclass
from typing import Mapping, Sequence

import cv2
import numpy as np


@dataclass(frozen=True)
class RoiTransform:
    original_to_roi: np.ndarray
    roi_to_original: np.ndarray
    width: int
    height: int


def _polygon_array(polygon: Sequence[Mapping[str, float]]) -> np.ndarray:
    if len(polygon) != 4:
        raise ValueError("ROI polygon must contain exactly four points")

    points = np.asarray(
        [[float(point["x"]), float(point["y"])] for point in polygon],
        dtype=np.float32,
    )
    if not np.isfinite(points).all():
        raise ValueError("ROI polygon points must be finite")
    if len(np.unique(points, axis=0)) != 4:
        raise ValueError("ROI polygon must contain four distinct points")
    return points


def rectify_roi(
    image: np.ndarray,
    polygon: Sequence[Mapping[str, float]],
) -> tuple[np.ndarray, RoiTransform]:
    points = _polygon_array(polygon)
    image_height, image_width = image.shape[:2]
    if (
        (points[:, 0] < 0).any()
        or (points[:, 0] > image_width).any()
        or (points[:, 1] < 0).any()
        or (points[:, 1] > image_height).any()
    ):
        raise ValueError("ROI polygon must stay inside the original image")

    top_width = np.linalg.norm(points[1] - points[0])
    bottom_width = np.linalg.norm(points[2] - points[3])
    left_height = np.linalg.norm(points[3] - points[0])
    right_height = np.linalg.norm(points[2] - points[1])
    width = int(round(max(top_width, bottom_width)))
    height = int(round(max(left_height, right_height)))
    if width < 1 or height < 1:
        raise ValueError("ROI polygon must have a positive area")

    target = np.asarray(
        [[0, 0], [width, 0], [width, height], [0, height]],
        dtype=np.float32,
    )
    original_to_roi = cv2.getPerspectiveTransform(points, target)
    roi_to_original = cv2.getPerspectiveTransform(target, points)
    roi_image = cv2.warpPerspective(image, original_to_roi, (width, height))
    return roi_image, RoiTransform(
        original_to_roi=original_to_roi,
        roi_to_original=roi_to_original,
        width=width,
        height=height,
    )


def map_roi_box_to_original(
    box: Mapping[str, float],
    transform: RoiTransform,
) -> list[dict[str, float]]:
    x = float(box["x"])
    y = float(box["y"])
    width = float(box["width"])
    height = float(box["height"])
    corners = np.asarray(
        [[[x, y], [x + width, y], [x + width, y + height], [x, y + height]]],
        dtype=np.float32,
    )
    mapped = cv2.perspectiveTransform(corners, transform.roi_to_original)[0]
    return [
        {"x": round(float(point[0]), 6), "y": round(float(point[1]), 6)}
        for point in mapped
    ]
