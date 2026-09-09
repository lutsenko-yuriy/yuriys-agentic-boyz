import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.notes import index


def write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class ParseNoteTests(unittest.TestCase):
    def test_no_frontmatter_is_missing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "HAB-1.md"
            write(note, "# HAB-1: Title\n\nBody.\n")
            has_key, bookmarks = index.parse_note(note)
            self.assertFalse(has_key)
            self.assertEqual(bookmarks, [])

    def test_frontmatter_without_bookmarks_key_is_missing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "HAB-1.md"
            write(note, "---\nother: value\n---\n\n# HAB-1: Title\n")
            has_key, bookmarks = index.parse_note(note)
            self.assertFalse(has_key)

    def test_explicit_empty_list_is_present_but_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "HAB-1.md"
            write(note, "---\nbookmarks: []\n---\n\n# HAB-1: Title\n")
            has_key, bookmarks = index.parse_note(note)
            self.assertTrue(has_key)
            self.assertEqual(bookmarks, [])

    def test_populated_list_is_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "HAB-1.md"
            write(note, "---\nbookmarks: [ci-flakiness, scope-creep]\n---\n\n# HAB-1: Title\n")
            has_key, bookmarks = index.parse_note(note)
            self.assertTrue(has_key)
            self.assertEqual(bookmarks, ["ci-flakiness", "scope-creep"])

    def test_quoted_items_are_unquoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "HAB-1.md"
            write(note, "---\nbookmarks: ['ci-flakiness', \"scope-creep\"]\n---\n\n# HAB-1: Title\n")
            has_key, bookmarks = index.parse_note(note)
            self.assertEqual(bookmarks, ["ci-flakiness", "scope-creep"])


class MalformedBookmarksTests(unittest.TestCase):
    def test_inline_list_is_not_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "HAB-1.md"
            write(note, "---\nbookmarks: [ci-flakiness]\n---\n\n# HAB-1: T\n")
            self.assertIsNone(index.detect_malformed_bookmarks(note))

    def test_no_frontmatter_is_not_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "HAB-1.md"
            write(note, "# HAB-1: T\n\nBody.\n")
            self.assertIsNone(index.detect_malformed_bookmarks(note))

    def test_block_style_list_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "HAB-1.md"
            write(note, "---\nbookmarks:\n  - ci-flakiness\n---\n\n# HAB-1: T\n")
            error = index.detect_malformed_bookmarks(note)
            self.assertIsNotNone(error)
            self.assertIn("block-list", error)


class LoadVocabularyTests(unittest.TestCase):
    def test_missing_file_yields_empty_vocabulary(self):
        self.assertEqual(index.load_vocabulary(Path("/nonexistent/BOOKMARKS.md")), set())

    def test_reads_bookmark_names_from_table_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            vocab_file = Path(tmp) / "BOOKMARKS.md"
            write(
                vocab_file,
                "# Bookmarks\n\n"
                "| Bookmark | Meaning |\n"
                "|---|---|\n"
                "| `ci-flakiness` | Intermittent CI failures |\n"
                "| `scope-creep` | Ticket grew mid-flight |\n",
            )
            self.assertEqual(index.load_vocabulary(vocab_file), {"ci-flakiness", "scope-creep"})

    def test_malformed_rows_are_excluded_from_vocabulary_not_silently_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            vocab_file = Path(tmp) / "BOOKMARKS.md"
            write(
                vocab_file,
                "# Bookmarks\n\n"
                "| Bookmark | Meaning |\n"
                "|---|---|\n"
                "| `CI-Flakiness` | Wrong case |\n"
                "| `scope creep` | Has a space |\n"
                "| `ok-one` | Valid |\n",
            )
            self.assertEqual(index.load_vocabulary(vocab_file), {"ok-one"})

    def test_validate_vocabulary_reports_malformed_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            vocab_file = Path(tmp) / "BOOKMARKS.md"
            write(
                vocab_file,
                "# Bookmarks\n\n| Bookmark | Meaning |\n|---|---|\n| `CI-Flakiness` | Wrong case |\n",
            )
            errors = index.validate_vocabulary(vocab_file)
            self.assertTrue(any("CI-Flakiness" in e for e in errors))

    def test_validate_vocabulary_clean_table_has_no_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            vocab_file = Path(tmp) / "BOOKMARKS.md"
            write(
                vocab_file,
                "# Bookmarks\n\n| Bookmark | Meaning |\n|---|---|\n| `ci-flakiness` | x |\n",
            )
            self.assertEqual(index.validate_vocabulary(vocab_file), [])


