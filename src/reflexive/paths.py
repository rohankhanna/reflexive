from __future__ import annotations

import os
from pathlib import Path
import shutil
from typing import Any


def _home() -> Path:
    return Path.home().expanduser().resolve()


def _xdg_path(env_name: str, fallback_relative: str) -> Path:
    value = os.environ.get(env_name)
    if value:
        return Path(value).expanduser().resolve() / "reflexive"
    return (_home() / fallback_relative / "reflexive").resolve()


def resolve_app_paths() -> dict[str, str]:
    runtime_base = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_base:
        runtime_root = Path(runtime_base).expanduser().resolve() / "reflexive"
    else:
        runtime_root = Path("/tmp") / f"reflexive-{os.getuid()}"

    return {
        "config": str(_xdg_path("XDG_CONFIG_HOME", ".config")),
        "state": str(_xdg_path("XDG_STATE_HOME", ".local/state")),
        "cache": str(_xdg_path("XDG_CACHE_HOME", ".cache")),
        "runtime": str(runtime_root.resolve()),
    }


def _selected_roots(
    *,
    config: bool,
    state: bool,
    cache: bool,
    runtime: bool,
    all_roots: bool,
) -> list[str]:
    if all_roots:
        return ["config", "state", "cache", "runtime"]
    selected: list[str] = []
    if config:
        selected.append("config")
    if state:
        selected.append("state")
    if cache:
        selected.append("cache")
    if runtime:
        selected.append("runtime")
    return selected


def purge_app_paths(
    *,
    config: bool = False,
    state: bool = False,
    cache: bool = False,
    runtime: bool = False,
    all_roots: bool = False,
    apply: bool = False,
) -> dict[str, Any]:
    paths = resolve_app_paths()
    selected = _selected_roots(
        config=config,
        state=state,
        cache=cache,
        runtime=runtime,
        all_roots=all_roots,
    )
    if not selected:
        selected = ["state", "cache", "runtime"]

    actions: list[dict[str, Any]] = []
    for name in selected:
        path = Path(paths[name])
        exists = path.exists()
        removed = False
        if apply and exists:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed = True
        actions.append(
            {
                "root": name,
                "path": str(path),
                "exists": exists,
                "removed": removed,
            }
        )

    return {
        "tool": "reflexive",
        "status": "purged" if apply else "dry_run",
        "selected_roots": selected,
        "actions": actions,
        "automatic_uninstall_cleanup_supported": False,
        "recommended_uninstall_sequence": [
            "reflexive purge --all --yes",
            "python3 -m pip uninstall reflexive",
        ],
    }
