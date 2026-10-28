"""Conservative Linux process identification; never signal a process group."""
import hashlib
import os
from pathlib import Path
import signal
import time

PROTECTED = {"hyprland", "caelestia", "qs", "quickshell", "steam", "steamwebhelper",
             "steamservice", "pressure-vessel", "wineserver", "services.exe", "explorer.exe",
             "rpcss.exe", "winedevice.exe", "plugplay.exe", "svchost.exe", "flatpak", "bwrap"}


def snapshot(pid, proc=Path("/proc")):
    base = proc / str(int(pid))
    stat = (base / "stat").read_text()
    # comm may contain spaces and closing parentheses; fields after the final ')' are fixed.
    fields = stat[stat.rfind(")") + 2:].split()
    uid = base.stat().st_uid
    exe = os.readlink(base / "exe")
    argv = [s.decode("utf-8", "replace") for s in (base / "cmdline").read_bytes().split(b"\0") if s]
    environ = {}
    for item in (base / "environ").read_bytes().split(b"\0"):
        key, _, value = item.partition(b"=")
        if key in (b"SteamAppId", b"STEAM_COMPAT_APP_ID", b"FLATPAK_ID"):
            environ[key.decode()] = value.decode("utf-8", "replace")
    identity = [int(pid), uid, fields[19], exe, argv]
    token = hashlib.sha256(repr(identity).encode()).hexdigest()
    return {"pid": int(pid), "uid": uid, "start_ticks": fields[19], "exe": exe,
            "argv": argv, "environment": environ, "token": token,
            "cpu_ticks": int(fields[11]) + int(fields[12]),
            "sampled_at": time.monotonic(),
            "rss_bytes": max(0, int(fields[21])) * os.sysconf("SC_PAGE_SIZE")}


def identify(process, games):
    if process["uid"] != os.getuid() or process["pid"] <= 1 or not process["argv"]:
        return None
    exe = Path(process["exe"])
    names = {exe.name.lower(), Path(process["argv"][0]).name.lower()}
    if names & PROTECTED:
        return None
    environment = process["environment"]
    if exe.name == "sober" and environment.get("FLATPAK_ID") == "org.vinegarhq.Sober":
        if any(g["id"] == "sober" for g in games):
            return {"game_id": "sober", "confidence": "matched Sober executable and Flatpak ID"}
    appid = environment.get("SteamAppId") or environment.get("STEAM_COMPAT_APP_ID")
    for game in games:
        if game["kind"] != "steam" or game["appid"] != appid:
            continue
        install = Path(game["install_path"]).resolve()
        if exe.resolve().is_relative_to(install):
            return {"game_id": game["id"], "confidence": "Steam app ID and executable inside installation"}
        # Wine helpers alone are insufficient. Require a Unix absolute game .exe argument.
        if exe.name in {"wine64-preloader", "wine-preloader", "wine64", "wine"}:
            for argument in process["argv"][1:]:
                path = Path(argument)
                if path.is_absolute() and path.suffix.lower() == ".exe" and path.resolve().is_relative_to(install):
                    return {"game_id": game["id"], "confidence": "Steam app ID and Proton game executable argument"}
    return None


def running(games, proc=Path("/proc")):
    matches = []
    unreadable = 0
    for directory in proc.iterdir():
        if not directory.name.isdecimal():
            continue
        try:
            process = snapshot(int(directory.name), proc)
            match = identify(process, games)
            if match:
                match["game_name"] = next((g["name"] for g in games if g["id"] == match["game_id"]), match["game_id"])
                matches.append({**match, **{key: process[key] for key in
                    ("pid", "exe", "start_ticks", "token", "rss_bytes", "cpu_ticks", "sampled_at")}})
        except (OSError, ValueError, IndexError):
            unreadable += 1
    if matches:
        time.sleep(0.2)
    for match in matches:
        match["cpu_percent"] = None
        try:
            current = snapshot(match["pid"], proc)
            interval = current["sampled_at"] - match["sampled_at"]
            if current["token"] == match["token"] and interval > 0:
                match["cpu_percent"] = round(max(0, current["cpu_ticks"] - match["cpu_ticks"])
                                              / os.sysconf("SC_CLK_TCK") / interval * 100, 1)
                match["rss_bytes"] = current["rss_bytes"]
        except (OSError, ValueError, IndexError):
            pass
    return {"processes": matches, "unreadable_processes": unreadable,
            "limitations": "Conservative matches only. Missing app IDs, inaccessible /proc, Windows paths, "
            "or wrappers may hide games. RSS is per process and may share memory. CPU is a short sample, "
            "100% equals one logical core; refresh for a new sample. Optional GPU readings are reported separately. "
            "Background games are not classified as unwanted."}


def terminate(pid, expected_token, games, force=False):
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        raise ValueError("Safe termination requires Linux pidfd support; no signal was sent")
    # A pidfd pins the process so PID reuse cannot redirect the signal.
    fd = os.pidfd_open(pid)
    try:
        process = snapshot(pid)
        if process["token"] != expected_token or not identify(process, games):
            raise ValueError("Process changed or is no longer safely identified; refresh before confirming")
        signal.pidfd_send_signal(fd, signal.SIGKILL if force else signal.SIGTERM)
    finally:
        os.close(fd)