class CheckTests(unittest.TestCase):
    def _setup_corpus(self, tmp, notes):
        notes_dir = Path(tmp) / "notes"
        notes_dir.mkdir()
        for name, content in notes.items():
            write(notes_dir / name, content)
        vocab_file = notes_dir / "BOOKMARKS.md"
        write(
            vocab_file,
            "# Bookmarks\n\n| Bookmark | Meaning |\n|---|---|\n| `ci-flakiness` | Intermittent CI failures |\n",
        )
        return notes_dir, vocab_file

    def test_clean_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir, vocab_file = self._setup_corpus(
                tmp, {"HAB-1.md": "---\nbookmarks: [ci-flakiness]\n---\n\n# HAB-1: T\n"}
            )
            index_file = notes_dir / "INDEX.md"
            index.write_index(notes_dir, vocab_file, index_file)
            errors = index.check(notes_dir, vocab_file, index_file)
            self.assertEqual(errors, [])

    def test_missing_bookmarks_key_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir, vocab_file = self._setup_corpus(tmp, {"HAB-1.md": "# HAB-1: T\n\nBody.\n"})
            index_file = notes_dir / "INDEX.md"
            index.write_index(notes_dir, vocab_file, index_file)
            errors = index.check(notes_dir, vocab_file, index_file)
            self.assertTrue(any("missing" in e and "HAB-1.md" in e for e in errors))

    def test_explicit_empty_list_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir, vocab_file = self._setup_corpus(tmp, {"HAB-1.md": "---\nbookmarks: []\n---\n\n# HAB-1: T\n"})
            index_file = notes_dir / "INDEX.md"
            index.write_index(notes_dir, vocab_file, index_file)
            errors = index.check(notes_dir, vocab_file, index_file)
            self.assertEqual(errors, [])

    def test_unknown_bookmark_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir, vocab_file = self._setup_corpus(
                tmp, {"HAB-1.md": "---\nbookmarks: [not-in-vocabulary]\n---\n\n# HAB-1: T\n"}
            )
            index_file = notes_dir / "INDEX.md"
            index.write_index(notes_dir, vocab_file, index_file)
            errors = index.check(notes_dir, vocab_file, index_file)
            self.assertTrue(any("unknown bookmark" in e and "not-in-vocabulary" in e for e in errors))

    def test_stale_index_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir, vocab_file = self._setup_corpus(
                tmp, {"HAB-1.md": "---\nbookmarks: [ci-flakiness]\n---\n\n# HAB-1: T\n"}
            )
            index_file = notes_dir / "INDEX.md"
            write(index_file, "stale content\n")
            errors = index.check(notes_dir, vocab_file, index_file)
            self.assertTrue(any("stale" in e for e in errors))

    def test_block_style_bookmarks_fails_with_specific_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir, vocab_file = self._setup_corpus(
                tmp, {"HAB-1.md": "---\nbookmarks:\n  - ci-flakiness\n---\n\n# HAB-1: T\n"}
            )
            index_file = notes_dir / "INDEX.md"
            index.write_index(notes_dir, vocab_file, index_file)
            errors = index.check(notes_dir, vocab_file, index_file)
            self.assertTrue(any("block-list" in e and "HAB-1.md" in e for e in errors))
            self.assertFalse(any("missing" in e for e in errors))

    def test_malformed_vocabulary_row_surfaces_as_its_own_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = Path(tmp) / "notes"
            notes_dir.mkdir()
            vocab_file = notes_dir / "BOOKMARKS.md"
            write(
                vocab_file,
                "# Bookmarks\n\n| Bookmark | Meaning |\n|---|---|\n| `CI-Flakiness` | Wrong case |\n",
            )
            index_file = notes_dir / "INDEX.md"
            index.write_index(notes_dir, vocab_file, index_file)
            errors = index.check(notes_dir, vocab_file, index_file)
            self.assertTrue(any("CI-Flakiness" in e and "not a valid bookmark name" in e for e in errors))

    def test_template_and_generated_files_are_excluded_from_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir, vocab_file = self._setup_corpus(
                tmp, {"HAB-1.md": "---\nbookmarks: [ci-flakiness]\n---\n\n# HAB-1: T\n"}
            )
            write(notes_dir / "TEMPLATE.md", "---\nbookmarks: []\n---\n\n# HAB-XX: <title>\n")
            index_file = notes_dir / "INDEX.md"
            index.write_index(notes_dir, vocab_file, index_file)
            errors = index.check(notes_dir, vocab_file, index_file)
            self.assertEqual(errors, [])


