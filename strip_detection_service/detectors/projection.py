from dataclasses import dataclass

import numpy as np
from scipy import ndimage, signal as scipy_signal

from strip_detection_service.detectors.base import DetectedBox


SEPARATION_FACTOR = 0.55
ACTIVE_SUPPORT_FRACTION = 0.05
MAXIMUM_SPLIT_VALLEY_RATIO = 0.75
MINIMUM_CONFIDENCE = {
    "low": 0.45,
    "normal": 0.30,
    "high": 0.15,
}


def remove_column_baseline(feature_map: np.ndarray) -> np.ndarray:
    if not feature_map.size:
        return feature_map.copy()

    baseline = np.percentile(feature_map, 50, axis=0, keepdims=True)
    corrected = np.maximum(
        feature_map.astype(np.float64) - baseline,
        0,
    )
    maximum = float(corrected.max())
    if maximum > 0:
        corrected = corrected / maximum * 255
    return corrected.astype(np.uint8)


@dataclass(frozen=True)
class ProjectionIsland:
    start: int
    end: int
    center: float
    energy: float
    confidence: float

    @property
    def width(self) -> int:
        return self.end - self.start


def extract_projection_islands(
    signal: np.ndarray,
    minimum_width: int = 5,
) -> list[ProjectionIsland]:
    if not signal.size:
        return []

    maximum = float(np.max(signal))
    active_indices = np.where(
        signal > maximum * ACTIVE_SUPPORT_FRACTION
    )[0]
    if active_indices.size:
        active_signal = signal[
            active_indices[0]:active_indices[-1] + 1
        ]
    else:
        active_signal = signal
    threshold = float(np.mean(active_signal)) * SEPARATION_FACTOR
    labeled, island_count = ndimage.label(signal > threshold)
    raw = []
    for island_id in range(1, island_count + 1):
        indices = np.where(labeled == island_id)[0]
        if len(indices) < minimum_width:
            continue
        weights = signal[indices]
        energy = float(np.sum(weights))
        if energy <= 0:
            continue
        raw.append(
            (
                int(indices[0]),
                int(indices[-1]) + 1,
                float(np.sum(indices * weights) / energy),
                energy,
            )
        )

    maximum_energy = max((item[3] for item in raw), default=0.0)
    return [
        ProjectionIsland(
            start=start,
            end=end,
            center=center,
            energy=energy,
            confidence=energy / maximum_energy,
        )
        for start, end, center, energy in raw
    ]


def filter_projection_islands(
    islands: list[ProjectionIsland],
    sensitivity: str,
) -> list[ProjectionIsland]:
    minimum = MINIMUM_CONFIDENCE[sensitivity]
    return [island for island in islands if island.confidence >= minimum]


def split_multi_peak_islands(
    signal: np.ndarray,
    islands: list[ProjectionIsland],
    minimum_width: int = 5,
) -> list[ProjectionIsland]:
    segments: list[tuple[int, int, float, float]] = []
    for island in islands:
        local_signal = signal[island.start:island.end]
        if local_signal.size < minimum_width * 2:
            segments.append(
                (island.start, island.end, island.center, island.energy)
            )
            continue

        local_maximum = float(np.max(local_signal))
        prominence = max(
            local_maximum * 0.08,
            float(np.std(local_signal)) * 0.5,
        )
        peak_distance = max(
            minimum_width,
            int(round(island.width * 0.20)),
        )
        peaks, _ = scipy_signal.find_peaks(
            local_signal,
            prominence=prominence,
            distance=peak_distance,
            plateau_size=True,
        )
        if len(peaks) < 2:
            segments.append(
                (island.start, island.end, island.center, island.energy)
            )
            continue

        boundaries = []
        for left_peak, right_peak in zip(peaks, peaks[1:]):
            valley_slice = local_signal[left_peak:right_peak + 1]
            valley = int(np.argmin(valley_slice)) + int(left_peak)
            weaker_peak = min(
                float(local_signal[left_peak]),
                float(local_signal[right_peak]),
            )
            if (
                weaker_peak > 0
                and float(local_signal[valley])
                <= weaker_peak * MAXIMUM_SPLIT_VALLEY_RATIO
            ):
                boundaries.append(island.start + valley)

        if not boundaries:
            segments.append(
                (island.start, island.end, island.center, island.energy)
            )
            continue

        child_bounds = [
            island.start,
            *boundaries,
            island.end,
        ]
        children = []
        for start, end in zip(child_bounds, child_bounds[1:]):
            if end - start < minimum_width:
                children = []
                break
            indices = np.arange(start, end)
            weights = signal[start:end]
            energy = float(np.sum(weights))
            if energy <= 0:
                children = []
                break
            center = float(np.sum(indices * weights) / energy)
            children.append((start, end, center, energy))
        if children:
            segments.extend(children)
        else:
            segments.append(
                (island.start, island.end, island.center, island.energy)
            )

    maximum_energy = max((item[3] for item in segments), default=0.0)
    return [
        ProjectionIsland(
            start=start,
            end=end,
            center=center,
            energy=energy,
            confidence=energy / maximum_energy,
        )
        for start, end, center, energy in segments
    ]


def refine_projection_box(
    feature_map: np.ndarray,
    island: ProjectionIsland,
    previous_island: ProjectionIsland | None,
    next_island: ProjectionIsland | None,
    vertical_limits: tuple[int, int] | None = None,
    support_map: np.ndarray | None = None,
) -> DetectedBox:
    image_height, image_width = feature_map.shape[:2]
    left_limit = (
        0
        if previous_island is None
        else int(round((previous_island.center + island.center) / 2))
    )
    right_limit = (
        image_width
        if next_island is None
        else int(round((island.center + next_island.center) / 2))
    )
    horizontal_padding = max(1, int(round(island.width * 0.08)))
    left = max(left_limit, island.start - horizontal_padding)
    right = min(right_limit, island.end + horizontal_padding)

    if vertical_limits is None:
        limit_top, limit_bottom = 0, image_height
    else:
        limit_top = max(0, int(vertical_limits[0]))
        limit_bottom = min(image_height, int(vertical_limits[1]))
    if limit_bottom <= limit_top:
        limit_top, limit_bottom = 0, image_height

    vertical_support = feature_map if support_map is None else support_map
    row_signal = np.sum(
        vertical_support[limit_top:limit_bottom, left:right],
        axis=1,
    )
    peak_index = int(np.argmax(row_signal))
    baseline = float(np.min(row_signal))
    peak = float(row_signal[peak_index])
    threshold = baseline + (peak - baseline) * 0.30
    above = row_signal > threshold
    labeled, _ = ndimage.label(above)
    selected_label = labeled[peak_index]
    if selected_label:
        rows = np.where(labeled == selected_label)[0] + limit_top
    else:
        rows = np.asarray([peak_index + limit_top])
    vertical_padding = 4
    top = max(0, int(rows[0]) - vertical_padding)
    bottom = min(image_height, int(rows[-1]) + 1 + vertical_padding)

    return DetectedBox(
        x=left,
        y=top,
        width=max(1, right - left),
        height=max(1, bottom - top),
        confidence=round(island.confidence, 6),
    )
