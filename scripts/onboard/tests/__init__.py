"""Unit tests for onboarding scripts."""

import unittest
from pathlib import Path

# Tests asserting the shipped template's state (artifact templates, placeholder-bearing files, the sentinel) cannot
# hold once /onboard has run, since `apply` deletes the sentinel; an onboarded repo skips them.
template_only = unittest.skipUnless((Path(__file__).resolve().parents[3] / ".yab-template").exists(),
                                    "template-only: repo is onboarded")
