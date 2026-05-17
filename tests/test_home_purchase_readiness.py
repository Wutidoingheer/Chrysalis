"""
Tests for home_purchase_readiness.py

Covers:
  - RSU schedule reconciliation (155 + 462 = 617)
  - Net-value calculations at reference price/withholding combos
  - ESPP monthly drain and per-purchase gain
  - income_summary take-home and free-cash figures
  - rsu_net_by_date cumulative slices
"""

import math
import pytest
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.home_purchase_readiness import (
    _RSU_SCHEDULE_RAW,
    rsu_schedule,
    rsu_net_by_date,
    espp_summary,
    income_summary,
)

# ── Fixtures ───────────────────────────────────────────────────────────────────

REFERENCE_CONFIG = {
    "adbe_price_default":    247,
    "rsu_withholding_default": 0.35,
    "base_salary":           150_000,
    "espp_rate_default":     0.15,
    "espp_discount":         0.15,
    "effective_tax_rate":    0.28,
    "bonus_rate_default":    0.075,
    "bonus_withholding":     0.35,
}


# ── RSU schedule shape ─────────────────────────────────────────────────────────

def test_total_gross_shares_equals_617():
    """155 cliff + 12 quarterly of 38.5 must equal 617."""
    total = sum(row[1] for row in _RSU_SCHEDULE_RAW)
    assert abs(total - 617) < 1e-9, f"Expected 617, got {total}"


def test_cliff_is_first_and_155():
    cliff_date, cliff_gross, cliff_type = _RSU_SCHEDULE_RAW[0]
    assert cliff_date  == "2026-12-15"
    assert cliff_gross == 155.0
    assert "Cliff" in cliff_type


def test_twelve_quarterly_vests():
    quarterly = [row for row in _RSU_SCHEDULE_RAW if row[2] == "Quarterly"]
    assert len(quarterly) == 12


def test_quarterly_shares_total():
    quarterly_total = sum(r[1] for r in _RSU_SCHEDULE_RAW if r[2] == "Quarterly")
    assert abs(quarterly_total - 462.0) < 1e-9


def test_quarterly_vest_dates_span_2027_to_2029():
    quarterly = [r[0] for r in _RSU_SCHEDULE_RAW if r[2] == "Quarterly"]
    assert quarterly[0]  == "2027-03-15"
    assert quarterly[-1] == "2029-12-15"


def test_vest_dates_are_on_the_15th():
    for vest_date, _, _ in _RSU_SCHEDULE_RAW:
        assert vest_date.endswith("-15"), f"{vest_date} is not on the 15th"


# ── Net value calculations at $247 / 35% ──────────────────────────────────────

def test_cliff_net_cash_reference():
    """Dec 2026 cliff: 155 × $247 × 0.65 ≈ $24,888."""
    vests = rsu_schedule(REFERENCE_CONFIG)
    cliff = vests[0]
    expected = 155 * 247 * 0.65
    assert abs(cliff["net_cash"] - expected) < 0.02
    assert abs(cliff["net_cash"] - 24_885.25) < 1.0  # 155 × 247 × 0.65 = 24,885.25 ≈ spec's ~$24,900


def test_cliff_net_shares():
    vests = rsu_schedule(REFERENCE_CONFIG)
    assert abs(vests[0]["net_shares"] - 155 * 0.65) < 0.01


def test_cumulative_through_sep_2027():
    """Cliff + 3 quarterly (Mar/Jun/Sep 2027) ≈ $43,432."""
    vests = rsu_schedule(REFERENCE_CONFIG)
    total = rsu_net_by_date(vests, "2027-09-15")
    assert abs(total - 43_432) < 50, f"Expected ~$43,432, got {total:.2f}"


def test_cumulative_through_dec_2027():
    """Cliff + 4 quarterly (through Dec 2027) ≈ $49,614."""
    vests = rsu_schedule(REFERENCE_CONFIG)
    total = rsu_net_by_date(vests, "2027-12-15")
    assert abs(total - 49_614) < 50, f"Expected ~$49,614, got {total:.2f}"


def test_full_grant_net():
    """617 shares × $247 × 0.65 ≈ $99,059."""
    vests = rsu_schedule(REFERENCE_CONFIG)
    full  = vests[-1]["cumulative_net_cash"]
    expected = 617 * 247 * 0.65
    assert abs(full - expected) < 1.0
    assert abs(full - 99_059) < 100, f"Expected ~$99,059, got {full:.2f}"


def test_net_cash_never_uses_gross():
    """net_cash must always be < gross_shares × price (withholding > 0)."""
    vests = rsu_schedule(REFERENCE_CONFIG)
    price = REFERENCE_CONFIG["adbe_price_default"]
    for v in vests:
        gross_cash = v["gross_shares"] * price
        assert v["net_cash"] < gross_cash, (
            f"net_cash {v['net_cash']} >= gross_cash {gross_cash} for {v['date']}"
        )


