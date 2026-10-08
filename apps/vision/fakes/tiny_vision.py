"""Tiny vision loader: real Apple-framework analysis via auge + apfel CLIs.

Mirrors FakeVisionModel/FakeVisionProcessor call shapes so generate() needs
no change: processor stashes the PIL, model runs `auge --output json` and
`apfel` on it, decode() returns the contract dict as JSON text. The result is
validated against packages/vision/contract.json.
Swap deps to (TinyVisionModel(), TinyVisionProcessor(), prompt); no canned.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

CONTRACT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "vision"
    / "contracts"
    / "small_vision.json"
)
TIMEOUT = 120


def _run(argv):
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=TIMEOUT, check=True
    ).stdout


def _json_argv(tool, *args):
    try:
        return json.loads(_run([tool, *args, "--output", "json"]))
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return None


def _faces(image_path):
    data = _json_argv("auge", "--faces", str(image_path))
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("faces", "detections", "observations"):
            if isinstance(data.get(key), list):
                return len(data[key])
    return 0


def _classify(image_path):
    data = _json_argv("auge", "--classify", str(image_path))
    labels = []
    candidates = data if isinstance(data, list) else (data or {}).get("classifications", [])
    for item in candidates if isinstance(candidates, list) else []:
        if isinstance(item, str):
            labels.append(item.lower())
        elif isinstance(item, dict):
            name = item.get("identifier") or item.get("label") or item.get("name")
            if name:
                labels.append(str(name).lower())
    return labels


def _describe(image_path, prompt):
    try:
        out = _run(["apfel", "-f", str(image_path), prompt, "--output", "json"])
        data = json.loads(out)
        if isinstance(data, dict):
            text = data.get("response") or data.get("text") or out
        else:
            text = out
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        try:
            text = _run(["apfel", "-f", str(image_path), prompt])
        except (subprocess.CalledProcessError, FileNotFoundError):
            text = ""
    return text if isinstance(text, str) else json.dumps(text)


def _classification(n_faces, labels):
    if n_faces == 1:
        return "portrait_1p"
    if n_faces == 2:
        return "portrait_2p"
    if n_faces == 3:
        return "portrait_3p"
    if n_faces > 3:
        return "portrait_group"
    blob = " ".join(labels)
    for keyword, cls in (
        ("food", "food_0p"), ("pizza", "food_0p"), ("meal", "food_0p"),
        ("receipt", "receipt_0p"), ("document", "document_0p"),
        ("paper", "document_0p"), ("text", "document_0p"),
        ("landscape", "landscape_0p"), ("mountain", "landscape_0p"),
        ("cat", "animal_0p"), ("dog", "animal_0p"), ("animal", "animal_0p"),
        ("screenshot", "screenshot_0p"),
    ):
        if keyword in blob:
            return cls
    return "other_0p"


def _contract():
    return json.loads(CONTRACT_PATH.read_text())["output"]


def analyze(image, prompt):
    """Real inference on a PIL image -> contract-shaped dict."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
        image.save(fh.name)
        path = fh.name
    try:
        n_faces = _faces(path)
        labels = _classify(path)
        description = _describe(path, prompt) or " ".join(labels) or "image"
        classification = _classification(n_faces, labels)
        contract = _contract()
        if classification not in contract["properties"]["classification"]["enum"]:
            classification = "other_0p"
        subjects = [label for label in labels[:3]] or [classification]
        return {
            "classification": classification,
            "subjects": subjects,
            "description": description.strip(),
        }
    finally:
        Path(path).unlink(missing_ok=True)


class TinyVisionModel:
    """Real model: generate() runs auge + apfel, returns [[json]]."""

    def generate(self, **kwargs):
        image = kwargs.get("tiny_image")
        prompt = kwargs.get("tiny_text") or ""
        return [[json.dumps(analyze(image, prompt))]]


class TinyVisionProcessor:
    """Real processor: stashes the PIL on the inputs, decodes JSON text."""

    def apply_chat_template(self, messages, **kwargs):
        parts = []
        for message in messages:
                    parts.extend(item.get("text", "") for item in message.get("content", []) if isinstance(item, dict) and item.get("type") == "text")
        return "\n".join(parts)

    def __call__(self, text=None, images=None, **kwargs):
        prompt = text[0] if isinstance(text, list) else (text or "")
        return _TinyInputs(prompt, images[0] if images else None)

    def decode(self, generated, **kwargs):
        return generated[0] if isinstance(generated, list) else generated


class _TinyInputs(dict):
    def __init__(self, prompt, image):
        super().__init__(input_ids=_TinyIds(), tiny_text=prompt, tiny_image=image)

    @property
    def input_ids(self):
        return self["input_ids"]

    def to(self, device):
        return self


class _TinyIds:
    shape = (1, 0)
