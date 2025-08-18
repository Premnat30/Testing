import os
import re
import shutil
import subprocess
from typing import Dict, List

from flask import Flask, jsonify, render_template, request
import psutil


app = Flask(__name__)


PROCESS_NAME_PATTERN = re.compile(r"^[\w\-.]+$")


def validate_process_name(process_name: str) -> None:
    if not process_name or not PROCESS_NAME_PATTERN.match(process_name):
        raise ValueError(
            "Invalid process name. Use only letters, numbers, underscore, dash, or dot."
        )


def start_process_by_name(process_name: str) -> int:
    executable_path = shutil.which(process_name)
    if executable_path is None:
        raise FileNotFoundError(
            f"Executable for '{process_name}' not found in PATH."
        )

    process = subprocess.Popen(
        [executable_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    return process.pid


def list_processes_matching(process_name: str) -> List[psutil.Process]:
    matches: List[psutil.Process] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = proc.info.get("name") or ""
            cmdline = proc.info.get("cmdline") or []
            name_match = name == process_name
            cmdline_match = any(process_name in part for part in cmdline)
            if name_match or cmdline_match:
                if proc.pid != os.getpid():
                    matches.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return matches


def stop_processes_by_name(process_name: str, timeout_seconds: float = 5.0) -> Dict[str, int]:
    targets = list_processes_matching(process_name)
    terminated = 0
    killed = 0

    for p in targets:
        try:
            p.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    gone, alive = psutil.wait_procs(targets, timeout=timeout_seconds)
    terminated += len(gone)

    for p in alive:
        try:
            p.kill()
            killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {"terminated": terminated, "killed": killed}


@app.route("/")
def index():
    return render_template("process_index.html")


@app.post("/api/start")
def api_start():
    data = request.get_json(silent=True) or {}
    process_name = (data.get("processName") or "").strip()
    try:
        validate_process_name(process_name)
        pid = start_process_by_name(process_name)
        return jsonify({"ok": True, "pid": pid, "message": f"Started '{process_name}'"})
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except FileNotFoundError as fe:
        return jsonify({"ok": False, "error": str(fe)}), 404
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"Failed to start: {exc}"}), 500


@app.post("/api/stop")
def api_stop():
    data = request.get_json(silent=True) or {}
    process_name = (data.get("processName") or "").strip()
    try:
        validate_process_name(process_name)
        result = stop_processes_by_name(process_name)
        return jsonify({"ok": True, **result, "message": f"Stopped processes matching '{process_name}'"})
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"Failed to stop: {exc}"}), 500


def create_app() -> Flask:
    return app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)

