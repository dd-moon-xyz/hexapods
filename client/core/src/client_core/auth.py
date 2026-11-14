import os


def headers(token: str | None = None) -> dict[str, str]:
    token = os.getenv("HEXAPODS_TOKEN", "") if token is None else token
    return {"Authorization": f"Bearer {token}"} if token else {}
