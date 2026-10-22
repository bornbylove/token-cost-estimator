from collections.abc import Iterable
from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from tokencost.core.schemas import ModelPrice


class PricingDataError(Exception):
    """The pricing file is missing, unreadable, or invalid."""


class _PricingFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    models: list[ModelPrice] = Field(min_length=1)

    @field_validator("models")
    @classmethod
    def _unique_ids(cls, models: list[ModelPrice]) -> list[ModelPrice]:
        seen: set[str] = set()
        for model in models:
            if model.id in seen:
                raise ValueError(f"duplicate model id: {model.id}")
            seen.add(model.id)
        return models


class PricingRepository:
    """Read-only access to model pricing."""

    def __init__(self, models: Iterable[ModelPrice]) -> None:
        self._models = {model.id: model for model in models}

    @classmethod
    def from_yaml(cls, path: Path) -> Self:
        try:
            raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise PricingDataError(f"cannot read pricing file {path}: {exc}") from exc

        try:
            data = _PricingFile.model_validate(raw)
        except ValidationError as exc:
            raise PricingDataError(f"invalid pricing file {path}:\n{exc}") from exc

        return cls(data.models)

    def all(self) -> list[ModelPrice]:
        return list(self._models.values())

    def get(self, model_id: str) -> ModelPrice | None:
        return self._models.get(model_id)

    def __len__(self) -> int:
        return len(self._models)