def _init_git_repo(repo_dir: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)


class IterNotesTests(unittest.TestCase):
    def test_untracked_note_is_excluded_in_a_git_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp)
            _init_git_repo(repo_dir)
            notes_dir = repo_dir / "notes"
            notes_dir.mkdir()
            write(notes_dir / "HAB-1.md", "---\nbookmarks: []\n---\n\n# HAB-1: Tracked\n")
            subprocess.run(["git", "add", "notes/HAB-1.md"], cwd=repo_dir, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "add HAB-1"], cwd=repo_dir, check=True)
            # HAB-2 is never `git add`ed — simulates a note file for an
            # unrelated, not-yet-committed ticket sitting in the working tree.
            write(notes_dir / "HAB-2.md", "---\nbookmarks: []\n---\n\n# HAB-2: Untracked\n")

            names = [p.name for p in index.iter_notes(notes_dir)]

            self.assertEqual(names, ["HAB-1.md"])

    def test_staged_but_uncommitted_note_is_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp)
            _init_git_repo(repo_dir)
            notes_dir = repo_dir / "notes"
            notes_dir.mkdir()
            write(notes_dir / "HAB-1.md", "---\nbookmarks: []\n---\n\n# HAB-1: Staged\n")
            subprocess.run(["git", "add", "notes/HAB-1.md"], cwd=repo_dir, check=True)
            # Deliberately not committed — still in the index, which is what matters.

            names = [p.name for p in index.iter_notes(notes_dir)]

            self.assertEqual(names, ["HAB-1.md"])

    def test_falls_back_to_including_everything_when_git_is_unavailable(self):
        # Forces the fallback path deterministically rather than relying on
        # tempfile.TemporaryDirectory() happening to land outside a repo —
        # that assumption doesn't hold everywhere (HAB-250 audit).
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = Path(tmp) / "notes"
            notes_dir.mkdir()
            write(notes_dir / "HAB-1.md", "---\nbookmarks: []\n---\n\n# HAB-1: T\n")

            with mock.patch("scripts.notes.index.subprocess.run", side_effect=FileNotFoundError):
                names = [p.name for p in index.iter_notes(notes_dir)]

            self.assertEqual(names, ["HAB-1.md"])

    def test_tracked_note_names_returns_none_when_git_invocation_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            with mock.patch("scripts.notes.index.subprocess.run", side_effect=FileNotFoundError):
                self.assertIsNone(index._tracked_note_names(notes_dir))

    def test_excluded_files_stay_excluded_even_when_tracked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp)
            _init_git_repo(repo_dir)
            notes_dir = repo_dir / "notes"
            notes_dir.mkdir()
            write(notes_dir / "HAB-1.md", "---\nbookmarks: []\n---\n\n# HAB-1: T\n")
            write(notes_dir / "TEMPLATE.md", "template")
            subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "add notes"], cwd=repo_dir, check=True)

            names = [p.name for p in index.iter_notes(notes_dir)]

            self.assertEqual(names, ["HAB-1.md"])


