"""Tests for the 6-check campaign proposal evaluator (spec §4.1)."""
import pytest
from framework.campaign_proposal import ProposalCheck, evaluate_proposal


# --- Happy path ---

def test_all_checks_pass():
    check = evaluate_proposal(
        name="Spring Lawn Campaign",
        goal="Replant",
        audience_segment_id="WdpJti",   # Warm — starred
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    assert check.all_pass is True
    assert check.goal_pass is True
    assert check.audience_pass is True
    assert check.cadence_pass is True
    assert check.suppression_pass is True
    assert check.offer_pass is True
    assert check.rpr_pass is True


# --- Rejection cases ---

def test_rejects_missing_goal():
    check = evaluate_proposal(
        name="No goal",
        goal=None,
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    assert check.all_pass is False
    assert check.goal_pass is False


def test_rejects_non_starred_segment():
    check = evaluate_proposal(
        name="Non-starred audience",
        goal="Retention",
        audience_segment_id="XXXZZZ",   # not in starred set
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    assert check.all_pass is False
    assert check.audience_pass is False


def test_rejects_cadence_cap_breach():
    check = evaluate_proposal(
        name="Over-mailed",
        goal="Replant",
        audience_segment_id="WdpJti",
        sends_past_7d=2,   # cap is 2 → 2 >= 2 → breach
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    assert check.all_pass is False
    assert check.cadence_pass is False


def test_rejects_missing_suppression():
    check = evaluate_proposal(
        name="No suppressions",
        goal="Replant",
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=False,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    assert check.all_pass is False
    assert check.suppression_pass is False


def test_rejects_offer_over_cap():
    check = evaluate_proposal(
        name="Too-large discount",
        goal="Replant",
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=0.20,   # 20% > 15% cap
        expected_rpr=0.65,
        target_type="targeted",
    )
    assert check.all_pass is False
    assert check.offer_pass is False


def test_rejects_rpr_below_targeted_minimum():
    check = evaluate_proposal(
        name="Low RPR targeted",
        goal="Replant",
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.40,   # below $0.50 min for targeted
        target_type="targeted",
    )
    assert check.all_pass is False
    assert check.rpr_pass is False


def test_broad_segment_uses_lower_rpr_minimum():
    check = evaluate_proposal(
        name="Broad segment",
        goal="Seasonal moment",
        audience_segment_id="RbH7na",   # E60D — starred
        sends_past_7d=0,
        cadence_cap=3,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.20,   # above $0.15 min for broad
        target_type="broad",
    )
    assert check.all_pass is True
    assert check.rpr_pass is True


# --- Markdown rendering ---

def test_to_markdown_contains_verdict_approved():
    check = evaluate_proposal(
        name="Spring Lawn Campaign",
        goal="Replant",
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    md = check.to_markdown()
    assert "APPROVED" in md
    assert "Spring Lawn Campaign" in md


def test_to_markdown_shows_rejection():
    check = evaluate_proposal(
        name="Bad Campaign",
        goal=None,
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.65,
        target_type="targeted",
    )
    md = check.to_markdown()
    assert "REJECTED" in md
    assert "❌" in md


def test_offer_at_exact_cap_passes():
    """Offer at exactly 15% must pass (spec uses <=)."""
    check = evaluate_proposal(
        name="Exact cap offer",
        goal="Seasonal moment",
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=0.15,
        expected_rpr=0.65,
        target_type="targeted",
    )
    assert check.offer_pass is True
    assert check.all_pass is True


def test_rpr_at_exact_targeted_minimum_passes():
    """RPR at exactly $0.50 must pass for targeted (spec uses >=)."""
    check = evaluate_proposal(
        name="Exact RPR targeted",
        goal="Replant",
        audience_segment_id="WdpJti",
        sends_past_7d=0,
        cadence_cap=2,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.50,
        target_type="targeted",
    )
    assert check.rpr_pass is True


def test_rpr_at_exact_broad_minimum_passes():
    """RPR at exactly $0.15 must pass for broad (spec uses >=)."""
    check = evaluate_proposal(
        name="Exact RPR broad",
        goal="Seasonal moment",
        audience_segment_id="RbH7na",
        sends_past_7d=0,
        cadence_cap=3,
        has_suppression_exclusions=True,
        offer_pct=None,
        expected_rpr=0.15,
        target_type="broad",
    )
    assert check.rpr_pass is True
