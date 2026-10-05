"""Unit tests for onboarding scripts."""

import os
import unittest
from pathlib import Path

from scripts.onboard.onboard import YAB_REPO as YAB_REPOSITORY

ROOT = Path(__file__).resolve().parents[3]


def template_state_expected(root=ROOT, env=os.environ):
    """True when tests asserting the shipped template's state must run.

    They cannot hold once /onboard has run (`apply` deletes the sentinel), so an onboarded repo skips them. YAB's own
    CI never skips: a missing sentinel there must fail loudly (SentinelTests), not silence the guarded tests.
    """
    return (root / ".yab-template").exists() or env.get("GITHUB_REPOSITORY", "").lower() == YAB_REPOSITORY


template_only = unittest.skipUnless(template_state_expected(), "template-only: repo is onboarded")
