import json
import logging
from uuid import uuid4

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, Header, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from strip_detection_service.contracts import DetectionOptions
from strip_detection_service.detectors.legacy import LegacyHeuristicDetector
from strip_detection_service.pipeline import StripDetectionPipeline


logger = logging.getLogger("strip_detection_service")
detector = LegacyHeuristicDetector()
pipeline = StripDetectionPipeline(detector)
app = FastAPI(title="BandQuant Strip Detection", version="1.0.0")


def _error_response(
    request_id: str,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "requestId": request_id,
            "error": {"code": code, "message": message},
        },
    )


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "algorithmVersion": detector.algorithm_version}


@app.post("/v1/detect-strips")
async def detect_strips(
    image: UploadFile = File(...),
    options: str = Form(...),
    x_request_id: str | None = Header(default=None),
):
    request_id = x_request_id or str(uuid4())
    try:
        parsed_options = DetectionOptions.model_validate(json.loads(options))
    except (json.JSONDecodeError, ValidationError, TypeError) as error:
        return _error_response(
            request_id,
            400,
            "INVALID_OPTIONS",
            str(error),
        )

    contents = await image.read()
    if not contents:
        return _error_response(
            request_id,
            400,
            "INVALID_IMAGE",
            "The uploaded image is empty.",
        )
    decoded = cv2.imdecode(np.frombuffer(contents, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if decoded is None:
        return _error_response(
            request_id,
            400,
            "INVALID_IMAGE",
            "The uploaded file could not be decoded as an image.",
        )

    try:
        result = pipeline.detect(decoded, parsed_options, request_id)
    except ValueError as error:
        return _error_response(request_id, 400, "INVALID_ROI", str(error))

    logger.info(
        "strip_detection_completed",
        extra={
            "request_id": request_id,
            "image_width": result["image"]["width"],
            "image_height": result["image"]["height"],
            "expected_count": result["expectedCount"],
            "detected_count": result["detectedCount"],
            "algorithm_version": result["algorithmVersion"],
            "processing_ms": result["processingMs"],
        },
    )
    return result