def test_cumulative_is_monotonically_increasing():
    vests = rsu_schedule(REFERENCE_CONFIG)
    for i in range(1, len(vests)):
        assert vests[i]["cumulative_net_cash"] > vests[i-1]["cumulative_net_cash"]


def test_rsu_net_by_date_before_any_vest():
    vests = rsu_schedule(REFERENCE_CONFIG)
    assert rsu_net_by_date(vests, "2025-01-01") == 0.0


def test_rsu_net_by_date_cutoff_inclusive():
    """cutoff exactly on a vest date should include that vest."""
    vests = rsu_schedule(REFERENCE_CONFIG)
    total_at_cliff = rsu_net_by_date(vests, "2026-12-15")
    assert abs(total_at_cliff - vests[0]["net_cash"]) < 0.01


# ── Price scenario sensitivity ─────────────────────────────────────────────────

@pytest.mark.parametrize("price,expected_full", [
    (247, 99_059),
    (325, 130_374),
    (400, 160_420),
])
def test_full_grant_at_price_scenarios(price, expected_full):
    cfg = {**REFERENCE_CONFIG, "adbe_price_default": price}
    vests = rsu_schedule(cfg)
    full  = vests[-1]["cumulative_net_cash"]
    # Allow 0.5% tolerance for rounding across 13 vests
    assert abs(full - expected_full) / expected_full < 0.005


def test_price_scenario_spread_is_significant():
    """High − Low full-grant net must exceed $60K (per spec)."""
    low_vests  = rsu_schedule({**REFERENCE_CONFIG, "adbe_price_default": 247})
    high_vests = rsu_schedule({**REFERENCE_CONFIG, "adbe_price_default": 400})
    spread = high_vests[-1]["cumulative_net_cash"] - low_vests[-1]["cumulative_net_cash"]
    assert spread > 60_000, f"Spread {spread:.0f} below expected $60K+"


# ── ESPP ──────────────────────────────────────────────────────────────────────

def test_espp_monthly_drain_at_15pct():
    """$150k × 15% / 12 = $1,875/mo."""
    summary = espp_summary(REFERENCE_CONFIG)
    assert abs(summary["monthly_drain"] - 1_875.0) < 0.01


def test_espp_annual_drain_at_15pct():
    summary = espp_summary(REFERENCE_CONFIG)
    assert abs(summary["annual_drain"] - 22_500.0) < 0.01


def test_espp_gain_per_purchase_15pct_discount():
    """$11,250 invested at 15% discount → gain ≈ $1,985."""
    summary = espp_summary(REFERENCE_CONFIG)
    # contribution per period = $22,500 / 2 = $11,250
    # gain = $11,250 × (0.15 / 0.85) ≈ $1,985.29
    expected = 11_250 * (0.15 / 0.85)
    assert abs(summary["gain_per_purchase"] - expected) < 1.0


def test_espp_annual_gain_approx_4000():
    """Two purchases per year × ~$2,000 each ≈ $4,000."""
    summary = espp_summary(REFERENCE_CONFIG)
    assert abs(summary["annual_gain"] - 4_000) < 200


def test_espp_zero_rate():
    cfg = {**REFERENCE_CONFIG, "espp_rate_default": 0.0}
    summary = espp_summary(cfg)
    assert summary["monthly_drain"] == 0.0
    assert summary["annual_gain"] == 0.0


def test_espp_sensitivity_has_four_entries():
    summary = espp_summary(REFERENCE_CONFIG)
    assert len(summary["sensitivity"]) == 4


def test_espp_sensitivity_drain_decreases_with_rate():
    summary = espp_summary(REFERENCE_CONFIG)
    drains = [s["monthly_drain"] for s in summary["sensitivity"]]
    assert drains == sorted(drains, reverse=True)


# ── Income ────────────────────────────────────────────────────────────────────

def test_gross_monthly_150k():
    s = income_summary(REFERENCE_CONFIG)
    assert abs(s["gross_monthly"] - 12_500.0) < 0.01


def test_takehome_monthly_at_28pct():
    """$12,500 × (1 − 0.28) = $9,000."""
    s = income_summary(REFERENCE_CONFIG)
    assert abs(s["takehome_monthly"] - 9_000.0) < 0.01


def test_free_cash_monthly_with_espp():
    """$9,000 take-home − $1,875 ESPP drain = $7,125."""
    s = income_summary(REFERENCE_CONFIG)
    assert abs(s["free_cash_monthly"] - 7_125.0) < 0.01


def test_net_bonus_at_7p5pct():
    """$150k × 7.5% × (1 − 0.35) = $7,312.50."""
    s = income_summary(REFERENCE_CONFIG)
    expected = 150_000 * 0.075 * 0.65
    assert abs(s["net_annual_bonus"] - expected) < 0.01


def test_utah_note_present():
    s = income_summary(REFERENCE_CONFIG)
    assert "Utah" in s["utah_note"]
