"""JSON CLI. All launch commands use argv; no game metadata is executed by a shell."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import subprocess
import tempfile
import time

from .library import discover, launch
from .processes import running, terminate
from .history import cached_history
from .resources import resource_context


def data_directory():
    directory = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "aeorys-gaming"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directory


def note_path(game_id):
    if not re.fullmatch(r"steam:[1-9][0-9]*|sober", game_id):
        raise ValueError("Invalid game ID")
    return data_directory() / (game_id.replace(":", "-") + ".txt")


def atomic_write(path, content):
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", action="append", default=[], help="Additional Steam library root (repeatable)")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("library")
    commands.add_parser("running")
    for action in ("launch", "notes-get", "notes-set"):
        command = commands.add_parser(action)
        command.add_argument("game_id")
    stop = commands.add_parser("terminate")
    stop.add_argument("pid", type=int)
    stop.add_argument("--confirm", required=True, help="Full process identity token from running output")
    stop.add_argument("--force", action="store_true", help="Separate force request, only after SIGTERM and a delay")
    args = parser.parse_args()
    try:
        if args.action.startswith("notes-"):
            path = note_path(args.game_id)
            if args.action == "notes-get":
                result = {"text": path.read_text() if path.exists() else ""}
            else:
                text = sys.stdin.read(65537)
                if len(text.encode()) > 65536:
                    raise ValueError("Notes are limited to 64 KiB")
                atomic_write(path, text)
                result = {"saved": True}
        else:
            config_path = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "aeorys-gaming/config.json"
            config = json.loads(config_path.read_text()) if config_path.exists() else {}
            if not isinstance(config, dict):
                raise ValueError("config.json must contain an object")
            paths = config.get("libraries", [])
            if not isinstance(paths, list) or not all(isinstance(p, str) and Path(p).expanduser().is_absolute() for p in paths):
                raise ValueError("config.json libraries must be an array of absolute library paths")
            library = discover(extra_libraries=paths + args.library)
            if args.action == "library":
                library["history"] = cached_history(library["games"], account=config.get("steam_user_id"))
                result = library
            elif args.action == "running":
                result = running(library["games"])
                result["resources"] = resource_context(result["processes"])
            elif args.action == "launch":
                game = next((g for g in library["games"] if g["id"] == args.game_id), None)
                if not game:
                    raise ValueError("Game is no longer installed; refresh the library")
                result = launch(game)
            else:
                if not re.fullmatch(r"[a-f0-9]{64}", args.confirm):
                    raise ValueError("Invalid process confirmation token")
                receipt = data_directory() / f"termination-{args.confirm}.json"
                if args.force:
                    if not receipt.exists():
                        raise ValueError("Request graceful termination first")
                    attempt = json.loads(receipt.read_text())
                    elapsed = time.monotonic() - attempt["time"]
                    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
                    if attempt["boot"] != boot or not 5 <= elapsed <= 300 or attempt["pid"] != args.pid:
                        raise ValueError("Graceful attempt must be 5–300 seconds old in this boot; refresh and retry")
                terminate(args.pid, args.confirm, library["games"], args.force)
                if not args.force:
                    atomic_write(receipt, json.dumps({"pid": args.pid, "time": time.monotonic(),
                        "boot": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}))
                result = {"sent": "SIGKILL" if args.force else "SIGTERM", "pid": args.pid,
                          "message": "Signal sent to this process only; refresh to check whether it exited."}
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
