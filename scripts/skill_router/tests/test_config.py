import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from skill_router.config import load_config, tomllib


def config_from(text):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "skill_router.toml"
        path.write_text(text)
        return load_config(str(path))


@unittest.skipIf(tomllib is None, "tomllib needs Python 3.11+")
class ProjectIdTests(unittest.TestCase):
    def test_project_table_is_not_a_provider(self):
        self.assertNotIn("project", config_from('[project]\nname = "X"\n').provider_settings)

    def test_project_id_feeds_linear(self):
        cfg = config_from('[project]\nproject_id = " p1 "\n')
        self.assertEqual(cfg.provider_settings["linear"], {"project_id": "p1"})

    def test_project_id_wins_over_legacy_linear(self):
        cfg = config_from('[project]\nproject_id = "p1"\n\n[linear]\nproject_id = "old"\nother = 1\n')
        self.assertEqual(cfg.provider_settings["linear"], {"project_id": "p1", "other": 1})

    def test_empty_project_id_keeps_legacy_linear(self):
        cfg = config_from('[project]\nproject_id = ""\n\n[linear]\nproject_id = "old"\n')
        self.assertEqual(cfg.provider_settings["linear"], {"project_id": "old"})

    def test_no_project_id_anywhere(self):
        self.assertNotIn("linear", config_from('[providers]\npm = "linear"\n').provider_settings)


class MissingTomllibTests(unittest.TestCase):
    def test_warns_when_config_exists_but_cannot_be_read(self):
        stderr = io.StringIO()
        with patch("skill_router.config.tomllib", None), redirect_stderr(stderr):
            cfg = config_from('[providers]\npm = "github"\n')
        self.assertEqual(cfg.provider_roles, {})
        self.assertIn("Python 3.11+", stderr.getvalue())

    def test_silent_when_no_config_file(self):
        stderr = io.StringIO()
        with patch("skill_router.config.tomllib", None), redirect_stderr(stderr):
            load_config("does/not/exist.toml")
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
