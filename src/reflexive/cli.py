from __future__ import annotations

import argparse
import json

from reflexive import __version__


def _status_payload() -> dict[str, object]:
    return {
        "tool": "reflexive",
        "version": __version__,
        "release_surface": "public-shell",
        "status": "early-public-release",
        "available_commands": ["status", "version"],
        "documented_domains": ["cortex", "doctor", "scratch", "scaffold"],
        "notes": [
            "This public release currently exposes a minimal installable CLI shell.",
            "The public docs describe the broader operator-safety direction of the project.",
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

    return parser


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

    parser.print_help()
    return 0
