"""Tests for claims and benchmark audit integrity (B4).

Enforces that numbers in README.md and DEMO_SCRIPT.md strictly match results/summary.csv
and results/calibration.json, and that synthetic datasets are never labeled as Grounded.
"""

from scripts.check_claims import check_claims


class TestClaimsHonesty:
    """Verifies that all repo claims originate from logged benchmark data."""

    def test_claims_match_summary_and_calibration(self):
        """All documented metrics must exactly match results/summary.csv and results/calibration.json."""
        errors = check_claims()
        assert not errors, f"Claims mismatch errors detected:\n" + "\n".join(errors)
