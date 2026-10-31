from __future__ import annotations

import hmac

from fastapi import HTTPException, Request


def require_bearer_token(request: Request, expected_token: str | None) -> None:
    if not expected_token:
        raise HTTPException(status_code=503, detail="API authentication is not configured")

    scheme, _, supplied_token = request.headers.get("authorization", "").partition(" ")
    if scheme.casefold() != "bearer" or not hmac.compare_digest(
        supplied_token.encode(), expected_token.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid API credential")
