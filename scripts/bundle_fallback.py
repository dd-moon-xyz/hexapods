import asyncio
import json
import os
import tempfile
from pathlib import Path
from zipfile import ZipFile

from client_core.preview import capture


async def main() -> None:
    destination = Path(__file__).resolve().parent.parent / "client/core/src/client_core/assets/fallback.zip"
    url = os.environ.get("SERVER_URL", f"ws://{os.environ.get('SERVER_ADDRESS', '127.0.0.1')}:9877/ws")
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        manifest = await capture(url, directory)
        archive = directory / "fallback.zip"
        with ZipFile(archive, "w") as bundle:
            bundle.writestr("manifest.json", json.dumps(manifest))
            for name in manifest["frames"]:
                bundle.write(directory / name, name)

        destination.write_bytes(archive.read_bytes())


if __name__ == "__main__":
    asyncio.run(main())
