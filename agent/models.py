from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class SlideType(str, Enum):
    TITLE = "title"
    AGENDA = "agenda"
    CONTENT = "content"
    SECTION = "section"
    QUOTE = "quote"
    CLOSING = "closing"


class SlideSpec(BaseModel):
    type: SlideType
    title: str = Field(min_length=1, max_length=90)
    subtitle: Optional[str] = Field(default=None, max_length=160)
    bullets: List[str] = Field(default_factory=list, max_length=6)
    quote: Optional[str] = Field(default=None, max_length=420)
    attribution: Optional[str] = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def validate_slide_content(self) -> "SlideSpec":
        if self.type in {SlideType.CONTENT, SlideType.AGENDA} and not self.bullets:
            raise ValueError(f"{self.type.value} slides require at least one bullet")
        if self.type == SlideType.QUOTE and not self.quote:
            raise ValueError("quote slides require quote text")
        if any(len(item) > 180 for item in self.bullets):
            raise ValueError("bullet text must not exceed 180 characters")
        return self


class PresentationSpec(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    subtitle: Optional[str] = Field(default=None, max_length=180)
    audience: str = Field(min_length=1, max_length=120)
    slides: List[SlideSpec] = Field(min_length=2, max_length=30)

    @model_validator(mode="after")
    def validate_structure(self) -> "PresentationSpec":
        if self.slides[0].type != SlideType.TITLE:
            raise ValueError("the first slide must use type 'title'")
        if self.slides[-1].type != SlideType.CLOSING:
            raise ValueError("the last slide must use type 'closing'")
        return self
