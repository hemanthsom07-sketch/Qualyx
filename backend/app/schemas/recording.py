"""
Recorder event ingestion schemas.

Field names on RecordedEventCreate are deliberately camelCase — not the
usual Python snake_case style used elsewhere in this codebase — because
this mirrors Recorder's actual RecordedEvent wire contract exactly:

    {
      id: string;
      type: "page_load" | "click" | "input_change";
      timestamp: number;
      pageUrl: string;
      targetTag?: string;
      elementId?: string;
      elementText?: string;
      value?: string;
      redacted?: boolean;
    }

This is the same shape as Intelligence's RealRecordedEvent dataclass
(intelligence/journey_understanding/recorder_adapter.py, confirmed by
inspection). No renaming or translation happens at this boundary on
purpose — see app/services/intelligence_client.py, which constructs a
RealRecordedEvent directly from this schema's field names.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RecordedEventCreate(BaseModel):
    id: str = Field(min_length=1)
    type: Literal["page_load", "click", "input_change"]
    timestamp: float
    pageUrl: str = Field(min_length=1)
    targetTag: str | None = None
    elementId: str | None = None
    elementText: str | None = None
    value: str | None = None
    redacted: bool | None = None


class RecordingCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    journey_id: str = Field(alias="journeyId", min_length=1)
    events: list[RecordedEventCreate] = Field(min_length=1)