class GenerateIndexTests(unittest.TestCase):
    def test_regeneration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = Path(tmp) / "notes"
            notes_dir.mkdir()
            write(notes_dir / "HAB-1.md", "---\nbookmarks: [ci-flakiness]\n---\n\n# HAB-1: T\n")
            vocab_file = notes_dir / "BOOKMARKS.md"
            write(vocab_file, "# Bookmarks\n\n| Bookmark | Meaning |\n|---|---|\n| `ci-flakiness` | x |\n")
            first = index.render_index(notes_dir, vocab_file)
            second = index.render_index(notes_dir, vocab_file)
            self.assertEqual(first, second)

    def test_notes_grouped_under_their_bookmark(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = Path(tmp) / "notes"
            notes_dir.mkdir()
            write(notes_dir / "HAB-1.md", "---\nbookmarks: [ci-flakiness]\n---\n\n# HAB-1: One\n")
            write(notes_dir / "HAB-2.md", "---\nbookmarks: []\n---\n\n# HAB-2: Two\n")
            vocab_file = notes_dir / "BOOKMARKS.md"
            write(vocab_file, "# Bookmarks\n\n| Bookmark | Meaning |\n|---|---|\n| `ci-flakiness` | x |\n")
            rendered = index.render_index(notes_dir, vocab_file)
            self.assertIn("HAB-1.md", rendered)
            self.assertIn("ci-flakiness", rendered)
            self.assertIn("HAB-2.md", rendered)


class ApplyBookmarksTests(unittest.TestCase):
    def test_inserts_frontmatter_without_touching_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = Path(tmp) / "notes"
            notes_dir.mkdir()
            note = notes_dir / "HAB-1.md"
            write(note, "# HAB-1: Title\n\nOriginal body text.\n")
            outcomes = index.apply_bookmarks(notes_dir, {"HAB-1.md": ["ci-flakiness"]})
            content = note.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---\nbookmarks: [ci-flakiness]\n---\n"))
            self.assertIn("Original body text.", content)
            self.assertEqual(outcomes, {"HAB-1.md": "applied"})

    def test_does_not_overwrite_existing_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = Path(tmp) / "notes"
            notes_dir.mkdir()
            note = notes_dir / "HAB-1.md"
            write(note, "---\nbookmarks: [scope-creep]\n---\n\n# HAB-1: Title\n")
            outcomes = index.apply_bookmarks(notes_dir, {"HAB-1.md": ["ci-flakiness"]})
            content = note.read_text(encoding="utf-8")
            self.assertIn("bookmarks: [scope-creep]", content)
            self.assertEqual(outcomes, {"HAB-1.md": "skipped-already-tagged"})

    def test_missing_file_raises_before_writing_anything(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = Path(tmp) / "notes"
            notes_dir.mkdir()
            note = notes_dir / "HAB-1.md"
            write(note, "# HAB-1: Title\n\nBody.\n")
            with self.assertRaises(ValueError):
                index.apply_bookmarks(
                    notes_dir, {"HAB-1.md": ["ci-flakiness"], "HAB-999-does-not-exist.md": ["ci-flakiness"]}
                )
            # Validation must run before any write — HAB-1.md is untouched.
            self.assertNotIn("bookmarks:", note.read_text(encoding="utf-8"))

    def test_excluded_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = Path(tmp) / "notes"
            notes_dir.mkdir()
            write(notes_dir / "INDEX.md", "generated content\n")
            with self.assertRaises(ValueError):
                index.apply_bookmarks(notes_dir, {"INDEX.md": ["ci-flakiness"]})

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = Path(tmp) / "notes"
            notes_dir.mkdir()
            with self.assertRaises(ValueError):
                index.apply_bookmarks(notes_dir, {"../outside.md": ["ci-flakiness"]})

    def test_unknown_bookmark_against_vocabulary_raises_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = Path(tmp) / "notes"
            notes_dir.mkdir()
            note = notes_dir / "HAB-1.md"
            write(note, "# HAB-1: Title\n\nBody.\n")
            vocab_file = notes_dir / "BOOKMARKS.md"
            write(vocab_file, "# Bookmarks\n\n| Bookmark | Meaning |\n|---|---|\n| `ci-flakiness` | x |\n")
            with self.assertRaises(ValueError):
                index.apply_bookmarks(notes_dir, {"HAB-1.md": ["not-in-vocabulary"]}, vocab_file)
            self.assertNotIn("bookmarks:", note.read_text(encoding="utf-8"))


class MainCliTests(unittest.TestCase):
    def test_apply_bookmarks_mode_is_wired(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = Path(tmp) / "docs" / "knowledge" / "notes"
            notes_dir.mkdir(parents=True)
            note = notes_dir / "HAB-1.md"
            write(note, "# HAB-1: Title\n\nBody.\n")
            vocab_file = notes_dir / "BOOKMARKS.md"
            write(vocab_file, "# Bookmarks\n\n| Bookmark | Meaning |\n|---|---|\n| `ci-flakiness` | x |\n")
            mapping_file = Path(tmp) / "mapping.json"
            mapping_file.write_text(json.dumps({"HAB-1.md": ["ci-flakiness"]}), encoding="utf-8")

            original_notes_dir, original_bookmarks, original_index = (
                index.NOTES_DIR, index.BOOKMARKS_FILE, index.INDEX_FILE,
            )
            try:
                index.NOTES_DIR = notes_dir
                index.BOOKMARKS_FILE = vocab_file
                index.INDEX_FILE = notes_dir / "INDEX.md"
                exit_code = index.main(["--apply-bookmarks", str(mapping_file)])
            finally:
                index.NOTES_DIR, index.BOOKMARKS_FILE, index.INDEX_FILE = (
                    original_notes_dir, original_bookmarks, original_index,
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("bookmarks: [ci-flakiness]", note.read_text(encoding="utf-8"))

    def test_unknown_mode_is_rejected(self):
        self.assertEqual(index.main(["--nonsense"]), 2)


if __name__ == "__main__":
    unittest.main()
