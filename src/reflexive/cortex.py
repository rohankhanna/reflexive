from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

SQLITE_MAIN_SUFFIXES = (".db", ".sqlite", ".sqlite3")
SQLITE_SIDECAR_SUFFIXES = (
    ".db-shm",
    ".db-wal",
    ".sqlite-shm",
    ".sqlite-wal",
    ".sqlite3-shm",
    ".sqlite3-wal",
)
SAMPLE_LIMIT = 10


def _resolve_path(raw_path: str) -> Path:
    return Path(raw_path).expanduser().resolve()


def _is_sqlite_sidecar(path: Path) -> bool:
    lowered = path.name.lower()
    return any(lowered.endswith(suffix) for suffix in SQLITE_SIDECAR_SUFFIXES)


def _is_sqlite_main(path: Path) -> bool:
    lowered = path.name.lower()
    return not _is_sqlite_sidecar(path) and any(lowered.endswith(suffix) for suffix in SQLITE_MAIN_SUFFIXES)


def _canonical_open_path(path: Path) -> str:
    return os.path.realpath(path.expanduser())


def _normalize_open_target(target: str) -> str:
    suffix = " (deleted)"
    if target.endswith(suffix):
        target = target[: -len(suffix)]
    return os.path.realpath(target)


def _read_proc_command(pid_dir: Path) -> str:
    cmdline_path = pid_dir / "cmdline"
    try:
        raw = cmdline_path.read_bytes()
    except OSError:
        raw = b""
    if raw:
        parts = [part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part]
        if parts:
            return " ".join(parts)
    comm_path = pid_dir / "comm"
    try:
        return comm_path.read_text(encoding="utf-8").strip()
    except OSError:
        return pid_dir.name


def _holders_via_proc(paths: list[Path]) -> dict[str, Any] | None:
    proc_root = Path("/proc")
    if not proc_root.exists():
        return None

    canonical_to_paths: dict[str, set[str]] = {}
    for path in paths:
        canonical_to_paths.setdefault(_canonical_open_path(path), set()).add(str(path))
    if not canonical_to_paths:
        return {
            "source": "proc",
            "available": True,
            "holder_count": 0,
            "holders": [],
            "quiesce_blocked": False,
        }

    holders: dict[int, dict[str, Any]] = {}
    for pid_dir in sorted(proc_root.iterdir(), key=lambda entry: entry.name):
        if not pid_dir.name.isdigit():
            continue
        fd_root = pid_dir / "fd"
        if not fd_root.is_dir():
            continue
        matched_paths: set[str] = set()
        try:
            fd_entries = list(fd_root.iterdir())
        except OSError:
            continue
        for fd_entry in fd_entries:
            try:
                target = os.readlink(fd_entry)
            except OSError:
                continue
            normalized = _normalize_open_target(target)
            if normalized in canonical_to_paths:
                matched_paths.update(canonical_to_paths[normalized])
        if not matched_paths:
            continue
        pid = int(pid_dir.name)
        holders[pid] = {
            "pid": pid,
            "command": _read_proc_command(pid_dir),
            "paths": sorted(matched_paths),
        }

    holder_list = [holders[pid] for pid in sorted(holders)]
    return {
        "source": "proc",
        "available": True,
        "holder_count": len(holder_list),
        "holders": holder_list[:SAMPLE_LIMIT],
        "quiesce_blocked": bool(holder_list),
    }


