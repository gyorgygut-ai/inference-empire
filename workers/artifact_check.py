import httpx


def artifact_exists(url: str, timeout: int = 30) -> bool:
    try:
        response = httpx.get(url, timeout=timeout)
        return response.status_code == 200 and len(response.content) > 0
    except httpx.HTTPError:
        return False
