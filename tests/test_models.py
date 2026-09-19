import pytest
from pydantic import ValidationError

from agent.models import PresentationSpec


def test_valid_plan() -> None:
    plan = PresentationSpec.model_validate(
        {
            "title": "Quantum Computing",
            "audience": "First-year university students",
            "slides": [
                {"type": "title", "title": "Quantum Computing", "subtitle": "An introduction"},
                {"type": "content", "title": "Qubits", "bullets": ["A qubit stores quantum information"]},
                {"type": "closing", "title": "Thank you"},
            ],
        }
    )
    assert len(plan.slides) == 3


def test_plan_requires_closing_slide() -> None:
    with pytest.raises(ValidationError):
        PresentationSpec.model_validate(
            {
                "title": "Quantum Computing",
                "audience": "Students",
                "slides": [
                    {"type": "title", "title": "Quantum Computing"},
                    {"type": "content", "title": "Qubits", "bullets": ["One point"]},
                ],
            }
        )

