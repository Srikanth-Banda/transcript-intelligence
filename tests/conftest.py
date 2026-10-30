import json
from types import SimpleNamespace

import pytest

from ti.load import load_meetings


@pytest.fixture(scope="session")
def meetings():
    return load_meetings()


class MockOpenAI:
    """Stands in for the OpenAI client. Answers Stage 0 from the user message; counts calls."""

    def __init__(self):
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls += 1
        user = kwargs["messages"][-1]["content"]
        label = "support" if "support" in user.lower().split("opening:")[-1] else "external"
        names = [ln.split(":", 1)[0] for ln in user.split("opening:\n")[-1].splitlines() if ":" in ln]
        body = {
            "label": label,
            "evidence_quote": "mock quote",
            "confidence": "high",
            "speaker_sides": [{"speaker": n, "side": "aegis_staff"} for n in dict.fromkeys(names)],
        }
        msg = SimpleNamespace(content=json.dumps(body))
        usage = SimpleNamespace(model_dump=lambda: {"prompt_tokens": 1, "completion_tokens": 1})
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], model="mock/model", usage=usage, model_extra={})


@pytest.fixture
def mock_openai():
    return MockOpenAI()
