import json

from agent.slide_planner import SlidePlanner


def plan_json(slide_count: int) -> str:
    slides = [{"type": "title", "title": "Test"}]
    slides.extend(
        {"type": "content", "title": f"Slide {number}", "bullets": ["Point"]}
        for number in range(2, slide_count)
    )
    slides.append({"type": "closing", "title": "Thank you"})
    return json.dumps({"title": "Test", "audience": "Students", "slides": slides})


class FakeClient:
    def __init__(self) -> None:
        self.calls = 0
        self.schemas = []

    def chat_json(self, **kwargs) -> str:
        self.calls += 1
        self.schemas.append(kwargs["schema"])
        return plan_json(6 if self.calls == 1 else 5)


def test_planner_retries_when_model_ignores_slide_count() -> None:
    client = FakeClient()
    plan = SlidePlanner(client).create_plan("Explain a topic", slide_count=5)

    assert len(plan.slides) == 5
    assert client.calls == 2
    assert client.schemas[0]["properties"]["slides"]["minItems"] == 5
    assert client.schemas[0]["properties"]["slides"]["maxItems"] == 5


class WrongEndpointsClient:
    def chat_json(self, **kwargs) -> str:
        data = json.loads(plan_json(5))
        data["slides"][0]["type"] = "content"
        data["slides"][0]["bullets"] = ["Incorrect model structure"]
        data["slides"][-1]["type"] = "content"
        data["slides"][-1]["bullets"] = ["Incorrect model structure"]
        return json.dumps(data)


def test_planner_repairs_required_first_and_last_slide_types() -> None:
    plan = SlidePlanner(WrongEndpointsClient()).create_plan("Explain a topic", slide_count=5)

    assert plan.slides[0].type.value == "title"
    assert plan.slides[-1].type.value == "closing"
