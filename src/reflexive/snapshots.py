from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
from tempfile import TemporaryDirectory
from typing import Any

from reflexive.cortex import inspect_path
from reflexive.paths import resolve_app_paths

MAX_SAMPLE_COUNT = 20


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat_z(value: datetime | None = None) -> str:
    return (value or _now_utc()).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _timestamp_slug(value: datetime | None = None) -> str:
    return (value or _now_utc()).strftime("%Y%m%dT%H%M%SZ")


def _slugify(value: str) -> str:
    parts = []
    last_dash = False
    for char in value.lower():
        if char.isalnum():
            parts.append(char)
            last_dash = False
        elif not last_dash:
            parts.append("-")
            last_dash = True
    slug = "".join(parts).strip("-")
    return slug or "path"


def _resolve_path(raw_path: str) -> Path:
    return Path(raw_path).expanduser().resolve()


def _state_root() -> Path:
    return Path(resolve_app_paths()["state"])


def _snapshot_catalog_root() -> Path:
    return _state_root() / "snapshots"


def _path_key(path: Path) -> str:
    digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:12]
    return f"{_slugify(path.name)}-{digest}"


def _path_root(path: Path) -> Path:
    return _snapshot_catalog_root() / _path_key(path)


def _snapshots_root(path: Path) -> Path:
    return _path_root(path) / "entries"


def _latest_pointer_path(path: Path) -> Path:
    return _path_root(path) / "latest.json"


def _metadata_path(path: Path) -> Path:
    return _path_root(path) / "target.json"


def _snapshot_dir(path: Path, snapshot_id: str) -> Path:
    return _snapshots_root(path) / snapshot_id


def _snapshot_manifest_path(path: Path, snapshot_id: str) -> Path:
    return _snapshot_dir(path, snapshot_id) / "manifest.json"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _allocate_snapshot_id(path: Path) -> str:
    base_id = _timestamp_slug()
    candidate = base_id
    suffix = 1
    while _snapshot_dir(path, candidate).exists():
        suffix += 1
        candidate = f"{base_id}-{suffix}"
    return candidate


def _is_sqlite_sidecar(path: Path) -> bool:
    lowered = path.name.lower()
    return lowered.endswith(("-wal", "-shm")) and (
        lowered.endswith(".sqlite-wal")
        or lowered.endswith(".sqlite-shm")
        or lowered.endswith(".sqlite3-wal")
        or lowered.endswith(".sqlite3-shm")
        or lowered.endswith(".db-wal")
        or lowered.endswith(".db-shm")
    )


def _is_sqlite_main(path: Path) -> bool:
    lowered = path.name.lower()
    return not _is_sqlite_sidecar(path) and lowered.endswith((".sqlite", ".sqlite3", ".db"))


def _sqlite_sidecar_paths(database_path: Path) -> tuple[Path, Path]:
    return (
        database_path.with_name(database_path.name + "-wal"),
        database_path.with_name(database_path.name + "-shm"),
    )


