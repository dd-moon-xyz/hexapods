from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["Movement", "Organism", "Start"]


class MovementVector(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    x: float = Field(ge=-1, le=1, allow_inf_nan=False)
    y: float = Field(ge=-1, le=1, allow_inf_nan=False)


class Movement(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["movement"]
    direction: Literal["inward", "outward", "vector"]
    speed_multiplier: float = Field(gt=0, le=10, allow_inf_nan=False)
    vector: MovementVector | None = None
    escape: bool | None = None

    @model_validator(mode="after")
    def validate_vector(self):
        if self.direction == "vector":
            if self.vector is None or self.escape is None:
                raise ValueError("Vector movement requires a vector and an escape flag")
            if self.vector.x == 0 and self.vector.y == 0:
                raise ValueError("Movement vector must be nonzero")
        else:
            if "vector" in self.model_fields_set or "escape" in self.model_fields_set:
                raise ValueError("Radial movement cannot include vector or escape fields")
        return self


class Organism(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    scale: int = Field(default=1, ge=1, le=10)
    x: int = Field(default=128, ge=0)
    y: int = Field(default=128, ge=0)


class Start(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    simulation: Literal["hexapod"] = "hexapod"
    action: Literal["start"]
    population_updates: bool = False
    birth_rate_min: float = Field(default=1.0, gt=0, allow_inf_nan=False)
    birth_rate_max: float = Field(default=5.0, gt=0, allow_inf_nan=False)
    interaction_count_min: int = Field(default=1, ge=1, le=2147483647)
    interaction_count_max: int = Field(default=10, ge=1, le=2147483647)
    size: int = Field(default=512, ge=256, le=1024)
    output_size: int | None = Field(default=None, ge=1, le=1024)
    fps: int = Field(default=20, ge=1, le=60)
    pixel_size: int = Field(default=1, ge=1, le=16)
    dt: float = Field(default=0.1, gt=0, le=0.2, allow_inf_nan=False)
    space_speed_multiplier: float = Field(default=2.0, ge=1, allow_inf_nan=False)
    boundary: Literal["circle"] = "circle"
    organisms: list[Organism] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_world(self):
        if self.interaction_count_min > self.interaction_count_max:
            raise ValueError("Minimum interaction count must not exceed maximum interaction count")

        if self.birth_rate_min > self.birth_rate_max:
            raise ValueError("Minimum birth rate must not exceed maximum birth rate")

        if any(item.x >= self.size or item.y >= self.size for item in self.organisms):
            raise ValueError("Hexapod positions must be inside the world")

        return self
