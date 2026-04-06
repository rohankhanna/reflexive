from __future__ import annotations

import argparse
import json
import sys

from reflexive import __version__
from reflexive.cortex import check_path, compare_paths, doctor_path, inspect_path
from reflexive.paths import purge_app_paths, resolve_app_paths
from reflexive.snapshots import (
    create_snapshot,
    diff_snapshot,
    latest_snapshot,
    list_snapshots,
    verify_snapshot,
)


def status_payload() -> dict[str, object]:
    return {
        "tool": "reflexive",
        "version": __version__,
        "release_surface": "public-shell",
        "status": "early-public-release",
        "available_commands": [
            "status",
            "version",
            "paths",
            "purge",
            "cortex inspect",
            "cortex check",
            "cortex doctor",
            "cortex compare",
            "cortex snapshot create",
            "cortex snapshot list",
            "cortex snapshot latest",
            "cortex snapshot verify",
            "cortex snapshot diff",
        ],
        "documented_domains": ["cortex", "app-paths"],
        "notes": [
            "This public release exposes read-only inspection commands plus explicit app-owned snapshot management for local tool-state directories.",
            "Future mutable state is intended to live under app-owned config/state/cache/runtime roots rather than inside the repo checkout.",
            "State-changing recovery and staging workflows are not part of the current public release.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reflexive",
        description="Minimal public CLI shell for reflexive.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser(
        "status",
        help="Show public release metadata for this shell.",
    )
    status_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    version_parser = subparsers.add_parser(
        "version",
        help="Show the public release version.",
    )
    version_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    paths_parser = subparsers.add_parser(
        "paths",
        help="Show the app-owned config, state, cache, and runtime roots.",
    )
    paths_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    purge_parser = subparsers.add_parser(
        "purge",
        help="Delete app-owned config, state, cache, and runtime roots.",
    )
    purge_parser.add_argument("--config", action="store_true", help="Select the config root.")
    purge_parser.add_argument("--state", action="store_true", help="Select the state root.")
    purge_parser.add_argument("--cache", action="store_true", help="Select the cache root.")
    purge_parser.add_argument("--runtime", action="store_true", help="Select the runtime root.")
    purge_parser.add_argument("--all", action="store_true", help="Select all roots.")
    purge_parser.add_argument("--yes", action="store_true", help="Apply deletion instead of showing a dry run.")
    purge_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    cortex_parser = subparsers.add_parser(
        "cortex",
        help="Inspect local tool-state directories.",
    )
    cortex_subparsers = cortex_parser.add_subparsers(dest="cortex_command", required=True)

    cortex_inspect_parser = cortex_subparsers.add_parser(
        "inspect",
        help="Inspect a tool-state directory without modifying it.",
    )
    cortex_inspect_parser.add_argument("path", help="Path to inspect.")
    cortex_inspect_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    cortex_check_parser = cortex_subparsers.add_parser(
        "check",
        help="Evaluate basic operator-risk signals for a tool-state directory.",
    )
    cortex_check_parser.add_argument("path", help="Path to inspect.")
    cortex_check_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    cortex_doctor_parser = cortex_subparsers.add_parser(
        "doctor",
        help="Add operator-facing recommendations for a tool-state directory.",
    )
    cortex_doctor_parser.add_argument("path", help="Path to inspect.")
    cortex_doctor_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    cortex_compare_parser = cortex_subparsers.add_parser(
        "compare",
        help="Compare two tool-state directories without modifying either one.",
    )
    cortex_compare_parser.add_argument("left_path", help="First path to inspect.")
    cortex_compare_parser.add_argument("right_path", help="Second path to inspect.")
    cortex_compare_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    cortex_snapshot_parser = cortex_subparsers.add_parser(
        "snapshot",
        help="Store and inspect app-owned snapshots for explicit paths.",
    )
    cortex_snapshot_subparsers = cortex_snapshot_parser.add_subparsers(
        dest="snapshot_command", required=True
    )

    cortex_snapshot_create_parser = cortex_snapshot_subparsers.add_parser(
        "create",
        help="Create an app-owned snapshot for a path.",
    )
    cortex_snapshot_create_parser.add_argument("path", help="Path to snapshot.")
    cortex_snapshot_create_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    cortex_snapshot_list_parser = cortex_snapshot_subparsers.add_parser(
        "list",
        help="List snapshots stored for a path.",
    )
    cortex_snapshot_list_parser.add_argument("path", help="Path whose snapshots should be listed.")
    cortex_snapshot_list_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    cortex_snapshot_latest_parser = cortex_snapshot_subparsers.add_parser(
        "latest",
        help="Show the latest snapshot stored for a path.",
    )
    cortex_snapshot_latest_parser.add_argument("path", help="Path whose latest snapshot should be shown.")
    cortex_snapshot_latest_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    cortex_snapshot_verify_parser = cortex_snapshot_subparsers.add_parser(
        "verify",
        help="Verify a path against a stored snapshot.",
    )
    cortex_snapshot_verify_parser.add_argument("path", help="Path to verify.")
    cortex_snapshot_verify_parser.add_argument("snapshot_ref", nargs="?", default="latest")
    cortex_snapshot_verify_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    cortex_snapshot_diff_parser = cortex_snapshot_subparsers.add_parser(
        "diff",
        help="Show differences between a path and a stored snapshot.",
    )
    cortex_snapshot_diff_parser.add_argument("path", help="Path to diff.")
    cortex_snapshot_diff_parser.add_argument("snapshot_ref", nargs="?", default="latest")
    cortex_snapshot_diff_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    return parser


def dispatch(args: argparse.Namespace) -> dict[str, object]:
    if args.command == "status":
        return status_payload()
    if args.command == "version":
        return {"tool": "reflexive", "version": __version__}
    if args.command == "paths":
        return {
            "tool": "reflexive",
            "paths": resolve_app_paths(),
            "automatic_uninstall_cleanup_supported": False,
            "recommended_uninstall_sequence": [
                "reflexive purge --all --yes",
                "python3 -m pip uninstall reflexive",
            ],
        }
    if args.command == "purge":
        return purge_app_paths(
            config=args.config,
            state=args.state,
            cache=args.cache,
            runtime=args.runtime,
            all_roots=args.all,
            apply=args.yes,
        )
    if args.command == "cortex":
        if args.cortex_command == "inspect":
            return inspect_path(args.path)
        if args.cortex_command == "check":
            return check_path(args.path)
        if args.cortex_command == "doctor":
            return doctor_path(args.path)
        if args.cortex_command == "compare":
            return compare_paths(args.left_path, args.right_path)
        if args.cortex_command == "snapshot":
            if args.snapshot_command == "create":
                return create_snapshot(args.path)
            if args.snapshot_command == "list":
                return list_snapshots(args.path)
            if args.snapshot_command == "latest":
                return latest_snapshot(args.path)
            if args.snapshot_command == "verify":
                return verify_snapshot(args.path, args.snapshot_ref)
            if args.snapshot_command == "diff":
                return diff_snapshot(args.path, args.snapshot_ref)
    raise ValueError("unsupported command")


def emit(payload: dict[str, object], as_json: bool, command: str, *, apply: bool = False) -> None:
    if as_json:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return
    if command == "status":
        sys.stdout.write("reflexive 0.1.0\n")
        sys.stdout.write("public shell: early public release\n")
        sys.stdout.write("commands: status, version\n")
        return
    if command == "version":
        sys.stdout.write(str(payload["version"]) + "\n")
        return
    if command == "purge" and not apply:
        sys.stderr.write(
            "dry run only; rerun with --yes to remove the selected app-owned roots\n"
        )
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = dispatch(args)
    emit(payload, getattr(args, "json", False), args.command, apply=getattr(args, "yes", False))
    return 0
