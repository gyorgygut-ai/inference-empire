from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
from pathlib import Path
from typing import TypedDict
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def find_workspace_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "nx.json").is_file() and (candidate / "package.json").is_file():
            return candidate
    raise RuntimeError(f"could not find Nx workspace root from {start}")


def workspace_root() -> Path:
    configured_root = os.getenv("NX_WORKSPACE_ROOT")
    if configured_root:
        candidate = Path(configured_root).resolve()
        if (candidate / "nx.json").is_file() and (candidate / "package.json").is_file():
            return candidate
        raise RuntimeError("NX_WORKSPACE_ROOT does not identify an Nx workspace")
    return find_workspace_root(Path(__file__).resolve().parent)


ROOT = workspace_root()
BEAM_SERVICE = "workers-voice-llm-chat-completions"


class ReplyMessage(TypedDict):
    content: str


class ReplyChoice(TypedDict):
    message: ReplyMessage


class CompletionResponse(TypedDict):
    choices: list[ReplyChoice]


def deployed_url() -> str:
    result = subprocess.run(
        ["npx", "tsx", "tools/get-beam-url.ts", BEAM_SERVICE],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout.strip().rstrip("/")


def request_completion(request: Request) -> CompletionResponse:
    try:
        with urlopen(request, timeout=180) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError(
            f"deployed Chat Completions request failed with HTTP {error.code}"
        ) from error


def main() -> None:
    token = os.environ["GENERATED_LLM_CHAT_COMPLETIONS_API_KEY"]
    url = f"{deployed_url()}/v1/chat/completions"
    payload = json.dumps(
        {
            "model": "Qwen/Qwen2.5-3B-Instruct",
            "messages": [{"role": "user", "content": "Reply with a short greeting."}],
            "temperature": 0,
            "max_tokens": 32,
        }
    ).encode()
    request = Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    responses: queue.Queue[tuple[CompletionResponse | None, Exception | None]] = queue.Queue()

    def send_request() -> None:
        try:
            responses.put((request_completion(request), None))
        except Exception as error:
            responses.put((None, error))

    threading.Thread(target=send_request, daemon=True).start()
    while True:
        try:
            body, error = responses.get(timeout=15)
            break
        except queue.Empty:
            print(
                "🐣 LLM acceptance request is still running; Beam logs are streaming.", flush=True
            )

    if error is not None:
        raise error
    if body is None:
        raise RuntimeError("deployed Chat Completions request returned no response")

    reply = body["choices"][0]["message"]["content"]
    if not isinstance(reply, str) or not reply.strip():
        raise AssertionError("deployed Chat Completions response has no reply text")

    rejected_request = Request(
        url,
        data=payload,
        headers={
            "Authorization": "Bearer invalid-voice-api-key",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(rejected_request, timeout=30):
            raise AssertionError("Chat Completions accepted an invalid API key")
    except HTTPError as error:
        if error.code != 401:
            raise AssertionError(
                f"Chat Completions rejected an invalid API key with HTTP {error.code}, not 401"
            ) from error

    print(json.dumps({"service": BEAM_SERVICE, "reply": reply}))


if __name__ == "__main__":
    main()
