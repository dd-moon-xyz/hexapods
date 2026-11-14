import argparse
import os
import shlex
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DIRECTORIES = {"server": "server", "local": "client/local", "raspi": "client/raspi"}


def read_config(path: Path) -> dict[str, str]:
    lines = path.read_text().splitlines() if path.exists() else ()
    entries = (line.split("=", 1) for line in lines if line.strip() and not line.lstrip().startswith("#"))
    return {key.strip(): " ".join(shlex.split(value, comments=True)) for key, value in entries}



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run",))
    parser.add_argument("role", choices=DIRECTORIES)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    directory = ROOT / DIRECTORIES[args.role]
    environment = {**read_config(directory / ".env"), **os.environ}
    command = args.command
    if not command:
        parser.error("Missing command")

    if args.role == "server" and command[0] == "./target/release/server":
        command = [*command, "--bind", environment.get("SERVER_BIND", "0.0.0.0:9877")]

    os.chdir(directory)
    os.execvpe(command[0], command, environment)


if __name__ == "__main__":
    main()