def _holders_via_lsof(paths: list[Path]) -> dict[str, Any] | None:
    lsof = shutil.which("lsof")
    if not lsof:
        return None

    canonical_to_paths: dict[str, set[str]] = {}
    for path in paths:
        canonical_to_paths.setdefault(_canonical_open_path(path), set()).add(str(path))
    if not canonical_to_paths:
        return {
            "source": "lsof",
            "available": True,
            "holder_count": 0,
            "holders": [],
            "quiesce_blocked": False,
        }

    try:
        completed = subprocess.run(
            [lsof, "-Fpcn", "--", *sorted(canonical_to_paths)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    holders: dict[int, dict[str, Any]] = {}
    current_pid: int | None = None
    current_command = ""
    matched_paths: set[str] = set()

    def flush_current() -> None:
        nonlocal current_pid, current_command, matched_paths
        if current_pid is None or not matched_paths:
            matched_paths = set()
            return
        holders[current_pid] = {
            "pid": current_pid,
            "command": current_command or str(current_pid),
            "paths": sorted(matched_paths),
        }
        matched_paths = set()

    for line in completed.stdout.splitlines():
        if not line:
            continue
        prefix, value = line[0], line[1:]
        if prefix == "p":
            flush_current()
            try:
                current_pid = int(value)
            except ValueError:
                current_pid = None
            current_command = ""
        elif prefix == "c":
            current_command = value
        elif prefix == "n":
            normalized = _normalize_open_target(value)
            if normalized in canonical_to_paths:
                matched_paths.update(canonical_to_paths[normalized])
    flush_current()

    holder_list = [holders[pid] for pid in sorted(holders)]
    return {
        "source": "lsof",
        "available": True,
        "holder_count": len(holder_list),
        "holders": holder_list[:SAMPLE_LIMIT],
        "quiesce_blocked": bool(holder_list),
    }


def _sqlite_holders_for_paths(paths: list[Path]) -> dict[str, Any]:
    proc_report = _holders_via_proc(paths)
    if proc_report is not None:
        return proc_report

    lsof_report = _holders_via_lsof(paths)
    if lsof_report is not None:
        return lsof_report

    return {
        "source": "unavailable",
        "available": False,
        "holder_count": 0,
        "holders": [],
        "quiesce_blocked": bool(paths),
    }


def inspect_path(raw_path: str) -> dict[str, Any]:
    root = _resolve_path(raw_path)

    if not root.exists():
        return {
            "path": str(root),
            "exists": False,
            "file_count": 0,
            "directory_count": 0,
            "symlink_count": 0,
            "unsafe_live_state_count": 0,
            "unsafe_live_state_samples": [],
            "sqlite_main_count": 0,
            "sqlite_main_samples": [],
            "sqlite_sidecar_count": 0,
            "sqlite_sidecar_samples": [],
            "sqlite_holder_detection": "proc",
            "sqlite_holder_count": 0,
            "sqlite_holder_samples": [],
            "sqlite_quiesce_blocked": False,
            "stale_sqlite_sidecar_count": 0,
            "stale_sqlite_sidecar_samples": [],
        }

    file_count = 0
    directory_count = 0
    symlink_count = 0
    sqlite_main_entries: list[str] = []
    sqlite_sidecar_entries: list[str] = []
    sqlite_paths: list[Path] = []

    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            symlink_count += 1
            continue
        if path.is_dir():
            directory_count += 1
            continue
        if not path.is_file():
            continue
        file_count += 1
        relative = str(path.relative_to(root))
        if _is_sqlite_main(path):
            sqlite_main_entries.append(relative)
            sqlite_paths.append(path)
        elif _is_sqlite_sidecar(path):
            sqlite_sidecar_entries.append(relative)
            sqlite_paths.append(path)

    holders = _sqlite_holders_for_paths(sqlite_paths)
    stale_sidecar_count = 0
    if sqlite_sidecar_entries and not holders["quiesce_blocked"] and holders["available"]:
        stale_sidecar_count = len(sqlite_sidecar_entries)

    unsafe_entries = sqlite_main_entries + sqlite_sidecar_entries
    return {
        "path": str(root),
        "exists": True,
        "file_count": file_count,
        "directory_count": directory_count,
        "symlink_count": symlink_count,
        "unsafe_live_state_count": len(unsafe_entries),
        "unsafe_live_state_samples": unsafe_entries[:SAMPLE_LIMIT],
        "sqlite_main_count": len(sqlite_main_entries),
        "sqlite_main_samples": sqlite_main_entries[:SAMPLE_LIMIT],
        "sqlite_sidecar_count": len(sqlite_sidecar_entries),
        "sqlite_sidecar_samples": sqlite_sidecar_entries[:SAMPLE_LIMIT],
        "sqlite_holder_detection": holders["source"],
        "sqlite_holder_count": holders["holder_count"],
        "sqlite_holder_samples": holders["holders"],
        "sqlite_quiesce_blocked": holders["quiesce_blocked"],
        "stale_sqlite_sidecar_count": stale_sidecar_count,
        "stale_sqlite_sidecar_samples": sqlite_sidecar_entries[:SAMPLE_LIMIT] if stale_sidecar_count else [],
    }


def check_path(raw_path: str) -> dict[str, Any]:
    inspection = inspect_path(raw_path)
    checks: list[dict[str, Any]] = []

    if not inspection["exists"]:
        checks.append(
            {"name": "path_exists", "status": "fail", "detail": f"missing path: {inspection['path']}"}
        )
    else:
        checks.append({"name": "path_exists", "status": "pass", "detail": inspection["path"]})

    sqlite_main_count = inspection["sqlite_main_count"]
    sqlite_sidecar_count = inspection["sqlite_sidecar_count"]
    sqlite_holder_count = inspection["sqlite_holder_count"]
    stale_sidecar_count = inspection["stale_sqlite_sidecar_count"]
    holder_detection = inspection["sqlite_holder_detection"]

    if sqlite_holder_count:
        checks.append(
            {
                "name": "live_sqlite_state",
                "status": "warn",
                "detail": (
                    f"{sqlite_main_count} SQLite database(s), {sqlite_sidecar_count} sidecar(s), "
                    f"and {sqlite_holder_count} live holder(s) detected; avoid copying or snapshotting this state "
                    "until the tool is fully stopped"
                ),
                "sample": inspection["sqlite_holder_samples"],
            }
        )
    elif stale_sidecar_count:
        checks.append(
            {
                "name": "live_sqlite_state",
                "status": "warn",
                "detail": (
                    f"{sqlite_main_count} SQLite database(s) and {sqlite_sidecar_count} sidecar(s) detected, "
                    f"but no live holders were found via {holder_detection}; sidecars appear stale"
                ),
                "sample": inspection["stale_sqlite_sidecar_samples"],
            }
        )
    elif sqlite_main_count:
        checks.append(
            {
                "name": "live_sqlite_state",
                "status": "pass",
                "detail": f"{sqlite_main_count} SQLite database(s) detected with no live holders",
            }
        )
    else:
        checks.append({"name": "live_sqlite_state", "status": "pass", "detail": "no SQLite files found"})

    if inspection["symlink_count"]:
        checks.append(
            {
                "name": "symlink_inventory",
                "status": "pass",
                "detail": f"{inspection['symlink_count']} symlink(s) detected",
            }
        )
    else:
        checks.append({"name": "symlink_inventory", "status": "pass", "detail": "no symlinks found"})

    recommendations: list[str] = []
    if sqlite_holder_count:
        recommendations.append("Stop the tool that owns this state before copying, snapshotting, or repairing it.")
    elif stale_sidecar_count:
        recommendations.append(
            "SQLite sidecars remain, but no live holders were found. Treat them as stale until the owning tool recreates them."
        )
    if inspection["unsafe_live_state_count"]:
        recommendations.append("Review SQLite-backed state carefully before attempting manual recovery or migration.")
    if not inspection["exists"]:
        recommendations.append("Point reflexive at an existing tool-state directory to inspect it.")

    status = "ok"
    if any(item["status"] == "warn" for item in checks):
        status = "warn"
    if any(item["status"] == "fail" for item in checks):
        status = "error"

    return {
        "path": inspection["path"],
        "status": status,
        "checks": checks,
        "inspection": inspection,
        "recommendations": recommendations,
    }
