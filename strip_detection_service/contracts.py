from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Point(BaseModel):
    x: float
    y: float


class RoiOptions(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    coordinate_space: Literal["original-pixels"] = Field(alias="coordinateSpace")
    polygon: list[Point] = Field(min_length=4, max_length=4)


class DetectionOptions(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    expected_count: int = Field(alias="expectedCount", ge=1, le=100)
    roi: RoiOptions
    polarity: Literal["auto", "dark-on-light", "light-on-dark"] = "auto"
    background_correction: Literal["auto", "off"] = Field(
        default="off",
        alias="backgroundCorrection",
    )
    sensitivity: Literal["low", "normal", "high"] = "normal"

