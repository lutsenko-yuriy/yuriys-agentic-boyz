import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from scripts.onboard import onboard

try:
    import tomllib  # noqa: F401

    HAS_TOMLLIB = True
except ImportError:
    HAS_TOMLLIB = False

needs_toml = unittest.skipUnless(HAS_TOMLLIB, "tomllib needs Python 3.11+")


class PrefixTests(unittest.TestCase):
    def test_rejects_invalid(self):
        for bad in ["", "N/A", "n/a", "NA", "na", "A B", "1AB", "A", "ABCDEFGHIJK", "  "]:
            self.assertFalse(onboard.valid_prefix(bad), bad)

    def test_accepts_valid(self):
        for good in ["HAB", "CheL", "GH", "HL", "A1", "ABCDEFGHIJ"]:
            self.assertTrue(onboard.valid_prefix(good), good)

    def test_defaults(self):
        self.assertEqual(onboard.default_prefix("Habit Loop"), "HL")
        self.assertEqual(onboard.default_prefix("CheckLister"), "CL")
        self.assertEqual(onboard.default_prefix("mordovorot"), "MOR")


class ProbeTests(unittest.TestCase):
    def test_reports_env_names_never_values(self):
        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sekrit-value", "HOME": "/x"}):
            data = onboard.probe()
        self.assertIn("OPENAI_API_KEY", data["env_vars_set"])
        self.assertNotIn("sekrit-value", json.dumps(data))

    def test_toolchains_via_which_without_executing(self):
        with mock.patch("shutil.which", side_effect=lambda n: "/bin/" + n if n == "git" else None), mock.patch(
            "subprocess.run", side_effect=AssertionError("must not execute")
        ):
            data = onboard.probe(run_tools=False)
        self.assertEqual(data["toolchains"]["git"], True)
        self.assertEqual(data["toolchains"]["flutter"], False)

    def test_python_versions_with_tomllib_from_names(self):
        with mock.patch("shutil.which", side_effect=lambda n: "/bin/" + n if n in ("python3.12", "python3.10") else None):
            data = onboard.probe(run_tools=False)
        self.assertEqual(data["pythons_with_tomllib"], ["python3.12"])


class LoadTomlTests(unittest.TestCase):
    def test_missing_tomllib_fails_loudly_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.toml"
            p.write_text("a = 1\n")
            with mock.patch.dict(sys.modules, {"tomllib": None}):
                with self.assertRaises(SystemExit) as cm, mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                    onboard.load_toml(p)
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("python3.12", err.getvalue())

    def test_probe_cli_works_without_tomllib(self):
        with mock.patch.dict(sys.modules, {"tomllib": None}), redirect_stdout(io.StringIO()) as out:
            code = onboard.main(["probe"])
        self.assertEqual(code, 0)
        json.loads(out.getvalue())
