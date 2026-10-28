"""Steam-reported per-user local cache; never infer playtime from app manifests."""
from pathlib import Path
import re
from .library import ManifestError, read_vdf, steam_roots


def lookup(mapping, key, default=None):
    if not isinstance(mapping, dict):
        return default
    return next((value for name, value in mapping.items() if name.casefold() == key.casefold()), default)


def cached_history(games, home=None, account=None):
    home = Path(home or Path.home())
    result = {"continue_playing": [], "most_played": [], "accounts": [], "account": None,
              "source": "Steam-reported · local cache", "warnings": [],
              "status": "Steam play history is unavailable. No locally tracked time is collected."}
    if account is not None and (not isinstance(account, str) or not re.fullmatch(r"[0-9]+", account)):
        raise ValueError("steam_user_id must be a numeric userdata directory name encoded as a string")
    caches = {}
    visited = set()
    for root in steam_roots(home):
        root = root.resolve()
        if root in visited:
            continue
        visited.add(root)
        try:
            for path in sorted((root / "userdata").glob("*/config/localconfig.vdf")):
                user = path.parent.parent.name
                if user.isdecimal():
                    caches.setdefault(user, []).append(path)
        except OSError as error:
            result["warnings"].append(f"Cannot inspect Steam userdata: {error}")
    result["accounts"] = sorted(caches)
    if account is None:
        if len(caches) == 1:
            account = next(iter(caches))
        elif len(caches) > 1:
            result["status"] = "Multiple Steam accounts found. Set steam_user_id in aeorys-gaming/config.json; histories are never merged across accounts."
            return result
    if account not in caches:
        return result
    result["account"] = account
    installed = {g["appid"]: g for g in games if g["kind"] == "steam"}
    records = {}
    for path in caches[account]:
        try:
            tree = read_vdf(path)
            apps = tree
            for key in ("UserLocalConfigStore", "Software", "Valve", "Steam", "apps"):
                apps = lookup(apps, key, {})
            if not isinstance(apps, dict):
                raise ManifestError("Steam apps cache must be an object")
            updated = path.stat().st_mtime
            for appid, values in apps.items():
                if appid not in installed or not isinstance(values, dict):
                    continue
                raw_minutes = lookup(values, "Playtime")
                raw_last = lookup(values, "LastPlayed")
                minutes = int(raw_minutes) if isinstance(raw_minutes, str) and raw_minutes.isdecimal() else None
                last = int(raw_last) if isinstance(raw_last, str) and raw_last.isdecimal() else None
                # Reject corrupt/unrepresentable timestamps and implausibly huge minute counters.
                if minutes is not None and not 0 <= minutes <= 100_000_000:
                    minutes = None
                if last is not None and not 0 < last <= 253402300799:
                    last = None
                record = {**installed[appid], "playtime_minutes": minutes, "last_played": last,
                          "cache_updated": updated}
                if appid not in records or updated > records[appid]["cache_updated"]:
                    records[appid] = record
        except (OSError, ValueError, TypeError) as error:
            result["warnings"].append(f"Cannot read Steam play history {path}: {error}")
    by_name = lambda game: (game["name"].casefold(), game["id"])
    result["continue_playing"] = sorted((g for g in records.values() if g["last_played"]),
        key=lambda g: (-g["last_played"], *by_name(g)))[:3]
    result["most_played"] = sorted((g for g in records.values() if g["playtime_minutes"]),
        key=lambda g: (-g["playtime_minutes"], *by_name(g)))[:5]
    if result["continue_playing"] or result["most_played"]:
        result["status"] = "Steam-reported local cache for account " + account + ". May be stale or incomplete; installed games only. No locally tracked time is collected."
    return result
