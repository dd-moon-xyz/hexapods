import argparse
import getpass
import hashlib
import os
import re
import secrets
import shlex
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent.parent
DIRECTORIES = {"server": "server", "local": "client/local", "raspi": "client/raspi"}


def read_config(path: Path) -> dict[str, str]:
    lines = path.read_text().splitlines() if path.exists() else ()
    entries = (line.split("=", 1) for line in lines if line.strip() and not line.lstrip().startswith("#"))
    return {key.strip(): " ".join(shlex.split(value, comments=True)) for key, value in entries}


def save_config(path: Path, values: dict[str, str]) -> None:
    lines = path.read_text().splitlines() if path.exists() else ()
    existing = {line.split("=", 1)[0].strip() for line in lines if "=" in line}
    updated = (
        f"{line.split('=', 1)[0].strip()}={shlex.quote(values[line.split('=', 1)[0].strip()])}"
        if line.split("=", 1)[0].strip() in values else line
        for line in lines
    )

    content = "\n".join((*updated, *(f"{key}={shlex.quote(value)}" for key, value in values.items() if key not in existing)))
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(content + "\n")

    print(f"Saved {path.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("add", "revoke", "configure", "run"))
    parser.add_argument("role", choices=DIRECTORIES)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    directory = ROOT / DIRECTORIES[args.role]
    path = directory / ".env"
    config = read_config(path)
    if args.action == "run":
        environment = {**config, **os.environ}
        command = args.command
        if not command:
            parser.error("Missing command")

        if args.role == "server" and command[0] == "./target/release/server":
            command = [*command, "--bind", environment.get("SERVER_BIND", "0.0.0.0:9877")]

        os.chdir(directory)
        os.execvpe(command[0], command, environment)

    if args.action in ("add", "revoke"):
        name = input("Client name (desktop, raspi, etc.): ").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            parser.error("Client name must contain only letters, digits, underscores or hyphens")

        entries = tuple(entry for entry in config.get("HEXAPODS_TOKEN_HASHES", "").split(",") if entry and entry.split(":", 1)[0] != name)
        if args.action == "add":
            token = secrets.token_hex(32)
            entries = (*entries, f"{name}:{hashlib.sha256(token.encode()).hexdigest()}")
            print(f"Client token (copy to the client configuration prompt): {token}")

        save_config(path, {"HEXAPODS_TOKEN_HASHES": ",".join(entries)})
        print("Restart the server to apply the change.")
        return

    if args.role == "server":
        bind = input(f"Listen address [{config.get('SERVER_BIND', '127.0.0.1:9877')}]: ").strip() or config.get("SERVER_BIND", "127.0.0.1:9877")
        origin = input("Browser HTTPS origin (empty disables browser login): ").strip()
        if origin and (urlsplit(origin).scheme != "https" or not urlsplit(origin).netloc or urlsplit(origin).path):
            parser.error("Use an HTTPS origin without a path, such as https://hexapods.example.com")

        save_config(path, {"SERVER_BIND": bind, "HEXAPODS_BROWSER_ORIGIN": origin})
        return

    url = input("Server WebSocket URL (wss://domain/ws for internet): ").strip()
    if urlsplit(url).scheme not in ("ws", "wss") or not urlsplit(url).netloc:
        parser.error("Enter a full ws:// or wss:// URL")

    token = getpass.getpass("Client token: ").strip()
    if not token:
        parser.error("Client token cannot be empty")

    save_config(path, {"SERVER_URL": url, "HEXAPODS_TOKEN": token})


if __name__ == "__main__":
    main()
