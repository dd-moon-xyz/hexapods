import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ASSET = Path(__file__).resolve().parent.parent / "client/core/src/client_core/assets/fallback.zip"
REPOSITORY = "dd-moon-xyz/hexapods"
API = f"https://api.github.com/repos/{REPOSITORY}/releases"


def checksum(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def download() -> None:
    metadata = json.loads(ASSET.with_suffix(".json").read_text())
    if ASSET.exists() and checksum(ASSET) == metadata["sha256"]:
        print("Fallback animation is already downloaded.")
        return

    ASSET.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ASSET.parent) as temporary:
        staging = Path(temporary) / ASSET.name
        with urlopen(metadata["url"], timeout=60) as source, staging.open("wb") as output:
            shutil.copyfileobj(source, output)

        if checksum(staging) != metadata["sha256"]:
            raise ValueError("Fallback download failed SHA-256 verification")

        staging.replace(ASSET)

    print(f"Downloaded fallback animation to {ASSET}")


def publish() -> None:
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token and shutil.which("gh"):
        token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()

    if not token:
        raise ValueError("Publishing requires GH_TOKEN, GITHUB_TOKEN, or an authenticated GitHub CLI")

    digest = checksum(ASSET)
    tag = f"fallback-{digest[:12]}"

    def request(url: str, method: str = "GET", data=None, content_type="application/json"):
        body = json.dumps(data).encode() if isinstance(data, dict) else data
        headers = {
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "Content-Type": content_type, "X-GitHub-Api-Version": "2022-11-28",
        }

        with urlopen(Request(url, data=body, headers=headers, method=method), timeout=120) as response:
            return json.load(response)

    try:
        release = request(f"{API}/tags/{tag}")
    except HTTPError as error:
        if error.code != 404:
            raise

        release = request(API, "POST", {
            "tag_name": tag, "name": "Fallback animation — 120 FPS",
            "body": "Offline fallback animation: 1024×1024 JPEG frames at 120 FPS.",
            "draft": True, "make_latest": "false",
        })

    if not any(asset["name"] == ASSET.name for asset in release["assets"]):
        upload = release["upload_url"].split("{", 1)[0]
        request(f"{upload}?name={ASSET.name}", "POST", ASSET.read_bytes(), "application/zip")

    if release["draft"]:
        request(release["url"], "PATCH", {"draft": False, "make_latest": "false"})

    metadata = {
        "url": f"https://github.com/{REPOSITORY}/releases/download/{tag}/{ASSET.name}",
        "sha256": digest,
    }

    ASSET.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Published https://github.com/{REPOSITORY}/releases/tag/{tag}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("download", "publish"))
    arguments = parser.parse_args()
    try:
        {"download": download, "publish": publish}[arguments.action]()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error: {error}\n")
