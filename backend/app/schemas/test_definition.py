"""
Pydantic schemas for the TestDefinition entity.

Backend-internal schemas for this milestone only — not the frozen
cross-module TestDefinition contract (see app/models/test_definition.py
docstring and the milestone report's cross-module requirements section).

Step validation here intentionally mirrors the execution engine's minimal
step model (navigate/click/fill) so that a TestDefinition's `content`
stored via this API is guaranteed to be shaped the way the execution
engine expects — without duplicating execution *logic* (no browser
actions happen here, only shape/field validation).
"""

from datetime import datetime
from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class NavigateStep(BaseModel):
    type: Literal["navigate"]
    url: str = Field(min_length=1)


class ClickStep(BaseModel):
    type: Literal["click"]
    selector: str = Field(min_length=1)


class FillStep(BaseModel):
    type: Literal["fill"]
    selector: str = Field(min_length=1)
    value: str = ""


Step = Union[NavigateStep, ClickStep, FillStep]

_StepListAdapter: TypeAdapter[list[Step]] = TypeAdapter(list[Step])


class TestDefinitionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    content: list[Step] = Field(min_length=1)


class TestDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    description: str | None
    content: list[dict]
    created_at: datetime
