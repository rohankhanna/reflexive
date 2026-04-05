from __future__ import annotations

import argparse
import json

from reflexive import __version__
from reflexive.cortex import check_path, inspect_path


def _status_payload() -> dict[str, object]:
    return {
        "tool": "reflexive",
        "version": __version__,
        "release_surface": "public-shell",
        "status": "early-public-release",
        "available_commands": ["status", "version", "cortex inspect", "cortex check"],
        "documented_domains": ["cortex"],
        "notes": [
            "This public release exposes read-only inspection commands for local tool-state directories.",
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

    if args.command == "cortex":
        if args.cortex_command == "inspect":
            _emit(inspect_path(args.path), args.json)
            return 0
        if args.cortex_command == "check":
            _emit(check_path(args.path), args.json)
            return 0
        parser.parse_args(["cortex", "--help"])
        return 0

    parser.print_help()
    return 0
