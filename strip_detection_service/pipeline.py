import time

import numpy as np

from strip_detection_service.contracts import DetectionOptions
from strip_detection_service.detectors.base import StripDetector
from strip_detection_service.geometry import map_roi_box_to_original, rectify_roi


class StripDetectionPipeline:
    def __init__(self, detector: StripDetector):
        self.detector = detector

    def detect(
        self,
        image: np.ndarray,
        options: DetectionOptions,
        request_id: str,
    ) -> dict:
        started_at = time.perf_counter()
        roi_polygon = [
            point.model_dump()
            for point in options.roi.polygon
        ]
        roi_image, transform = rectify_roi(image, roi_polygon)
        boxes = self.detector.detect(roi_image, options)

        detections = []
        for index, box in enumerate(boxes, start=1):
            roi_box = {
                "x": box.x,
                "y": box.y,
                "width": box.width,
                "height": box.height,
            }
            detections.append(
                {
                    "id": f"detection-{index}",
                    "source": "detected",
                    "confidence": box.confidence,
                    "roiBox": roi_box,
                    "originalPolygon": map_roi_box_to_original(roi_box, transform),
                }
            )

        detected_count = len(detections)
        warnings = []
        if detected_count == 0:
            warnings.append(
                {
                    "code": "NO_BANDS_FOUND",
                    "message": "No bands were detected in the selected ROI.",
                }
            )
        if detected_count != options.expected_count:
            warnings.append(
                {
                    "code": "COUNT_MISMATCH",
                    "message": (
                        f"Expected {options.expected_count} bands "
                        f"but detected {detected_count}."
                    ),
                }
            )

        image_height, image_width = image.shape[:2]
        return {
            "requestId": request_id,
            "algorithmVersion": self.detector.algorithm_version,
            "image": {"width": image_width, "height": image_height},
            "roi": {
                "coordinateSpace": "original-pixels",
                "polygon": roi_polygon,
                "width": transform.width,
                "height": transform.height,
            },
            "expectedCount": options.expected_count,
            "detectedCount": detected_count,
            "detections": detections,
            "warnings": warnings,
            "processingMs": round((time.perf_counter() - started_at) * 1000, 3),
        }
