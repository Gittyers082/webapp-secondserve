"""Base schema: JSON uses camelCase to match src/data/types.ts; Python uses snake_case."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Schema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


T = TypeVar("T")


class Page(Schema, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