def _copy_sqlite_database(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    has_sidecars = any(sidecar.exists() for sidecar in _sqlite_sidecar_paths(source))
    source_uri = source.resolve().as_uri() + ("?mode=ro" if has_sidecars else "?mode=ro&immutable=1")
    source_connection = sqlite3.connect(source_uri, uri=True)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.execute("PRAGMA busy_timeout = 1000")
        destination_connection.execute("PRAGMA busy_timeout = 1000")
        source_connection.backup(destination_connection)
        destination_connection.commit()
    finally:
        destination_connection.close()
        source_connection.close()


def _write_target_metadata(path: Path) -> None:
    _write_json(
        _metadata_path(path),
        {
            "path": str(path),
            "path_key": _path_key(path),
            "updated_at": _isoformat_z(),
        },
    )


def _set_latest_pointer(path: Path, snapshot_id: str) -> dict[str, Any]:
    payload = {
        "path": str(path),
        "path_key": _path_key(path),
        "snapshot_id": snapshot_id,
        "updated_at": _isoformat_z(),
    }
    _write_json(_latest_pointer_path(path), payload)
    return payload


def _snapshot_file_map(files_root: Path) -> dict[str, Path]:
    return {
        str(path.relative_to(files_root)): path
        for path in sorted(files_root.rglob("*"))
        if path.is_file()
    }


def _snapshot_symlink_map(manifest: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for entry in manifest.get("symlink_entries", []):
        relative_path = entry.get("path")
        target = entry.get("target")
        if isinstance(relative_path, str) and isinstance(target, str):
            mapping[relative_path] = target
    return mapping


def _target_entry_map(
    target_root: Path,
) -> tuple[dict[str, Path], dict[str, str], list[dict[str, str]], int]:
    file_mapping: dict[str, Path] = {}
    symlink_mapping: dict[str, str] = {}
    ignored: list[dict[str, str]] = []
    ignored_count = 0
    for path in sorted(target_root.rglob("*")):
        relative_path = str(path.relative_to(target_root))
        if path.is_symlink():
            symlink_mapping[relative_path] = os.readlink(path)
            continue
        if path.is_dir():
            continue
        if not path.is_file():
            ignored_count += 1
            if len(ignored) < MAX_SAMPLE_COUNT:
                ignored.append({"path": relative_path, "reason": "unsupported_file_type"})
            continue
        if _is_sqlite_sidecar(path):
            ignored_count += 1
            if len(ignored) < MAX_SAMPLE_COUNT:
                ignored.append({"path": relative_path, "reason": "sqlite_sidecar_not_compared"})
            continue
        file_mapping[relative_path] = path
    return file_mapping, symlink_mapping, ignored, ignored_count


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files_match(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    return _file_digest(left) == _file_digest(right)


def _materialize_current_comparison_path(
    current_path: Path, scratch_root: Path, relative_path: str
) -> Path:
    if not _is_sqlite_main(current_path):
        return current_path
    comparable_path = scratch_root / relative_path
    try:
        _copy_sqlite_database(current_path, comparable_path)
    except sqlite3.DatabaseError:
        comparable_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(current_path, comparable_path)
    return comparable_path


def _load_snapshot_bundle(path: Path, snapshot_ref: str) -> tuple[dict[str, Any], Path, dict[str, Any] | None]:
    if snapshot_ref == "latest":
        pointer_path = _latest_pointer_path(path)
        if not pointer_path.exists():
            raise FileNotFoundError("latest_snapshot_unavailable")
        latest_pointer = _read_json(pointer_path)
        snapshot_id = latest_pointer["snapshot_id"]
        pointer = latest_pointer
    else:
        snapshot_id = snapshot_ref
        pointer = None

    manifest_path = _snapshot_manifest_path(path, snapshot_id)
    if not manifest_path.exists():
        raise FileNotFoundError("snapshot_not_found")
    manifest = _read_json(manifest_path)
    files_root = manifest_path.parent / "files"
    return manifest, files_root, pointer


def _diff_snapshot_against_path(raw_path: str, snapshot_ref: str) -> tuple[dict[str, Any], dict[str, Any]]:
    target_root = _resolve_path(raw_path)
    if not target_root.exists():
        raise FileNotFoundError("missing_path")

    manifest, files_root, pointer = _load_snapshot_bundle(target_root, snapshot_ref)
    snapshot_files = _snapshot_file_map(files_root)
    snapshot_symlinks = _snapshot_symlink_map(manifest)

    actual_copied_files = len(snapshot_files)
    actual_copied_bytes = sum(path.stat().st_size for path in snapshot_files.values())
    manifest_integrity = {
        "copied_files_match": actual_copied_files == manifest.get("copied_files", 0),
        "copied_bytes_match": actual_copied_bytes == manifest.get("copied_bytes", 0),
        "captured_symlinks_match": len(snapshot_symlinks) == manifest.get("captured_symlink_count", 0),
        "expected_copied_files": manifest.get("copied_files", 0),
        "actual_copied_files": actual_copied_files,
        "expected_copied_bytes": manifest.get("copied_bytes", 0),
        "actual_copied_bytes": actual_copied_bytes,
        "expected_captured_symlinks": manifest.get("captured_symlink_count", 0),
        "actual_captured_symlinks": len(snapshot_symlinks),
    }

    target_files, target_symlinks, ignored_current_samples, ignored_current_count = _target_entry_map(target_root)
    changed_files: list[str] = []
    missing_files: list[str] = []
    verified_files = 0
    changed_symlinks: list[str] = []
    missing_symlinks: list[str] = []
    verified_symlinks = 0

    with TemporaryDirectory(prefix="reflexive-public-snapshot-compare-") as scratch_dir:
        scratch_root = Path(scratch_dir)
        for relative_path, snapshot_path in snapshot_files.items():
            current_path = target_files.get(relative_path)
            if current_path is None:
                if relative_path in target_symlinks:
                    changed_files.append(relative_path)
                    continue
                missing_files.append(relative_path)
                continue
            comparable_current_path = _materialize_current_comparison_path(
                current_path, scratch_root, relative_path
            )
            if _files_match(snapshot_path, comparable_current_path):
                verified_files += 1
                continue
            changed_files.append(relative_path)

    for relative_path, snapshot_target in snapshot_symlinks.items():
        current_target = target_symlinks.get(relative_path)
        if current_target is None:
            if relative_path in target_files:
                changed_symlinks.append(relative_path)
                continue
            missing_symlinks.append(relative_path)
            continue
        if current_target == snapshot_target:
            verified_symlinks += 1
            continue
        changed_symlinks.append(relative_path)

    snapshot_entry_paths = set(snapshot_files).union(snapshot_symlinks)
    extra_current_files = sorted(set(target_files).difference(snapshot_entry_paths))
    extra_current_symlinks = sorted(set(target_symlinks).difference(snapshot_entry_paths))
    comparison = {
        "path": str(target_root),
        "path_key": _path_key(target_root),
        "snapshot_id": manifest["id"],
        "snapshot_reference": snapshot_ref,
        "snapshot_pointer": pointer,
        "snapshot_path": str((files_root.parent)),
        "manifest": manifest,
        "manifest_integrity": manifest_integrity,
        "verified_files": verified_files,
        "verified_symlinks": verified_symlinks,
        "changed_files_count": len(changed_files),
        "changed_files_samples": changed_files[:MAX_SAMPLE_COUNT],
        "missing_files_count": len(missing_files),
        "missing_files_samples": missing_files[:MAX_SAMPLE_COUNT],
        "changed_symlinks_count": len(changed_symlinks),
        "changed_symlinks_samples": changed_symlinks[:MAX_SAMPLE_COUNT],
        "missing_symlinks_count": len(missing_symlinks),
        "missing_symlinks_samples": missing_symlinks[:MAX_SAMPLE_COUNT],
        "extra_current_files_count": len(extra_current_files),
        "extra_current_files_samples": extra_current_files[:MAX_SAMPLE_COUNT],
        "extra_current_symlinks_count": len(extra_current_symlinks),
        "extra_current_symlinks_samples": extra_current_symlinks[:MAX_SAMPLE_COUNT],
        "ignored_current_count": ignored_current_count,
        "ignored_current_samples": ignored_current_samples,
    }
    return comparison, manifest


def create_snapshot(raw_path: str) -> dict[str, Any]:
    source_root = _resolve_path(raw_path)
    inspection = inspect_path(raw_path)
    if not inspection["exists"]:
        return {
            "error": "missing_path",
            "path": str(source_root),
        }
    if inspection["sqlite_holder_count"]:
        return {
            "error": "path_not_quiesced",
            "path": str(source_root),
            "sqlite_holder_count": inspection["sqlite_holder_count"],
            "sqlite_holder_samples": inspection["sqlite_holder_samples"],
        }

    snapshot_id = _allocate_snapshot_id(source_root)
    target_root = _snapshot_dir(source_root, snapshot_id)
    files_root = target_root / "files"
    files_root.mkdir(parents=True, exist_ok=False)

    copied_files = 0
    copied_bytes = 0
    sqlite_backup_files = 0
    sqlite_backup_samples: list[str] = []
    symlink_entries: list[dict[str, str]] = []
    skipped_count = 0
    skipped_samples: list[dict[str, str]] = []

    try:
        for path in sorted(source_root.rglob("*")):
            relative_path = path.relative_to(source_root)
            if path.is_symlink():
                symlink_entries.append({"path": str(relative_path), "target": os.readlink(path)})
                continue
            if path.is_dir():
                continue
            if not path.is_file():
                skipped_count += 1
                if len(skipped_samples) < MAX_SAMPLE_COUNT:
                    skipped_samples.append({"path": str(relative_path), "reason": "unsupported_file_type"})
                continue

            destination = files_root / relative_path
            if _is_sqlite_sidecar(path):
                skipped_count += 1
                if len(skipped_samples) < MAX_SAMPLE_COUNT:
                    skipped_samples.append({"path": str(relative_path), "reason": "sqlite_sidecar_skipped"})
                continue
            if _is_sqlite_main(path):
                try:
                    _copy_sqlite_database(path, destination)
                except sqlite3.DatabaseError:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, destination)
                else:
                    sqlite_backup_files += 1
                    if len(sqlite_backup_samples) < MAX_SAMPLE_COUNT:
                        sqlite_backup_samples.append(str(relative_path))
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)

            copied_files += 1
            copied_bytes += destination.stat().st_size
    except Exception:
        shutil.rmtree(target_root, ignore_errors=True)
        raise

    manifest = {
        "id": snapshot_id,
        "path": str(source_root),
        "path_key": _path_key(source_root),
        "created_at": _isoformat_z(),
        "storage": {
            "root": "files",
            "restore_modes": [],
            "sqlite_capture": "online_backup",
            "symlink_capture": "manifest",
        },
        "copied_files": copied_files,
        "copied_bytes": copied_bytes,
        "sqlite_backup_files": sqlite_backup_files,
        "sqlite_backup_samples": sqlite_backup_samples,
        "captured_symlink_count": len(symlink_entries),
        "captured_symlink_samples": [entry["path"] for entry in symlink_entries[:MAX_SAMPLE_COUNT]],
        "symlink_entries": symlink_entries,
        "skipped_count": skipped_count,
        "skipped_samples": skipped_samples,
        "warnings": [
            "Public snapshots are explicit-path machine-local copies stored under the app-owned state root.",
            "SQLite main databases are captured via SQLite backup when possible.",
            "SQLite sidecar files are skipped.",
            "Public restore workflows are not part of the current release yet.",
        ],
    }

    _write_target_metadata(source_root)
    _write_json(_snapshot_manifest_path(source_root, snapshot_id), manifest)
    latest_pointer = _set_latest_pointer(source_root, snapshot_id)
    return {
        "path": str(source_root),
        "path_key": _path_key(source_root),
        "snapshot": manifest,
        "snapshot_dir": str(target_root),
        "latest_pointer": latest_pointer,
    }


def list_snapshots(raw_path: str) -> dict[str, Any]:
    source_root = _resolve_path(raw_path)
    root = _snapshots_root(source_root)
    latest_pointer = _read_json(_latest_pointer_path(source_root)) if _latest_pointer_path(source_root).exists() else None
    snapshots: list[dict[str, Any]] = []
    if root.exists():
        for manifest_path in sorted(root.glob("*/manifest.json"), reverse=True):
            manifest = _read_json(manifest_path)
            manifest["snapshot_dir"] = str(manifest_path.parent)
            manifest["is_latest"] = bool(
                latest_pointer is not None and latest_pointer.get("snapshot_id") == manifest["id"]
            )
            snapshots.append(manifest)
    return {
        "path": str(source_root),
        "path_key": _path_key(source_root),
        "snapshot_count": len(snapshots),
        "latest_pointer": latest_pointer,
        "snapshots": snapshots,
    }


def latest_snapshot(raw_path: str) -> dict[str, Any]:
    listing = list_snapshots(raw_path)
    if not listing["snapshots"]:
        return {
            "error": "latest_snapshot_unavailable",
            "path": listing["path"],
            "path_key": listing["path_key"],
        }
    return {
        "path": listing["path"],
        "path_key": listing["path_key"],
        "latest_pointer": listing["latest_pointer"],
        "snapshot": listing["snapshots"][0],
    }


def verify_snapshot(raw_path: str, snapshot_ref: str = "latest") -> dict[str, Any]:
    target_root = _resolve_path(raw_path)
    try:
        comparison, manifest = _diff_snapshot_against_path(raw_path, snapshot_ref)
    except FileNotFoundError as exc:
        return {
            "error": str(exc),
            "path": str(target_root),
            "path_key": _path_key(target_root),
        }

    integrity = comparison["manifest_integrity"]
    status = "ok"
    if not integrity["copied_files_match"] or not integrity["copied_bytes_match"]:
        status = "error"
    elif (
        not integrity["captured_symlinks_match"]
        or comparison["changed_symlinks_count"]
        or comparison["missing_symlinks_count"]
        or comparison["extra_current_symlinks_count"]
        or comparison["changed_files_count"]
        or comparison["missing_files_count"]
        or comparison["extra_current_files_count"]
        or comparison["ignored_current_count"]
        or manifest.get("skipped_count", 0)
    ):
        status = "warn"

    return {
        **comparison,
        "status": status,
        "verified_at": _isoformat_z(),
        "warnings": manifest.get("warnings", []),
        "skipped_count": manifest.get("skipped_count", 0),
        "skipped_samples": manifest.get("skipped_samples", []),
    }


def diff_snapshot(raw_path: str, snapshot_ref: str = "latest") -> dict[str, Any]:
    target_root = _resolve_path(raw_path)
    try:
        comparison, manifest = _diff_snapshot_against_path(raw_path, snapshot_ref)
    except FileNotFoundError as exc:
        return {
            "error": str(exc),
            "path": str(target_root),
            "path_key": _path_key(target_root),
        }

    integrity = comparison["manifest_integrity"]
    status = "ok"
    if not integrity["copied_files_match"] or not integrity["copied_bytes_match"]:
        status = "error"
    elif (
        not integrity["captured_symlinks_match"]
        or comparison["changed_symlinks_count"]
        or comparison["missing_symlinks_count"]
        or comparison["extra_current_symlinks_count"]
        or comparison["changed_files_count"]
        or comparison["missing_files_count"]
        or comparison["extra_current_files_count"]
    ):
        status = "warn"

    return {
        **comparison,
        "status": status,
        "diffed_at": _isoformat_z(),
        "warnings": manifest.get("warnings", []),
        "skipped_count": manifest.get("skipped_count", 0),
        "skipped_samples": manifest.get("skipped_samples", []),
    }
