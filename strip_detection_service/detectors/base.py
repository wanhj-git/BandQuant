from dataclasses import dataclass
from typing import Protocol

import numpy as np

from strip_detection_service.contracts import DetectionOptions


@dataclass(frozen=True)
class DetectedBox:
    x: int
    y: int
    width: int
    height: int
    confidence: float


class StripDetector(Protocol):
    algorithm_version: str

    def detect(
        self,
        image: np.ndarray,
        options: DetectionOptions,
    ) -> list[DetectedBox]:
        ...

