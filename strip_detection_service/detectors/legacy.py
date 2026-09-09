import cv2
import numpy as np
from scipy import ndimage

from strip_detection_service.contracts import DetectionOptions
from strip_detection_service.detectors.base import DetectedBox
from strip_detection_service.detectors.box_normalization import (
    normalize_detection_box_sizes,
)
from strip_detection_service.detectors.candidate_selection import (
    DetectionCandidate,
    score_detection_candidate,
    select_detection_candidate,
)
from strip_detection_service.detectors.projection import (
    extract_projection_islands,
    filter_projection_islands,
    refine_projection_box,
    remove_column_baseline,
    split_multi_peak_islands,
)


class LegacyHeuristicDetector:
    algorithm_version = "legacy-projection-2.4.0"
    minimum_analysis_height = 170
    maximum_analysis_scale = 2.5

    @staticmethod
    def _to_grayscale(image: np.ndarray) -> np.ndarray:
        if image.ndim == 3:
            # OpenCV decodes color images as BGR. These weights preserve the
            # legacy detector's RGB-to-grayscale result for the same source.
            return np.dot(image[..., :3], [0.114, 0.587, 0.299]).astype(np.uint8)
        return image.astype(np.uint8, copy=True)

    @staticmethod
    def _remove_background(image: np.ndarray) -> np.ndarray:
        structure_width = max(20, min(image.shape[1] // 10, 100))
        structure = np.ones((5, structure_width), dtype=np.uint8)
        background = ndimage.grey_opening(image, structure=structure)
        background = ndimage.grey_closing(background, structure=structure)
        corrected = np.maximum(
            image.astype(np.float32) - background.astype(np.float32),
            0,
        )
        if corrected.max() > 0:
            corrected = corrected / corrected.max() * 255
        return corrected.astype(np.uint8)

    @staticmethod
    def _blackhat(image: np.ndarray) -> np.ndarray:
        structure = np.ones((21, 81), dtype=np.uint8)
        closed = ndimage.grey_closing(image, structure=structure)
        feature_map = closed.astype(np.float32) - image.astype(np.float32)
        maximum = float(feature_map.max())
        if maximum > 0:
            feature_map = feature_map / maximum * 255
        return np.clip(feature_map, 0, 255).astype(np.uint8)

    def detect(
        self,
        image: np.ndarray,
        options: DetectionOptions,
    ) -> list[DetectedBox]:
        gray = self._to_grayscale(image)
        if options.polarity == "dark-on-light":
            selected = self._detect_polarity_candidate(
                gray,
                options,
                invert=False,
                polarity="dark-on-light",
            )
        elif options.polarity == "light-on-dark":
            selected = self._detect_polarity_candidate(
                gray,
                options,
                invert=True,
                polarity="light-on-dark",
            )
        else:
            dark_candidate = self._detect_polarity_candidate(
                gray,
                options,
                invert=False,
                polarity="dark-on-light",
            )
            light_candidate = self._detect_polarity_candidate(
                gray,
                options,
                invert=True,
                polarity="light-on-dark",
            )
            selected = select_detection_candidate(
                dark_candidate,
                light_candidate,
                options.expected_count,
            )
        return normalize_detection_box_sizes(
            selected.boxes,
            gray.shape,
        )

    def _detect_polarity_candidate(
        self,
        gray: np.ndarray,
        options: DetectionOptions,
        invert: bool,
        polarity: str,
    ) -> DetectionCandidate:
        original_boxes = self._detect_single_polarity(
            gray,
            options,
            invert,
        )
        original_candidate = DetectionCandidate(
            polarity=polarity,
            boxes=tuple(original_boxes),
            score=score_detection_candidate(
                original_boxes,
                gray.shape,
            ),
        )
        if gray.shape[0] >= self.minimum_analysis_height:
            return original_candidate

        scale = min(
            self.maximum_analysis_scale,
            self.minimum_analysis_height / max(1, gray.shape[0]),
        )
        scaled_width = max(1, int(round(gray.shape[1] * scale)))
        scaled_height = max(1, int(round(gray.shape[0] * scale)))
        scaled_gray = cv2.resize(
            gray,
            (scaled_width, scaled_height),
            interpolation=cv2.INTER_CUBIC,
        )
        scaled_boxes = self._detect_single_polarity(
            scaled_gray,
            options,
            invert,
        )
        mapped_boxes = self._map_boxes_to_original(
            scaled_boxes,
            original_shape=gray.shape,
            scaled_shape=scaled_gray.shape,
        )
        scaled_candidate = DetectionCandidate(
            polarity=polarity,
            boxes=tuple(mapped_boxes),
            score=score_detection_candidate(
                mapped_boxes,
                gray.shape,
            ),
        )
        return select_detection_candidate(
            original_candidate,
            scaled_candidate,
            options.expected_count,
        )

    @staticmethod
    def _map_boxes_to_original(
        boxes: list[DetectedBox],
        original_shape: tuple[int, ...],
        scaled_shape: tuple[int, ...],
    ) -> list[DetectedBox]:
        original_height, original_width = original_shape[:2]
        scaled_height, scaled_width = scaled_shape[:2]
        scale_x = scaled_width / max(1, original_width)
        scale_y = scaled_height / max(1, original_height)
        mapped = []
        for box in boxes:
            left = max(0, int(round(box.x / scale_x)))
            top = max(0, int(round(box.y / scale_y)))
            right = min(
                original_width,
                int(round((box.x + box.width) / scale_x)),
            )
            bottom = min(
                original_height,
                int(round((box.y + box.height) / scale_y)),
            )
            mapped.append(
                DetectedBox(
                    x=left,
                    y=top,
                    width=max(1, right - left),
                    height=max(1, bottom - top),
                    confidence=box.confidence,
                )
            )
        return mapped

    def _detect_single_polarity(
        self,
        gray: np.ndarray,
        options: DetectionOptions,
        invert: bool,
    ) -> list[DetectedBox]:
        if invert:
            gray = 255 - gray
        if options.background_correction == "auto":
            gray = self._remove_background(gray)

        feature_map = self._blackhat(gray)
        refinement_map = remove_column_baseline(feature_map)
        row_sums = np.sum(feature_map, axis=1)
        if not row_sums.size or float(row_sums.max()) <= 0:
            return []

        y_peak = int(np.argmax(row_sums))
        y_indices = np.where(row_sums > float(row_sums.max()) * 0.3)[0]
        y_indices = y_indices[
            np.abs(y_indices - y_peak) < max(1, gray.shape[0] * 0.15)
        ]
        if y_indices.size:
            lane_top = int(y_indices[0])
            lane_bottom = int(y_indices[-1]) + 1
        else:
            lane_top = max(0, y_peak - 15)
            lane_bottom = min(gray.shape[0], y_peak + 16)

        lane_roi = feature_map[lane_top:lane_bottom, :]
        if lane_roi.size == 0:
            return []
        column_sums = np.sum(lane_roi, axis=0)
        smoothed = ndimage.gaussian_filter1d(column_sums, sigma=2.0)
        raw_islands = extract_projection_islands(smoothed)
        split_islands = split_multi_peak_islands(
            smoothed,
            raw_islands,
        )
        islands = filter_projection_islands(
            split_islands,
            options.sensitivity,
        )
        selected = sorted(islands, key=lambda island: island.center)
        if not selected:
            return []

        lane_height = max(1, lane_bottom - lane_top)
        vertical_margin = max(4, int(round(lane_height * 0.25)))
        vertical_limits = (
            max(0, lane_top - vertical_margin),
            min(feature_map.shape[0], lane_bottom + vertical_margin),
        )
        boxes = []
        for index, island in enumerate(selected):
            previous_island = selected[index - 1] if index > 0 else None
            next_island = (
                selected[index + 1]
                if index + 1 < len(selected)
                else None
            )
            boxes.append(
                refine_projection_box(
                    refinement_map,
                    island,
                    previous_island,
                    next_island,
                    vertical_limits=vertical_limits,
                    support_map=feature_map,
                )
            )
        return boxes
