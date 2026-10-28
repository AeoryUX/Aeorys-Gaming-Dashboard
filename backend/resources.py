"""Optional read-only NVIDIA and CPU temperature context. No hardware tuning."""
import csv
import io
import json
from pathlib import Path
import shutil
import subprocess


def number(value):
    try:
        result = float(value.strip())
        return result if 0 <= result < 1_000_000 else None
    except (ValueError, AttributeError):
        return None


def parse_gpu_csv(text):
    gpus = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) != 6 or not row[0].strip().isdecimal():
            continue
        gpus.append({"index": int(row[0]), "name": row[1].strip(),
                     "utilization_percent": number(row[2]), "vram_used_mib": number(row[3]),
                     "vram_total_mib": number(row[4]), "temperature_c": number(row[5]),
                     "scope": "GPU-wide, not selected-game usage"})
    return gpus


def parse_pmon(text):
    columns = None
    readings = []
    for line in text.splitlines():
        parts = line.split()
        if line.lstrip().startswith("#"):
            header = line.lstrip()[1:].split()
            if all(key in header for key in ("gpu", "pid", "sm")):
                columns = header
            continue
        if not columns or len(parts) < len(columns):
            continue
        row = dict(zip(columns, parts))
        if not row.get("pid", "").isdecimal() or not row.get("gpu", "").isdecimal():
            continue
        # An unsupported field stays null. Do not substitute total GPU memory.
        readings.append({"pid": int(row["pid"]), "gpu_index": int(row["gpu"]),
                         "gpu_percent": number(row.get("sm")),
                         "vram_mib": number(row.get("fb"))})
    return readings


def cpu_temperatures(hwmon=Path("/sys/class/hwmon")):
    temperatures = []
    for device in hwmon.glob("hwmon*"):
        try:
            name = (device / "name").read_text().strip()
            if name not in {"coretemp", "k10temp"}:
                continue
            for sensor in device.glob("temp*_input"):
                label_path = sensor.with_name(sensor.name.replace("_input", "_label"))
                label = label_path.read_text().strip()
                if not (label.startswith("Package id") or label in {"Tctl", "Tdie"}):
                    continue
                value = int(sensor.read_text().strip()) / 1000
                if -50 <= value <= 150:
                    temperatures.append({"label": f"CPU {label}", "celsius": value, "scope": "system context"})
        except (OSError, ValueError):
            continue
    return temperatures


def resource_context(processes):
    annotate_window_activity(processes)
    result = {"gpus": [], "cpu_temperatures": cpu_temperatures(), "warnings": [],
              "per_process_status": "Per-process GPU/VRAM unavailable. No NVIDIA tool detected."}
    if not shutil.which("nvidia-smi"):
        return result
    try:
        query = subprocess.run(["nvidia-smi", "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                                "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=4, check=False)
        if query.returncode == 0:
            result["gpus"] = parse_gpu_csv(query.stdout)
        else:
            result["warnings"].append("NVIDIA GPU-wide readings unavailable; nvidia-smi failed.")
        sample = subprocess.run(["nvidia-smi", "pmon", "-c", "1", "-s", "um"],
                                capture_output=True, text=True, timeout=4, check=False)
        result["per_process_status"] = "Per-process GPU/VRAM unavailable where driver fields are unsupported or no matching PID is reported. GPU-wide values are separate."
        if sample.returncode == 0:
            rows = parse_pmon(sample.stdout)
            # IDs are those already identified by /proc. Revalidate tokens after sampling.
            from .processes import snapshot
            for process in processes:
                try:
                    if snapshot(process["pid"])["token"] != process["token"]:
                        continue
                except (OSError, ValueError, IndexError):
                    continue
                process["gpu_samples"] = [row for row in rows if row["pid"] == process["pid"]]
    except (OSError, subprocess.TimeoutExpired):
        result["warnings"].append("NVIDIA resource query unavailable or timed out.")
    return result


def classify_window_activity(pid, active, clients):
    if not isinstance(active, dict) or not isinstance(clients, list):
        return "unknown"
    matches = [client for client in clients if isinstance(client, dict) and client.get("pid") == pid]
    if not matches:
        return "unknown"
    if active.get("pid") == pid:
        return "foreground"
    if isinstance(active.get("pid"), int) and active["pid"] > 0:
        return "background"
    return "unknown"


def annotate_window_activity(processes):
    for process in processes:
        process["window_activity"] = "unknown"
    if not processes or not shutil.which("hyprctl"):
        return
    try:
        active = subprocess.run(["hyprctl", "-j", "activewindow"], capture_output=True, text=True, timeout=2, check=False)
        clients = subprocess.run(["hyprctl", "-j", "clients"], capture_output=True, text=True, timeout=2, check=False)
        if active.returncode or clients.returncode:
            return
        active, clients = json.loads(active.stdout), json.loads(clients.stdout)
        for process in processes:
            process["window_activity"] = classify_window_activity(process["pid"], active, clients)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return
