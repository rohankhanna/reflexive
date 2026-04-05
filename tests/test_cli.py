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

    def test_snapshot_create_list_and_latest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            source.mkdir()
            (source / "state.sqlite").write_text("placeholder", encoding="utf-8")
            env = {"XDG_STATE_HOME": str(base / "state")}

            with patch.dict("os.environ", env, clear=False):
                create_code, create_output = self._run(["cortex", "snapshot", "create", str(source), "--json"])
                list_code, list_output = self._run(["cortex", "snapshot", "list", str(source), "--json"])
                latest_code, latest_output = self._run(["cortex", "snapshot", "latest", str(source), "--json"])

            create_payload = json.loads(create_output)
            list_payload = json.loads(list_output)
            latest_payload = json.loads(latest_output)

            self.assertEqual(create_code, 0)
            self.assertEqual(list_code, 0)
            self.assertEqual(latest_code, 0)
            self.assertEqual(list_payload["snapshot_count"], 1)
            self.assertEqual(latest_payload["snapshot"]["id"], create_payload["snapshot"]["id"])

    def test_snapshot_verify_and_diff_warn_after_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            source.mkdir()
            file_path = source / "file.txt"
            file_path.write_text("before", encoding="utf-8")
            env = {"XDG_STATE_HOME": str(base / "state")}

            with patch.dict("os.environ", env, clear=False):
                self._run(["cortex", "snapshot", "create", str(source), "--json"])
                file_path.write_text("after", encoding="utf-8")
                verify_code, verify_output = self._run(
                    ["cortex", "snapshot", "verify", str(source), "--json"]
                )
                diff_code, diff_output = self._run(
                    ["cortex", "snapshot", "diff", str(source), "--json"]
                )

            verify_payload = json.loads(verify_output)
            diff_payload = json.loads(diff_output)

            self.assertEqual(verify_code, 0)
            self.assertEqual(diff_code, 0)
            self.assertEqual(verify_payload["status"], "warn")
            self.assertEqual(diff_payload["status"], "warn")
            self.assertEqual(verify_payload["changed_files_count"], 1)
            self.assertEqual(diff_payload["changed_files_count"], 1)

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
