from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reflexive.cli import main


class ReflexiveCliTest(unittest.TestCase):
    def _run(self, argv: list[str]) -> tuple[int, str]:
        buffer = io.StringIO()
        with patch("sys.stdout", buffer):
            exit_code = main(argv)
        return exit_code, buffer.getvalue()

    def test_status_json_lists_public_commands(self) -> None:
        exit_code, output = self._run(["status", "--json"])
        payload = json.loads(output)
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["tool"], "reflexive")
        self.assertIn("paths", payload["available_commands"])
        self.assertIn("purge", payload["available_commands"])
        self.assertIn("cortex inspect", payload["available_commands"])
        self.assertIn("cortex check", payload["available_commands"])
        self.assertIn("cortex doctor", payload["available_commands"])
        self.assertIn("cortex compare", payload["available_commands"])
        self.assertIn("cortex snapshot create", payload["available_commands"])
        self.assertIn("cortex snapshot list", payload["available_commands"])
        self.assertIn("cortex snapshot latest", payload["available_commands"])
        self.assertIn("cortex snapshot verify", payload["available_commands"])
        self.assertIn("cortex snapshot diff", payload["available_commands"])

    def test_version_json_reports_version(self) -> None:
        exit_code, output = self._run(["version", "--json"])
        payload = json.loads(output)
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["tool"], "reflexive")
        self.assertTrue(payload["version"])

    def test_paths_json_uses_xdg_environment(self) -> None:
        env = {
            "XDG_CONFIG_HOME": "/tmp/reflexive-test-config",
            "XDG_STATE_HOME": "/tmp/reflexive-test-state",
            "XDG_CACHE_HOME": "/tmp/reflexive-test-cache",
            "XDG_RUNTIME_DIR": "/tmp/reflexive-test-runtime",
        }
        with patch.dict("os.environ", env, clear=False):
            exit_code, output = self._run(["paths", "--json"])
        payload = json.loads(output)
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["paths"]["config"], "/tmp/reflexive-test-config/reflexive")
        self.assertEqual(payload["paths"]["state"], "/tmp/reflexive-test-state/reflexive")
        self.assertEqual(payload["paths"]["cache"], "/tmp/reflexive-test-cache/reflexive")
        self.assertEqual(payload["paths"]["runtime"], "/tmp/reflexive-test-runtime/reflexive")

    def test_purge_all_removes_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            env = {
                "XDG_CONFIG_HOME": str(base / "config"),
                "XDG_STATE_HOME": str(base / "state"),
                "XDG_CACHE_HOME": str(base / "cache"),
                "XDG_RUNTIME_DIR": str(base / "runtime"),
            }
            for key in ("config", "state", "cache", "runtime"):
                (base / key / "reflexive").mkdir(parents=True, exist_ok=True)

            with patch.dict("os.environ", env, clear=False):
                exit_code, output = self._run(["purge", "--all", "--yes", "--json"])

            payload = json.loads(output)
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "purged")
            for action in payload["actions"]:
                self.assertTrue(action["removed"])


if __name__ == "__main__":
    unittest.main()
