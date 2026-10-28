"""Read Steam KeyValues files without evaluating their contents."""
from pathlib import Path
import os
import re
import shutil
import subprocess


class ManifestError(ValueError):
    pass


def parse_vdf(text):
    opening, closing = object(), object()
    tokens = []
    pattern = re.compile(r'\s+|//[^\n]*|"((?:\\.|[^"\\])*)"|([{}])|([^\s{}"]+)')
    offset = 0
    while offset < len(text):
        match = pattern.match(text, offset)
        if not match:
            raise ManifestError(f"Invalid KeyValues syntax at offset {offset}")
        offset = match.end()
        if match.group(1) is not None:
            tokens.append(re.sub(r'\\(["\\])', r'\1', match.group(1)))
        elif match.group(2):
            tokens.append(opening if match.group(2) == "{" else closing)
        elif match.group(3):
            tokens.append(match.group(3))
    index = 0

    def object_value(nested=False, depth=0):
        nonlocal index
        if depth > 32:
            raise ManifestError("KeyValues nesting too deep")
        result = {}
        while index < len(tokens):
            key = tokens[index]
            index += 1
            if key is closing:
                if not nested:
                    raise ManifestError("Unexpected closing brace")
                return result
            if key is opening or index >= len(tokens):
                raise ManifestError("Expected key/value pair")
            value = tokens[index]
            index += 1
            if value is opening:
                value = object_value(True, depth + 1)
            elif value is closing:
                raise ManifestError("Missing value")
            result[key] = value
        if nested:
            raise ManifestError("Unclosed object")
        return result

    return object_value()


def read_vdf(path):
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ManifestError("Manifest exceeds 4 MiB limit")
    return parse_vdf(path.read_text(encoding="utf-8-sig"))


def steam_roots(home):
    return [home / ".local/share/Steam", home / ".steam/steam",
            home / ".steam/root",
            home / ".var/app/com.valvesoftware.Steam/.local/share/Steam"]


def discover(home=None, extra_libraries=(), check_sober=True):
    home = Path(home or Path.home())
    roots = list(dict.fromkeys(p.resolve() for p in steam_roots(home)))
    libraries = set()
    warnings = []
    for root in roots:
        if not root.exists():
            continue
        libraries.add(root)
        path = root / "steamapps/libraryfolders.vdf"
        if not path.exists():
            continue
        try:
            folders = read_vdf(path).get("libraryfolders", {})
            if not isinstance(folders, dict):
                raise ManifestError("libraryfolders must be an object")
            for key, value in folders.items():
                if not key.isdecimal():
                    continue
                location = value.get("path") if isinstance(value, dict) else value
                if isinstance(location, str) and Path(location).is_absolute():
                    libraries.add(Path(location).resolve())
        except (OSError, ValueError) as error:
            warnings.append(f"Cannot read {path}: {error}")
    libraries.update(Path(p).expanduser().resolve() for p in extra_libraries)
    games = []
    for library in sorted(libraries):
        folder = library / "steamapps"
        try:
            manifests = sorted(folder.glob("appmanifest_*.acf"))
            if not folder.is_dir():
                warnings.append(f"Steam library unavailable: {library}")
                continue
            for manifest in manifests:
                try:
                    state = read_vdf(manifest).get("AppState")
                    if not isinstance(state, dict):
                        raise ManifestError("Missing AppState object")
                    appid = state.get("appid", "")
                    name, directory = state.get("name"), state.get("installdir")
                    if not isinstance(appid, str) or not re.fullmatch(r"[1-9][0-9]*", appid):
                        raise ManifestError("Invalid app ID")
                    if manifest.name != f"appmanifest_{appid}.acf":
                        raise ManifestError("Manifest filename/app ID mismatch")
                    if not isinstance(name, str) or not name or not isinstance(directory, str) or not directory:
                        raise ManifestError("Missing name or installation directory")
                    common = (folder / "common").resolve()
                    install = (common / directory).resolve()
                    if install == common or not install.is_relative_to(common):
                        raise ManifestError("Installation path escapes Steam common directory")
                    if not install.is_dir():
                        warnings.append(f"{name}: installation directory missing; omitted")
                        continue
                    flags = int(state.get("StateFlags", "0"))
                    if not flags & 4:
                        warnings.append(f"{name}: installation is incomplete; omitted")
                        continue
                    artwork = None
                    for root in roots:
                        for candidate in [root / f"appcache/librarycache/{appid}_library_600x900.jpg",
                                          root / f"appcache/librarycache/{appid}_header.jpg"]:
                            if candidate.is_file():
                                artwork = candidate.as_uri()
                                break
                        if artwork:
                            break
                    games.append({"id": f"steam:{appid}", "appid": appid, "name": name,
                                  "kind": "steam", "install_path": str(install),
                                  "library_path": str(library), "artwork": artwork,
                                  "protondb_url": f"https://www.protondb.com/app/{appid}",
                                  "store_url": f"https://store.steampowered.com/app/{appid}/"})
                except (OSError, ValueError, TypeError) as error:
                    warnings.append(f"Cannot read {manifest}: {error}")
        except OSError as error:
            warnings.append(f"Cannot scan {folder}: {error}")
    if check_sober and shutil.which("flatpak"):
        try:
            result = subprocess.run(["flatpak", "info", "org.vinegarhq.Sober"],
                                    capture_output=True, timeout=5, check=False)
            if result.returncode == 0:
                games.append({"id": "sober", "name": "Sober (Roblox)", "kind": "sober",
                              "install_path": "Flatpak: org.vinegarhq.Sober", "artwork": None})
        except (OSError, subprocess.TimeoutExpired) as error:
            warnings.append(f"Cannot query Sober: {error}")
    return {"games": sorted(games, key=lambda g: (g["name"].casefold(), g["install_path"])),
            "warnings": warnings, "libraries": [str(p) for p in sorted(libraries)]}


def launch(game):
    if game["kind"] == "sober":
        argv = ["flatpak", "run", "org.vinegarhq.Sober"]
    else:
        appid = game["appid"]
        if not re.fullmatch(r"[1-9][0-9]*", appid):
            raise ValueError("Invalid Steam app ID")
        if shutil.which("steam"):
            argv = ["steam", f"steam://rungameid/{appid}"]
        elif shutil.which("flatpak"):
            probe = subprocess.run(["flatpak", "info", "com.valvesoftware.Steam"],
                                   capture_output=True, timeout=5, check=False)
            if probe.returncode:
                raise ValueError("Neither native Steam nor Flatpak Steam is available")
            argv = ["flatpak", "run", "com.valvesoftware.Steam", f"steam://rungameid/{appid}"]
        else:
            raise ValueError("Steam is not installed or is not on PATH")
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    return {"requested": True, "pid": process.pid,
            "message": "Launch request sent; this does not confirm the game started."}
