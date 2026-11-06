
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StockMovementCreate(BaseModel):
    movement_type: Literal["IN", "OUT", "ADJUSTMENT"]
    quantity: int = Field(ge=0)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_movement_quantity(self):
        if self.movement_type in ("IN", "OUT") and self.quantity == 0:
            raise ValueError("IN and OUT movements require a quantity greater than zero.")

        return self


class StockMovementResponse(BaseModel):
    id: int
    item_id: int
    movement_type: str
    quantity: int
    previous_quantity: int
    new_quantity: int
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
