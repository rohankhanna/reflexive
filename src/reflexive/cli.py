from __future__ import annotations

import argparse
import json
import sys

from reflexive import __version__
from reflexive.cortex import check_path, compare_paths, doctor_path, inspect_path
from reflexive.paths import purge_app_paths, resolve_app_paths
from reflexive.snapshots import create_snapshot, diff_snapshot, latest_snapshot, list_snapshots, verify_snapshot


def _status_payload() -> dict[str, object]:
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reflexive",
        description="Minimal public CLI shell for reflexive.",
    )
    subparsers = parser.add_subparsers(dest="command")

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
    cortex_subparsers = cortex_parser.add_subparsers(dest="cortex_command")

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
    cortex_snapshot_subparsers = cortex_snapshot_parser.add_subparsers(dest="snapshot_command")

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


def _emit(payload: dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    print(json.dumps(payload, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "status":
        payload = _status_payload()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("reflexive 0.1.0")
            print("public shell: early public release")
            print("commands: status, version")
        return 0

    if args.command == "version":
        payload = {"tool": "reflexive", "version": __version__}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(__version__)
        return 0

    if args.command == "paths":
        payload = {
            "tool": "reflexive",
            "paths": resolve_app_paths(),
            "automatic_uninstall_cleanup_supported": False,
            "recommended_uninstall_sequence": [
                "reflexive purge --all --yes",
                "python3 -m pip uninstall reflexive",
            ],
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(json.dumps(payload, indent=2))
        return 0

    if args.command == "purge":
        payload = purge_app_paths(
            config=args.config,
            state=args.state,
            cache=args.cache,
            runtime=args.runtime,
            all_roots=args.all,
            apply=args.yes,
        )
        if not args.json and not args.yes:
            sys.stderr.write(
                "dry run only; rerun with --yes to remove the selected app-owned roots\n"
            )
        _emit(payload, args.json)
        return 0

    if args.command == "cortex":
        if args.cortex_command == "inspect":
            _emit(inspect_path(args.path), args.json)
            return 0
        if args.cortex_command == "check":
            _emit(check_path(args.path), args.json)
            return 0
        if args.cortex_command == "doctor":
            _emit(doctor_path(args.path), args.json)
            return 0
        if args.cortex_command == "compare":
            _emit(compare_paths(args.left_path, args.right_path), args.json)
            return 0
        if args.cortex_command == "snapshot":
            if args.snapshot_command == "create":
                _emit(create_snapshot(args.path), args.json)
                return 0
            if args.snapshot_command == "list":
                _emit(list_snapshots(args.path), args.json)
                return 0
            if args.snapshot_command == "latest":
                _emit(latest_snapshot(args.path), args.json)
                return 0
            if args.snapshot_command == "verify":
                _emit(verify_snapshot(args.path, args.snapshot_ref), args.json)
                return 0
            if args.snapshot_command == "diff":
                _emit(diff_snapshot(args.path, args.snapshot_ref), args.json)
                return 0
        parser.parse_args(["cortex", "--help"])
        return 0

    parser.print_help()
    return 0
