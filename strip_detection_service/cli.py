import base64
import json
import sys

import cv2
import numpy as np

from strip_detection_service.contracts import DetectionOptions
from strip_detection_service.detectors.legacy import LegacyHeuristicDetector
from strip_detection_service.pipeline import StripDetectionPipeline


def main() -> int:
    try:
        request = json.load(sys.stdin)
        image_bytes = base64.b64decode(request["imageBase64"], validate=True)
        image = cv2.imdecode(
            np.frombuffer(image_bytes, dtype=np.uint8),
            cv2.IMREAD_UNCHANGED,
        )
        if image is None:
            raise ValueError("The image payload could not be decoded.")
        options = DetectionOptions.model_validate(request["options"])
        result = StripDetectionPipeline(LegacyHeuristicDetector()).detect(
            image,
            options,
            request["requestId"],
        )
        json.dump(result, sys.stdout, separators=(",", ":"))
        return 0
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
