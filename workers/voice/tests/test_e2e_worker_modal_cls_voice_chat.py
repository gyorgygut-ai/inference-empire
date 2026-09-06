import pytest
from pydantic import ValidationError

import workers.voice.worker_modal_cls_voice_chat as worker_mod


class StubPipeline:
    def __init__(self):
        self.voices = {}


@pytest.mark.local_e2e
def test_e2e_modal_session_update_returns_updated_session(e2e_target):
    deps = (StubPipeline(),)

    out = e2e_target.run_async(
        worker_mod,
        {
            "type": "session.update",
            "session": {"instructions": "Speak briefly.", "language": "hu"},
        },
        deps,
    )

    assert out["type"] == "session.updated" and out["session"]["instructions"] == "Speak briefly."


@pytest.mark.local_e2e
def test_e2e_modal_session_update_rejects_bad_type(e2e_target):
    deps = (StubPipeline(),)

    with pytest.raises(ValidationError):
        e2e_target.run(worker_mod, {"type": "bogus"}, deps)


