import tempfile
import unittest
from pathlib import Path

from skill_router.config import load_config


def config_from(text):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "skill_router.toml"
        path.write_text(text)
        return load_config(str(path))


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


if __name__ == "__main__":
    unittest.main()
