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
        self.assertIn("cortex inspect", payload["available_commands"])
        self.assertIn("cortex check", payload["available_commands"])
        self.assertIn("cortex doctor", payload["available_commands"])
        self.assertIn("cortex compare", payload["available_commands"])

    def test_cortex_inspect_reports_missing_path(self) -> None:
        missing = "/tmp/reflexive-public-missing-path"
        exit_code, output = self._run(["cortex", "inspect", missing, "--json"])
        payload = json.loads(output)
        self.assertEqual(exit_code, 0)
        self.assertFalse(payload["exists"])
        self.assertEqual(Path(payload["path"]), Path(missing))

    def test_cortex_check_reports_stale_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "state.sqlite").write_text("placeholder", encoding="utf-8")
            (root / "state.sqlite-wal").write_text("placeholder", encoding="utf-8")
            (root / "state.sqlite-shm").write_text("placeholder", encoding="utf-8")

            exit_code, output = self._run(["cortex", "check", str(root), "--json"])
            payload = json.loads(output)

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "warn")
            self.assertEqual(payload["inspection"]["sqlite_main_count"], 1)
            self.assertEqual(payload["inspection"]["sqlite_sidecar_count"], 2)
            self.assertEqual(payload["inspection"]["sqlite_holder_count"], 0)

    def test_cortex_doctor_returns_recommendations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "state.sqlite").write_text("placeholder", encoding="utf-8")

            exit_code, output = self._run(["cortex", "doctor", str(root), "--json"])
            payload = json.loads(output)

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertTrue(payload["recommendations"])

    def test_cortex_compare_reports_difference(self) -> None:
        with tempfile.TemporaryDirectory() as left_dir, tempfile.TemporaryDirectory() as right_dir:
            left = Path(left_dir)
            right = Path(right_dir)
            (left / "state.sqlite").write_text("placeholder", encoding="utf-8")

            exit_code, output = self._run(["cortex", "compare", str(left), str(right), "--json"])
            payload = json.loads(output)

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "warn")
            self.assertTrue(payload["differences"])


if __name__ == "__main__":
    unittest.main()
