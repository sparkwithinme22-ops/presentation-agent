from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Optional

from pydantic import ValidationError

from .models import PresentationSpec
from .ollama_client import OllamaClient, OllamaError


SYSTEM_PROMPT = """You are a university presentation planner.
Return only JSON matching the supplied schema. Write concise, natural slide copy.
Do not fabricate statistics, sources, quotations, or current facts. When no research
has been provided, explain stable concepts without unsupported numbers.

The presentation uses a formal Knowledge Foundation university design system.
Choose slide types based on communication needs, not decoration. The first slide
must be type 'title' and the final slide must be type 'closing'. Use 'agenda' only
when it improves navigation. Use 'section' sparingly. Use 'quote' only when the
user supplied a real quotation; otherwise do not use it.

For content slides, provide 2-5 concise bullets. Each bullet should express one
specific idea and normally stay below 18 words. Avoid marketing language, vague
claims, em dashes, semicolons, arrow characters, and repetitive three-part slogans.
Slide titles should directly name the subject. Do not include formatting instructions."""


def requested_slide_count(request: str) -> Optional[int]:
    match = re.search(r"\b(\d{1,2})\s*[- ]?slides?\b", request, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


class SlidePlanner:
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    def create_plan(self, request: str, *, slide_count: Optional[int] = None) -> PresentationSpec:
        count = slide_count if slide_count is not None else requested_slide_count(request)
        count_instruction = (
            f"Create exactly {count} slides in total, including title and closing slides."
            if count
            else "Choose a concise slide count between 5 and 10, including title and closing slides."
        )
        user_prompt = f"""User request:
{request.strip()}

{count_instruction}
Create a coherent presentation for the audience stated or implied by the request.
The closing slide title should be appropriate for the request language."""

        schema = deepcopy(PresentationSpec.model_json_schema())
        if count is not None:
            slides_schema = schema["properties"]["slides"]
            slides_schema["minItems"] = count
            slides_schema["maxItems"] = count

        for attempt in range(2):
            current_prompt = user_prompt
            if attempt == 1 and count is not None:
                current_prompt += (
                    f"\n\nYour previous response had the wrong number of slides. "
                    f"Return exactly {count} slide objects. Count them before responding."
                )

            raw = self.client.chat_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=current_prompt,
                schema=schema,
            )
            try:
                plan_data = json.loads(raw)
                slides = plan_data.get("slides") if isinstance(plan_data, dict) else None
                if isinstance(slides, list) and len(slides) >= 2:
                    if isinstance(slides[0], dict):
                        slides[0]["type"] = "title"
                    if isinstance(slides[-1], dict):
                        slides[-1]["type"] = "closing"
                plan = PresentationSpec.model_validate(plan_data)
            except (json.JSONDecodeError, ValidationError) as exc:
                if attempt == 0:
                    continue
                raise OllamaError(
                    f"The model returned invalid presentation data after retrying: {exc}"
                ) from exc

            if count is None or len(plan.slides) == count:
                return plan

        raise OllamaError(
            f"The model returned {len(plan.slides)} slides after retrying, "
            f"but {count} were requested. Try generating again."
        )
