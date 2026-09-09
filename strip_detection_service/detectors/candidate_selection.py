from dataclasses import dataclass

import numpy as np

from strip_detection_service.detectors.base import DetectedBox


COUNT_MISMATCH_WEIGHT = 0.30


@dataclass(frozen=True)
class DetectionCandidate:
    polarity: str
    boxes: tuple[DetectedBox, ...]
    score: float


def score_detection_candidate(
    boxes: list[DetectedBox] | tuple[DetectedBox, ...],
    image_shape: tuple[int, ...],
) -> float:
    if not boxes:
        return float("-inf")

    image_height = image_shape[0]
    confidence = float(np.mean([box.confidence for box in boxes]))
    aspect = float(
        np.mean(
            [
                min(1.0, box.width / max(1.0, box.height))
                for box in boxes
            ]
        )
    )
    centers_x = np.asarray(
        [box.x + box.width / 2 for box in boxes],
        dtype=np.float64,
    )
    centers_y = np.asarray(
        [box.y + box.height / 2 for box in boxes],
        dtype=np.float64,
    )
    if len(boxes) >= 3:
        slope, intercept = np.polyfit(centers_x, centers_y, 1)
        residuals = centers_y - (slope * centers_x + intercept)
    else:
        residuals = centers_y - float(np.mean(centers_y))
    alignment = 1.0 - min(
        1.0,
        float(np.std(residuals)) / max(1.0, image_height * 0.15),
    )
    full_height_penalty = (
        sum(box.height >= image_height * 0.75 for box in boxes)
        / len(boxes)
    )

    if len(centers_x) >= 3:
        spacings = np.diff(centers_x)
        spacing_consistency = 1.0 - min(
            1.0,
            float(np.std(spacings)) / max(1.0, float(np.mean(spacings))),
        )
    else:
        spacing_consistency = 0.0

    return (
        confidence
        + aspect
        + alignment
        + spacing_consistency
        - full_height_penalty
    )


def _selection_score(
    candidate: DetectionCandidate,
    expected_count: int,
) -> float:
    count_gap = abs(len(candidate.boxes) - expected_count) / max(
        1,
        expected_count,
    )
    return candidate.score - COUNT_MISMATCH_WEIGHT * min(1.0, count_gap)


def select_detection_candidate(
    dark_candidate: DetectionCandidate,
    light_candidate: DetectionCandidate,
    expected_count: int,
) -> DetectionCandidate:
    dark_score = _selection_score(dark_candidate, expected_count)
    light_score = _selection_score(light_candidate, expected_count)
    if dark_score != light_score:
        return dark_candidate if dark_score > light_score else light_candidate
    return dark_candidate
