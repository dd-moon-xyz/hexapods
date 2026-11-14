import argparse
import asyncio
import json
import os
from pathlib import Path

from websockets.exceptions import WebSocketException

from .client import load_preset
from .replay import record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="ws://" + os.getenv("SERVER_ADDRESS", "192.168.0.15:9877") + "/ws")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--directory", type=Path, default=Path("recordings/default"))
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--output-size", type=int, default=800)
    args = parser.parse_args()
    try:
        if not 0 < args.seconds < float("inf") or not 1 <= args.output_size <= 1024:
            raise ValueError("--seconds must be positive and finite; --output-size must be between 1 and 1024")
        config = load_preset(args.url) if args.config is None else json.loads(args.config.read_text())
        config = {**config, "output_size": args.output_size}
        print(f"Collecting {args.seconds:g} seconds worth of frames from {args.url}…", flush=True)
        asyncio.run(record(args.url, config, args.directory, args.seconds))
        print(f"Recording ready in {args.directory}. Run make replay to display it.", flush=True)
    except (OSError, ValueError, WebSocketException) as error:
        parser.exit(1, f"Error: {error}\n")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
