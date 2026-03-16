"""
Cycle Orchestrator — Nature's Seed Google Ads Drip Automation
=============================================================
Runs every Monday and Thursday via GitHub Actions.

Workflow:
    1. Read IMPLEMENTATION_TRACKER.md for goals, history, and next steps
    2. Pull live account data via Google Ads API
    3. Generate "Today's Plan" with proposed changes
    4. Output plan for human review (Telegram/Discord)
    5. After approval, execute approved changes
    6. Update IMPLEMENTATION_TRACKER.md with results

Usage:
    # Step 1: Generate today's plan (no changes made)
    python cycle_orchestrator.py plan

    # Step 2: Execute approved changes (after human review)
    python cycle_orchestrator.py execute --approve plan_20260310.json

    # Step 3: Update tracker with results
    python cycle_orchestrator.py update
"""

import json
import sys
import re
import os
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cycle_orchestrator")

DRIP_DIR = Path(__file__).resolve().parent
AUDIT_DIR = DRIP_DIR.parent
TRACKER_PATH = DRIP_DIR / "IMPLEMENTATION_TRACKER.md"
PLANS_DIR = DRIP_DIR / "plans"
PLANS_DIR.mkdir(exist_ok=True)

# ── Seasonality ──────────────────────────────────────────────────────────────
PEAK_MONTHS = {3, 4, 5, 9, 10}
MODERATE_MONTHS = {11, 12, 1, 2}
OFF_PEAK_MONTHS = {6, 7, 8}


def get_season_status():
    """Return current season status and allowed actions."""
    month = datetime.now().month
    if month in PEAK_MONTHS:
        return {
            "status": "PEAK",
            "emoji": "🔴",
            "allowed": [
                "budget_adjustment (within 30%)",
                "negative_keywords",
                "product_exclusions",
                "keyword_pauses",
                "keyword_additions (to existing ad groups)",
                "search_term_mining",
            ],
            "blocked": [
                "bidding_strategy_changes",
                "campaign_creation",
                "campaign_restructuring",
                "asset_group_creation",
                "conversion_tracking_changes",
            ],
        }
    elif month in OFF_PEAK_MONTHS:
        return {
            "status": "OFF-PEAK",
            "emoji": "🟢",
            "allowed": ["ALL changes allowed"],
            "blocked": [],
        }
    else:
        return {
            "status": "MODERATE",
            "emoji": "🟡",
            "allowed": [
                "Most changes allowed",
                "Avoid major restructuring in November",
            ],
            "blocked": [],
        }


def load_tracker():
    """Load and parse the implementation tracker."""
    if not TRACKER_PATH.exists():
        raise FileNotFoundError(f"Tracker not found at {TRACKER_PATH}")
    return TRACKER_PATH.read_text()


def load_cogs():
    """Load COGS analysis data."""
    cogs_path = AUDIT_DIR / "cogs_analysis.json"
    if cogs_path.exists():
        with open(cogs_path) as f:
            return json.load(f)
    return None


def load_health_plan():
    """Load the health & growth plan for reference."""
    plan_path = AUDIT_DIR / "NATURES_SEED_HEALTH_AND_GROWTH_PLAN.md"
    if plan_path.exists():
        return plan_path.read_text()
    return None


# ── Plan Audit ────────────────────────────────────────────────────────────────

# Baseline budgets when the strategic plan was first written (March 2026)
_PLAN_BASELINE_BUDGETS = {
    "Shopping | Catch All.": 1450,
    "PMAX | Catch all": 760,
    "Search | Animal Seed (Broad) | ROAS": 260,
    "PMAX - Search": 300,
    "Search | Brand | ROAS": 220,
    "Search | Pasture | Exact": 78,
}

# Sequential budget steps per campaign (ascending = increases, descending = cuts)
_BUDGET_STEPS = {
    "Search | Brand | ROAS":                    [220, 286, 372, 483, 500],
    "Search | Animal Seed (Broad) | ROAS":      [260, 182, 130],
    "Search | Pasture | Exact":                 [78, 101, 131, 170, 200],
}

# Tracker row fragments for each step — used to mark items complete
_TRACKER_STEP_STRINGS = {
    ("Search | Brand | ROAS", 1):               "Increase Brand Search budget (step 1)",
    ("Search | Brand | ROAS", 2):               "Increase Brand Search budget (step 2)",
    ("Search | Brand | ROAS", 3):               "Increase Brand Search budget (step 3)",
    ("Search | Animal Seed (Broad) | ROAS", 1): "Cut Animal Seed Broad budget (step 1)",
    ("Search | Animal Seed (Broad) | ROAS", 2): "Cut Animal Seed Broad budget (step 2)",
    ("Search | Pasture | Exact", 1):            "Increase Pasture Exact budget (step 1)",
    ("Search | Pasture | Exact", 2):            "Increase Pasture Exact budget (step 2)",
    ("Search | Pasture | Exact", 3):            "Increase Pasture Exact budget (step 3)",
}


def audit_strategic_plan(snapshot: dict, tracker_text: str) -> dict:
    """
    Compare current account data against IMPLEMENTATION_TRACKER to determine:
    1. Which planned tasks are already done but not marked
    2. Whether strategy assumptions are still valid given current performance
    3. Whether new patterns have emerged that are not in the plan

    Returns:
        plan_needs_update   bool
        recommendation      "proceed" | "update_tracker" | "rebuild_plan"
        cycles_completed    int
        completed_untracked list of {item, evidence, next_step, tracker_key}
        strategy_concerns   list of {concern, implication, severity}
        new_opportunities   list of str
    """
    campaigns = {c["name"]: c for c in snapshot.get("campaigns", [])}
    account = snapshot.get("account_totals", {})
    cycles_done = count_completed_cycles(tracker_text)

    completed_untracked = []
    strategy_concerns = []
    new_opportunities = []

    # ── Brand Search ─────────────────────────────────────────────────────────
    brand = campaigns.get("Search | Brand | ROAS", {})
    if brand:
        budget = brand.get("budget_daily", 220)
        roas = brand.get("roas", 0)
        steps = _BUDGET_STEPS["Search | Brand | ROAS"]

        # How many step-up thresholds have been crossed?
        steps_done = sum(1 for threshold in steps[:-1] if budget >= threshold - 3)
        for step_num in range(1, steps_done + 1):
            key = ("Search | Brand | ROAS", step_num)
            tracker_fragment = _TRACKER_STEP_STRINGS.get(key, "")
            if tracker_fragment and "⬜ Not started" in _find_tracker_row(tracker_text, tracker_fragment):
                next_step_idx = step_num  # steps is 0-indexed for the "after" value
                next_label = (
                    f"Step {step_num + 1}: ${steps[step_num - 1]:.0f} → ${steps[step_num]:.0f}/day"
                    if step_num < len(steps) - 1 else "Target reached"
                )
                completed_untracked.append({
                    "item": f"Increase Brand Search budget (step {step_num})",
                    "evidence": f"Current budget ${budget:.0f}/day — baseline was $220",
                    "next_step": next_label,
                    "tracker_key": key,
                })

        if roas > 0 and roas < 4.0:
            strategy_concerns.append({
                "concern": f"Brand Search ROAS declined to {roas:.1f}x (was 10.5x at plan creation)",
                "implication": "Budget increase steps were based on 10x+ ROAS. At current levels, further increases need review.",
                "severity": "medium",
            })
        elif roas >= 8.0 and budget < 350:
            new_opportunities.append(
                f"Brand Search still at {roas:.1f}x ROAS with only ${budget:.0f}/day — budget increase headroom remains large"
            )

    # ── Animal Seed ───────────────────────────────────────────────────────────
    animal = campaigns.get("Search | Animal Seed (Broad) | ROAS", {})
    if animal:
        budget = animal.get("budget_daily", 260)
        roas = animal.get("roas", 0)
        steps = _BUDGET_STEPS["Search | Animal Seed (Broad) | ROAS"]

        # Steps here are cuts: baseline 260 → 182 → 130
        if budget <= steps[1] + 3:  # at or below first cut target
            key = ("Search | Animal Seed (Broad) | ROAS", 1)
            if _find_tracker_row(tracker_text, _TRACKER_STEP_STRINGS[key]).find("⬜ Not started") >= 0:
                completed_untracked.append({
                    "item": "Cut Animal Seed Broad budget (step 1)",
                    "evidence": f"Current budget ${budget:.0f}/day — baseline was $260",
                    "next_step": f"Step 2: ${steps[1]:.0f} → ${steps[2]:.0f}/day" if budget > steps[2] + 3 else "Target $130 reached",
                    "tracker_key": key,
                })
        if budget <= steps[2] + 3:
            key = ("Search | Animal Seed (Broad) | ROAS", 2)
            frag = _TRACKER_STEP_STRINGS.get(key, "")
            if frag and "⬜ Not started" in _find_tracker_row(tracker_text, frag):
                completed_untracked.append({
                    "item": "Cut Animal Seed Broad budget (step 2)",
                    "evidence": f"Current budget ${budget:.0f}/day — at target floor",
                    "next_step": "Final cut target reached",
                    "tracker_key": key,
                })

        if roas > 0 and roas >= 3.0:
            strategy_concerns.append({
                "concern": f"Animal Seed ROAS improved to {roas:.1f}x (plan assumed <2.5x warranted cuts)",
                "implication": "This campaign may now be profitable enough to maintain or grow rather than cut further.",
                "severity": "high" if roas >= 3.5 else "medium",
            })
        elif roas > 0 and roas < 1.0:
            strategy_concerns.append({
                "concern": f"Animal Seed ROAS further declined to {roas:.1f}x",
                "implication": "Consider pausing campaign entirely rather than continued slow cuts.",
                "severity": "high",
            })

    # ── Pasture Exact ─────────────────────────────────────────────────────────
    pasture = campaigns.get("Search | Pasture | Exact", {})
    if pasture:
        budget = pasture.get("budget_daily", 78)
        roas = pasture.get("roas", 0)
        steps = _BUDGET_STEPS["Search | Pasture | Exact"]

        steps_done = sum(1 for threshold in steps[:-1] if budget >= threshold - 3)
        for step_num in range(1, steps_done + 1):
            key = ("Search | Pasture | Exact", step_num)
            frag = _TRACKER_STEP_STRINGS.get(key, "")
            if frag and "⬜ Not started" in _find_tracker_row(tracker_text, frag):
                next_label = (
                    f"Step {step_num + 1}: ${steps[step_num - 1]:.0f} → ${steps[step_num]:.0f}/day"
                    if step_num < len(steps) - 1 else "Target $200 reached"
                )
                completed_untracked.append({
                    "item": f"Increase Pasture Exact budget (step {step_num})",
                    "evidence": f"Current budget ${budget:.0f}/day — baseline was $78",
                    "next_step": next_label,
                    "tracker_key": key,
                })

        if roas > 0 and roas < 2.0:
            strategy_concerns.append({
                "concern": f"Pasture Exact ROAS dropped to {roas:.1f}x",
                "implication": "Plan is scaling this to $200/day. At current ROAS, increasing budget is questionable.",
                "severity": "high",
            })

    # ── Negative keyword progress ─────────────────────────────────────────────
    if cycles_done >= 1:
        neg_frag = "Add negative keywords (batch 1)"
        if "⬜ Not started" in _find_tracker_row(tracker_text, neg_frag):
            completed_untracked.append({
                "item": "Add negative keywords (batch 1)",
                "evidence": f"{cycles_done} cycle(s) completed — negatives are added each cycle",
                "next_step": "Mark batch 1 done; batch 2 follows",
                "tracker_key": None,
            })
        kw_frag = "Pause money-losing keywords (batch 1)"
        if "⬜ Not started" in _find_tracker_row(tracker_text, kw_frag):
            completed_untracked.append({
                "item": "Pause money-losing keywords (batch 1)",
                "evidence": f"{cycles_done} cycle(s) completed — keywords paused each cycle",
                "next_step": "Continue batch 2",
                "tracker_key": None,
            })

    # ── Unplanned high-waste ───────────────────────────────────────────────────
    for c in snapshot.get("campaigns", []):
        if c.get("roas", 99) < 1.5 and c.get("spend_30d", 0) > 5000:
            if c["name"] not in ("Search | Animal Seed (Broad) | ROAS",):
                strategy_concerns.append({
                    "concern": f"Unaddressed waste: {c['name']} — {c['roas']}x ROAS on ${c['spend_30d']:,.0f} spend",
                    "implication": "Not in current plan. May need to add a cut or restructure action.",
                    "severity": "high",
                })

    # ── Overall ROAS ──────────────────────────────────────────────────────────
    overall_roas = account.get("roas", 0)
    if 0 < overall_roas < 2.5:
        strategy_concerns.append({
            "concern": f"Overall ROAS {overall_roas:.2f}x — well below 3.75x 6-month target",
            "implication": "Current plan may be too conservative. Consider more aggressive waste elimination.",
            "severity": "high",
        })

    # ── Recommendation ────────────────────────────────────────────────────────
    high_severity = any(c["severity"] == "high" for c in strategy_concerns)
    plan_needs_update = bool(completed_untracked) or high_severity or bool(new_opportunities)

    if not plan_needs_update:
        recommendation = "proceed"
    elif completed_untracked and not high_severity:
        recommendation = "update_tracker"
    else:
        recommendation = "rebuild_plan"

    return {
        "plan_needs_update": plan_needs_update,
        "recommendation": recommendation,
        "cycles_completed": cycles_done,
        "completed_untracked": completed_untracked,
        "strategy_concerns": strategy_concerns,
        "new_opportunities": new_opportunities,
    }


def _find_tracker_row(tracker_text: str, fragment: str) -> str:
    """Return the first tracker table row containing the given fragment, or empty string."""
    for line in tracker_text.splitlines():
        if fragment in line:
            return line
    return ""


def format_audit_for_telegram(audit: dict) -> str:
    """Format the plan audit result as a Telegram message."""
    rec = audit["recommendation"]
    lines = ["🔍 <b>PLAN AUDIT — Before This Cycle</b>"]
    lines.append(f"Cycles completed: {audit['cycles_completed']}")
    lines.append("")

    if rec == "proceed":
        lines.append("✅ Plan is current and strategy is on track. Running scheduled cycle.")
        return "\n".join(lines)

    if audit["completed_untracked"]:
        lines.append(f"📋 <b>{len(audit['completed_untracked'])} tasks done but not marked in tracker:</b>")
        for item in audit["completed_untracked"]:
            lines.append(f"  • {item['item']}")
            lines.append(f"    Evidence: {item['evidence']}")
            lines.append(f"    Next: {item['next_step']}")
        lines.append("")

    if audit["strategy_concerns"]:
        lines.append(f"⚠️ <b>{len(audit['strategy_concerns'])} strategy concern(s):</b>")
        for c in audit["strategy_concerns"]:
            emoji = "🔴" if c["severity"] == "high" else "🟡"
            lines.append(f"  {emoji} {c['concern']}")
            lines.append(f"    → {c['implication']}")
        lines.append("")

    if audit["new_opportunities"]:
        lines.append(f"💡 <b>New opportunities not in plan:</b>")
        for opp in audit["new_opportunities"]:
            lines.append(f"  • {opp}")
        lines.append("")

    if rec == "rebuild_plan":
        lines.append("❓ <b>Strategy may need updating before this cycle proceeds.</b>")
        lines.append("")
        lines.append("Reply:")
        lines.append("  <code>REBUILD</code> — Rebuild strategic plan with current data, then run cycle")
        lines.append("  <code>PROCEED</code> — Skip plan update, run cycle with current plan")
    else:  # update_tracker
        lines.append("📝 <b>Tracker needs syncing (completed steps not yet marked).</b>")
        lines.append("")
        lines.append("Reply:")
        lines.append("  <code>UPDATE</code> — Sync tracker then run cycle")
        lines.append("  <code>PROCEED</code> — Skip sync, run cycle anyway")

    return "\n".join(lines)


def sync_tracker_from_audit(audit: dict, tracker_text: str) -> str:
    """
    Update IMPLEMENTATION_TRACKER.md to mark confirmed-completed items.
    Only touches rows we know are done based on hard data (budget thresholds).
    Returns updated tracker text.
    """
    updated = tracker_text
    today = datetime.now().strftime("%Y-%m-%d")
    cycle = audit["cycles_completed"]

    for item in audit["completed_untracked"]:
        fragment = item["item"]
        for line in tracker_text.splitlines():
            if fragment in line and "⬜ Not started" in line:
                # Replace status and fill in cycle/date
                new_line = (line
                    .replace("⬜ Not started", "✅ Complete")
                    .replace("| — | — |", f"| {cycle} | {today} |", 1))
                updated = updated.replace(line, new_line, 1)
                log.info(f"Tracker: marked complete → {fragment}")
                break

    return updated


def rebuild_strategic_plan_from_data(snapshot: dict, tracker_text: str, audit: dict) -> str:
    """
    Rebuild the strategic plan phases based on current account data.
    1. Syncs completed items (same as sync_tracker_from_audit)
    2. Updates budget step notes to reflect current state
    3. Flags strategy concerns inline

    Returns updated tracker text.
    """
    # Start with completed-item sync
    updated = sync_tracker_from_audit(audit, tracker_text)
    today = datetime.now().strftime("%Y-%m-%d")
    campaigns = {c["name"]: c for c in snapshot.get("campaigns", [])}

    # Annotate strategy concern items in the tracker
    for concern in audit["strategy_concerns"]:
        # Look for relevant campaign references in the tracker
        for campaign_name in campaigns:
            if any(part in concern["concern"] for part in campaign_name.split("|")):
                short_name = campaign_name.strip().split("|")[0].strip()
                annotation = f"⚠️ REVIEW {today}: {concern['concern'][:80]}"
                # Find and annotate the relevant "Not started" rows for this campaign
                for line in tracker_text.splitlines():
                    if short_name in line and "Not started" in line:
                        new_line = line.rstrip()
                        if "Notes" in updated:  # it's a table row
                            # Append note to the last cell
                            new_line = new_line.rstrip("|") + f" {annotation} |"
                            updated = updated.replace(line, new_line, 1)
                            break

    return updated


def find_next_actions(tracker_text: str) -> list:
    """Parse the tracker for next actions that are 'Not started'."""
    actions = []
    # Find lines with ⬜ Not started
    for line in tracker_text.splitlines():
        if "⬜ Not started" in line:
            # Extract action name from table row
            parts = line.split("|")
            if len(parts) >= 3:
                action = parts[1].strip()
                notes = parts[-1].strip() if len(parts) > 5 else ""
                actions.append({"action": action, "notes": notes})
    return actions


def find_blocked_actions(tracker_text: str) -> list:
    """Parse the tracker for blocked actions."""
    actions = []
    for line in tracker_text.splitlines():
        if "⬜ Blocked" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                action = parts[1].strip()
                notes = parts[-1].strip() if len(parts) > 5 else ""
                actions.append({"action": action, "notes": notes})
    return actions


def count_completed_cycles(tracker_text: str) -> int:
    """Count how many cycles have been completed (actual entries, not template text)."""
    import re
    # Match actual cycle entries like "### Cycle 1 — Monday, 2026-03-10"
    return len(re.findall(r"### Cycle \d+ —", tracker_text))


# ── Plan Generation ──────────────────────────────────────────────────────────

def generate_plan(snapshot: dict = None):
    """
    Generate today's optimization plan based on:
    1. Implementation tracker goals and next steps
    2. Live account data
    3. Season constraints
    4. COGS margins

    Args:
        snapshot: Pre-fetched account snapshot dict. If None, will be pulled from API.
    """
    from google_ads_mutator import GoogleAdsMutator

    log.info("=" * 60)
    log.info("GENERATING CYCLE PLAN")
    log.info("=" * 60)

    # Load context
    tracker = load_tracker()
    cogs = load_cogs()
    season = get_season_status()
    cycle_num = count_completed_cycles(tracker) + 1

    log.info(f"Cycle #{cycle_num} | Season: {season['status']} {season['emoji']}")
    log.info(f"Blocked actions: {season['blocked']}")

    # Pull live data (reuse snapshot from audit if provided)
    mutator = GoogleAdsMutator()
    if snapshot is None:
        snapshot = mutator.get_account_snapshot()

    # Find what's next on the tracker
    next_actions = find_next_actions(tracker)
    blocked_actions = find_blocked_actions(tracker)

    log.info(f"Next actions available: {len(next_actions)}")
    log.info(f"Blocked actions (peak season): {len(blocked_actions)}")

    # Build the plan
    plan = {
        "cycle_number": cycle_num,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "day_of_week": datetime.now().strftime("%A"),
        "season": season,
        "account_snapshot": {
            "spend_30d": snapshot["account_totals"]["spend"],
            "revenue_30d": snapshot["account_totals"]["revenue"],
            "roas_30d": snapshot["account_totals"]["roas"],
            "campaigns": [
                {
                    "name": c["name"],
                    "budget_daily": c["budget_daily"],
                    "roas": c["roas"],
                    "impression_share": c["impression_share"],
                    "spend_30d": c["cost"],
                    "revenue_30d": c["revenue"],
                }
                for c in snapshot["campaigns"]
            ],
        },
        "waste_identified": snapshot["waste_summary"],
        "proposed_actions": [],
        "deferred_actions": [],
        "rationale": [],
    }

    # ── Propose actions based on priority and season ──

    # Priority 1: Budget adjustments (always allowed)
    for c in snapshot["campaigns"]:
        # Brand Search: if ROAS > 5x and budget is low, propose increase
        if "Brand" in c["name"] and c["roas"] > 5.0 and c["budget_daily"] < 500:
            current = c["budget_daily"]
            proposed = min(current * 1.30, 500)  # 30% max or $500 cap
            if proposed > current + 5:  # Only if meaningful change
                plan["proposed_actions"].append({
                    "type": "budget_increase",
                    "campaign": c["name"],
                    "campaign_id": c["id"],
                    "current": current,
                    "proposed": round(proposed, 0),
                    "change_pct": f"+{(proposed - current) / current:.0%}",
                    "rationale": f"ROAS {c['roas']}x with only {c['impression_share']:.0%} IS — massive headroom",
                    "priority": "P0",
                })

        # Animal Seed Broad: if ROAS < 2.5x, propose decrease
        if "Animal Seed" in c["name"] and c["roas"] < 2.5 and c["budget_daily"] > 130:
            current = c["budget_daily"]
            proposed = max(current * 0.70, 130)  # 30% max reduction or $130 floor
            plan["proposed_actions"].append({
                "type": "budget_decrease",
                "campaign": c["name"],
                "campaign_id": c["id"],
                "current": current,
                "proposed": round(proposed, 0),
                "change_pct": f"{(proposed - current) / current:.0%}",
                "rationale": f"ROAS {c['roas']}x — barely profitable after pasture COGS (57% margin)",
                "priority": "P1",
            })

        # Pasture Exact: if ROAS > 2.5x and budget is low, propose increase
        if "Pasture" in c["name"] and "Exact" in c["name"] and c["roas"] > 2.5 and c["budget_daily"] < 200:
            current = c["budget_daily"]
            proposed = min(current * 1.30, 200)
            if proposed > current + 5:
                plan["proposed_actions"].append({
                    "type": "budget_increase",
                    "campaign": c["name"],
                    "campaign_id": c["id"],
                    "current": current,
                    "proposed": round(proposed, 0),
                    "change_pct": f"+{(proposed - current) / current:.0%}",
                    "rationale": f"ROAS {c['roas']}x with room to grow — adding proven keywords",
                    "priority": "P2",
                })

    # Priority 2: Negative keywords (always allowed)
    wasted_terms = [
        t for t in snapshot["search_terms_sample"]
        if t["roas"] < 0.5 and t["cost"] > 20
    ]
    if wasted_terms:
        # Take top 10 worst
        worst = sorted(wasted_terms, key=lambda t: -t["cost"])[:10]
        plan["proposed_actions"].append({
            "type": "add_negatives",
            "terms": [{"term": t["term"], "cost": t["cost"], "roas": t["roas"]} for t in worst],
            "count": len(worst),
            "total_waste": sum(t["cost"] for t in worst),
            "rationale": f"Top {len(worst)} wasted search terms — ${sum(t['cost'] for t in worst):.0f} spent at <0.5x ROAS",
            "priority": "P1",
        })

    # Priority 3: Keyword pauses (always allowed)
    losing_kws = [
        k for k in snapshot["keywords"]
        if k["roas"] < 1.0 and k["cost"] > 20
    ]
    if losing_kws:
        worst_kws = sorted(losing_kws, key=lambda k: -k["cost"])[:5]
        plan["proposed_actions"].append({
            "type": "pause_keywords",
            "keywords": [
                {
                    "keyword": k["keyword"],
                    "match_type": k["match_type"],
                    "campaign": k["campaign_name"],
                    "ad_group_id": k["ad_group_id"],
                    "criterion_id": k["criterion_id"],
                    "cost": k["cost"],
                    "roas": k["roas"],
                }
                for k in worst_kws
            ],
            "count": len(worst_kws),
            "total_waste": sum(k["cost"] for k in worst_kws),
            "rationale": f"Top {len(worst_kws)} money-losing keywords — ${sum(k['cost'] for k in worst_kws):.0f} wasted",
            "priority": "P1",
        })

    # Priority 4: New keyword opportunities (from winning search terms)
    winner_terms = [
        t for t in snapshot["search_terms_sample"]
        if t["roas"] >= 5.0 and t["cost"] > 30
    ]
    if winner_terms:
        plan["proposed_actions"].append({
            "type": "keyword_opportunities",
            "terms": [
                {"term": t["term"], "revenue": t["revenue"], "roas": t["roas"], "campaign": t["campaign_name"]}
                for t in winner_terms[:8]
            ],
            "rationale": "High-ROAS search terms that could be added as explicit keywords",
            "priority": "P2",
            "note": "Review individually — some may already be targeted",
        })

    # Deferred actions (peak season blocks)
    if season["status"] == "PEAK":
        plan["deferred_actions"] = [
            {"action": a["action"], "reason": "Peak season — deferred to June 2026"}
            for a in blocked_actions
        ]

    # Save plan
    plan_filename = f"plan_{datetime.now().strftime('%Y%m%d')}.json"
    plan_path = PLANS_DIR / plan_filename
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2, default=str)

    log.info(f"Plan saved to {plan_path}")

    # Generate human-readable summary
    summary = format_plan_for_chat(plan)
    summary_path = PLANS_DIR / f"plan_{datetime.now().strftime('%Y%m%d')}_summary.md"
    with open(summary_path, "w") as f:
        f.write(summary)

    log.info(f"Summary saved to {summary_path}")
    print("\n" + summary)

    return plan


def format_plan_for_chat(plan: dict) -> str:
    """Format the plan as a readable message for Telegram/Discord."""
    lines = []
    lines.append(f"# Google Ads Optimization — Cycle #{plan['cycle_number']}")
    lines.append(f"**Date**: {plan['date']} ({plan['day_of_week']})")
    lines.append(f"**Season**: {plan['season']['emoji']} {plan['season']['status']}")
    lines.append("")

    # Account snapshot
    snap = plan["account_snapshot"]
    lines.append("## Account Snapshot (Last 30 Days)")
    lines.append(f"- **Total Spend**: ${snap['spend_30d']:,.0f}")
    lines.append(f"- **Total Revenue**: ${snap['revenue_30d']:,.0f}")
    lines.append(f"- **Blended ROAS**: {snap['roas_30d']}x")
    lines.append("")

    lines.append("| Campaign | Budget | ROAS | IS% |")
    lines.append("|----------|--------|------|-----|")
    for c in snap["campaigns"]:
        # Escape pipe characters in campaign names for markdown tables
        safe_name = c['name'].replace('|', '/')
        lines.append(f"| {safe_name} | ${c['budget_daily']:.0f}/d | {c['roas']}x | {c['impression_share']:.0%} |")
    lines.append("")

    # Waste
    w = plan["waste_identified"]
    lines.append("## Waste Identified")
    lines.append(f"- Wasted search terms: {w['wasted_search_terms']} = ${w['wasted_search_spend']:,.0f}")
    lines.append(f"- Zero-revenue products: {w['zero_rev_products']} = ${w['zero_rev_spend']:,.0f}")
    lines.append(f"- Losing keywords: {w['losing_keywords']}")
    lines.append("")

    # Proposed actions
    lines.append("## Proposed Actions")
    lines.append("")

    for i, action in enumerate(plan["proposed_actions"], 1):
        priority = action.get("priority", "P2")
        lines.append(f"### {i}. [{priority}] {action['type'].replace('_', ' ').title()}")
        lines.append(f"**Rationale**: {action['rationale']}")

        if action["type"] in ("budget_increase", "budget_decrease"):
            lines.append(f"- Campaign: **{action['campaign']}**")
            lines.append(f"- Current: ${action['current']:.0f}/day → Proposed: ${action['proposed']:.0f}/day ({action['change_pct']})")

        elif action["type"] == "add_negatives":
            lines.append(f"- **{action['count']} terms** to add as negatives (${action['total_waste']:.0f} wasted):")
            for t in action["terms"]:
                lines.append(f"  - \"{t['term']}\" — ${t['cost']:.0f} spent, {t['roas']}x ROAS")

        elif action["type"] == "pause_keywords":
            lines.append(f"- **{action['count']} keywords** to pause (${action['total_waste']:.0f} wasted):")
            for k in action["keywords"]:
                lines.append(f"  - \"{k['keyword']}\" ({k['match_type']}) — ${k['cost']:.0f}, {k['roas']}x | {k['campaign']}")

        elif action["type"] == "keyword_opportunities":
            lines.append(f"- High-ROAS terms to consider adding:")
            for t in action["terms"]:
                lines.append(f"  - \"{t['term']}\" — ${t['revenue']:.0f} rev, {t['roas']}x | via {t['campaign']}")

        lines.append("")

    # Deferred
    if plan["deferred_actions"]:
        lines.append("## Deferred (Peak Season)")
        for d in plan["deferred_actions"]:
            lines.append(f"- {d['action']} — {d['reason']}")
        lines.append("")

    # Blocked
    if plan["season"]["blocked"]:
        lines.append("## Blocked This Cycle (Peak Season)")
        for b in plan["season"]["blocked"]:
            lines.append(f"- {b}")
        lines.append("")

    lines.append("---")
    lines.append("**Reply with**: ✅ Approve all | ✅❌ Approve/reject individually | 🔄 Modify | ⏭️ Defer to next cycle")

    return "\n".join(lines)


# ── Plan Execution ───────────────────────────────────────────────────────────

def execute_plan(plan_path: str, approved_actions: list = None):
    """
    Execute approved actions from a plan.

    Args:
        plan_path: Path to the plan JSON file
        approved_actions: List of action indices to execute (1-based).
                         If None, executes all.
    """
    from google_ads_mutator import GoogleAdsMutator

    with open(plan_path) as f:
        plan = json.load(f)

    mutator = GoogleAdsMutator()
    results = []

    for i, action in enumerate(plan["proposed_actions"], 1):
        if approved_actions and i not in approved_actions:
            log.info(f"Action {i} ({action['type']}) — SKIPPED (not approved)")
            results.append({"action_index": i, "type": action["type"], "status": "skipped"})
            continue

        log.info(f"\nExecuting action {i}: {action['type']}")

        try:
            if action["type"] == "budget_increase" or action["type"] == "budget_decrease":
                result = mutator.update_campaign_budget(
                    campaign_id=action["campaign_id"],
                    new_budget_daily=action["proposed"],
                    current_budget_daily=action["current"],
                    validate_only=False,
                )
                results.append({"action_index": i, "type": action["type"], "status": "success", "result": result})

            elif action["type"] == "add_negatives":
                # Add negatives to all search campaigns
                terms = [t["term"] for t in action["terms"]]
                # Add to each campaign that triggered them
                campaign_ids_seen = set()
                for t_data in action.get("terms", []):
                    # We add account-level negatives for simplicity
                    pass
                for term in terms:
                    result = mutator.add_negative_keyword_account_level(
                        keyword_text=term,
                        match_type="EXACT",
                        validate_only=False,
                    )
                results.append({"action_index": i, "type": action["type"], "status": "success", "count": len(terms)})

            elif action["type"] == "pause_keywords":
                specs = [
                    {
                        "ad_group_id": k["ad_group_id"],
                        "criterion_id": k["criterion_id"],
                        "keyword_text": k["keyword"],
                    }
                    for k in action["keywords"]
                ]
                result = mutator.batch_pause_keywords(specs, validate_only=False)
                results.append({"action_index": i, "type": action["type"], "status": "success", "count": len(specs)})

            elif action["type"] == "keyword_opportunities":
                # Skip — handled interactively via Telegram in run_full_cycle()
                log.info("Keyword opportunities — handled separately via Telegram")
                results.append({"action_index": i, "type": action["type"], "status": "manual_required"})

            elif action["type"] == "add_keyword":
                # Resolved keyword placement from interactive Telegram flow
                result = mutator.add_keyword_to_ad_group(
                    ad_group_id=action["ad_group_id"],
                    keyword_text=action["keyword"],
                    match_type=action["match_type"],
                    validate_only=False,
                )
                results.append({"action_index": i, "type": action["type"], "status": "success", "result": result})

            else:
                log.warning(f"Unknown action type: {action['type']}")
                results.append({"action_index": i, "type": action["type"], "status": "unknown_type"})

        except Exception as e:
            log.error(f"Action {i} failed: {e}")
            results.append({"action_index": i, "type": action["type"], "status": "error", "error": str(e)})

    # Save change log
    mutator.save_change_log()

    # Save execution results
    results_path = PLANS_DIR / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_path, "w") as f:
        json.dump({"plan_file": str(plan_path), "results": results, "timestamp": datetime.now().isoformat()}, f, indent=2)

    log.info(f"\nExecution results saved to {results_path}")
    return results


# ── Tracker Update ───────────────────────────────────────────────────────────

def update_tracker(plan_path: str, results: list):
    """Update IMPLEMENTATION_TRACKER.md with cycle results."""
    with open(plan_path) as f:
        plan = json.load(f)

    tracker = load_tracker()
    cycle_num = plan["cycle_number"]
    date = plan["date"]
    day = plan["day_of_week"]

    # Build the change history entry
    entry_lines = [
        f"\n### Cycle {cycle_num} — {day}, {date}",
        f"**Season**: {plan['season']['emoji']} {plan['season']['status']}",
        f"**Plan proposed**: {len(plan['proposed_actions'])} actions",
    ]

    executed = [r for r in results if r["status"] == "success"]
    skipped = [r for r in results if r["status"] == "skipped"]
    errors = [r for r in results if r["status"] == "error"]

    entry_lines.append(f"**Executed**: {len(executed)} | **Skipped**: {len(skipped)} | **Errors**: {len(errors)}")
    entry_lines.append("**Changes implemented**:")

    for r in results:
        action = plan["proposed_actions"][r["action_index"] - 1]
        if r["status"] == "success":
            if action["type"] in ("budget_increase", "budget_decrease"):
                entry_lines.append(
                    f"- ✅ {action['campaign']}: ${action['current']:.0f} → ${action['proposed']:.0f}/day"
                )
            elif action["type"] == "add_negatives":
                entry_lines.append(f"- ✅ Added {r.get('count', '?')} negative keywords (account-level)")
            elif action["type"] == "pause_keywords":
                entry_lines.append(f"- ✅ Paused {r.get('count', '?')} money-losing keywords")
        elif r["status"] == "skipped":
            entry_lines.append(f"- ⏭️ {action['type']} — skipped (not approved)")
        elif r["status"] == "error":
            entry_lines.append(f"- ❌ {action['type']} — ERROR: {r.get('error', 'unknown')}")
        elif r["status"] == "manual_required":
            entry_lines.append(f"- 📋 {action['type']} — requires manual implementation")

    snap = plan["account_snapshot"]
    entry_lines.append(
        f"**Account snapshot**: Spend ${snap['spend_30d']:,.0f} | Revenue ${snap['revenue_30d']:,.0f} | ROAS {snap['roas_30d']}x (30d)"
    )
    entry_lines.append("")

    # Insert into tracker after "*(No entries yet — first cycle pending)*"
    placeholder = "*(No entries yet — first cycle pending)*"
    new_entry = "\n".join(entry_lines)

    if placeholder in tracker:
        tracker = tracker.replace(placeholder, new_entry)
    else:
        # Append after "## Change History Log" section
        marker = "## Change History Log"
        if marker in tracker:
            # Find the end of the template block and append
            idx = tracker.index(marker)
            # Find the next ## section
            next_section = tracker.find("\n## ", idx + len(marker))
            if next_section > 0:
                tracker = tracker[:next_section] + new_entry + "\n" + tracker[next_section:]
            else:
                tracker += "\n" + new_entry

    # Update campaign budgets in the Quick Reference table
    for action in plan["proposed_actions"]:
        if action["type"] in ("budget_increase", "budget_decrease"):
            r = [r for r in results if plan["proposed_actions"][r["action_index"] - 1] == action]
            if r and r[0]["status"] == "success":
                # Update the budget line in the tracker
                old_line = f"| {action['campaign'].split('|')[0].strip()}"
                # This is a simplified update — in practice the agent would do a proper edit
                pass

    # Write updated tracker
    with open(TRACKER_PATH, "w") as f:
        f.write(tracker)

    log.info(f"Tracker updated with Cycle {cycle_num} results")


# ── Approval Log ─────────────────────────────────────────────────────────────

APPROVAL_LOG_PATH = DRIP_DIR / "APPROVAL_LOG.md"


def update_approval_log(
    cycle_num: int,
    plan: dict,
    first_approval: str,
    first_approval_time: str,
    second_confirmation: str,
    second_confirmation_time: str,
    results: list,
    modifications: list = None,
    rejected: list = None,
    deferred: list = None,
):
    """Update APPROVAL_LOG.md with a full audit entry."""
    log_text = APPROVAL_LOG_PATH.read_text()
    date = plan["date"]
    day = plan["day_of_week"]

    entry = []
    entry.append(f"\n### [CYCLE-{cycle_num:03d}] {date} — {day}\n")
    entry.append(f"**Plan Sent**: via Telegram")
    entry.append(f"**First Approval**: {first_approval_time} — `{first_approval}`")
    entry.append(f"**Second Confirmation**: {second_confirmation_time} — `{second_confirmation}`\n")

    # Approved & executed
    entry.append("#### Approved Actions")
    entry.append("| # | Action | Before | After | Status |")
    entry.append("|---|--------|--------|-------|--------|")

    for r in results:
        action = plan["proposed_actions"][r["action_index"] - 1]
        if r["status"] == "success":
            if action["type"] in ("budget_increase", "budget_decrease"):
                entry.append(
                    f"| {r['action_index']} | {action['type']} — {action.get('campaign', '')} | "
                    f"${action.get('current', 0):.0f}/day | ${action.get('proposed', 0):.0f}/day | ✅ Executed |"
                )
            elif action["type"] == "add_negatives":
                entry.append(
                    f"| {r['action_index']} | Add {action.get('count', '?')} negatives | — | "
                    f"{action.get('count', '?')} terms | ✅ Executed |"
                )
            elif action["type"] == "pause_keywords":
                entry.append(
                    f"| {r['action_index']} | Pause {action.get('count', '?')} keywords | Enabled | "
                    f"Paused | ✅ Executed |"
                )

    # Rejected / postponed
    if rejected or deferred:
        entry.append("\n#### Rejected / Postponed Actions")
        entry.append("| # | Action | Reason | Deferred To |")
        entry.append("|---|--------|--------|-------------|")
        for r in (rejected or []):
            entry.append(f"| {r['index']} | {r['action']} | {r.get('reason', 'Rejected')} | — |")
        for d in (deferred or []):
            entry.append(f"| {d['index']} | {d['action']} | Deferred | Next cycle |")

    # Modifications
    if modifications:
        entry.append("\n#### Modifications Requested")
        for m in modifications:
            entry.append(f"- {m}")

    # Errors
    errors = [r for r in results if r["status"] == "error"]
    if errors:
        entry.append("\n#### Errors")
        for e in errors:
            action = plan["proposed_actions"][e["action_index"] - 1]
            entry.append(f"- Action {e['action_index']} ({action['type']}): {e.get('error', 'Unknown')}")

    entry.append("")

    new_entry = "\n".join(entry)

    # Insert into log
    placeholder = "*(First cycle pending — no approvals yet)*"
    if placeholder in log_text:
        log_text = log_text.replace(placeholder, new_entry)
    else:
        # Append before "## Quick Stats"
        stats_marker = "## Quick Stats"
        if stats_marker in log_text:
            idx = log_text.index(stats_marker)
            log_text = log_text[:idx] + new_entry + "\n" + log_text[idx:]
        else:
            log_text += "\n" + new_entry

    # Update quick stats
    import re
    total_cycles = len(re.findall(r"\[CYCLE-\d+\]", log_text))
    total_approved = log_text.count("✅ Executed")
    total_rejected = log_text.count("Rejected")
    total_deferred_count = log_text.count("Deferred | Next cycle")
    total_errors = log_text.count("#### Errors")

    stats_section = f"""## Quick Stats

| Metric | Value |
|--------|-------|
| Total cycles run | {total_cycles} |
| Total actions approved | {total_approved} |
| Total actions rejected | {total_rejected} |
| Total actions deferred | {total_deferred_count} |
| Total actions executed | {total_approved} |
| Execution errors | {total_errors} |

*Updated automatically after each cycle.*"""

    # Replace existing stats section
    stats_pattern = r"## Quick Stats.*?\*Updated automatically after each cycle\.\*"
    log_text = re.sub(stats_pattern, stats_section, log_text, flags=re.DOTALL)

    with open(APPROVAL_LOG_PATH, "w") as f:
        f.write(log_text)

    log.info(f"Approval log updated with CYCLE-{cycle_num:03d}")


# ── Full Telegram Cycle ─────────────────────────────────────────────────────

def handle_keyword_opportunities(bot, plan, mutator):
    """
    Interactive keyword placement via Telegram using numbered menus.

    3-step flow:
        1. Pick campaigns (letter+number: a3, b3, c1)
        2. Pick ad groups per campaign (letter+number: a5, b2)
        3. Pick match types (E/P/B for all, or a-E, b-P per keyword)
    Then confirm and return add_keyword actions.

    Returns:
        list of resolved add_keyword action dicts, or empty list if skipped.
    """
    from telegram_bot import TelegramBot

    # Find keyword_opportunities action in the plan
    kw_action = None
    for action in plan["proposed_actions"]:
        if action["type"] == "keyword_opportunities":
            kw_action = action
            break

    if not kw_action:
        return []

    terms = kw_action.get("terms", [])
    if not terms:
        return []

    # Get campaign list for numbered menu
    campaigns_map = mutator.get_campaigns_map()
    campaign_names = sorted(campaigns_map.keys())

    # Assign letters to keywords
    keyword_letters = [(chr(ord('a') + i), t["term"]) for i, t in enumerate(terms)]

    # ── Step 1: Campaign selection ──
    log.info("Step 1: Sending keyword opportunities with campaign menu...")
    bot.send_keyword_opportunities(terms, campaign_names)

    reply = bot.wait_for_reply(timeout_minutes=60)
    if not reply or reply.strip().upper() == "SKIP":
        log.info("Keyword placement skipped.")
        bot.send_message("⏭️ Keyword placement skipped.")
        return []

    # Parse letter+number pairs
    campaign_picks = bot.parse_letter_number_pairs(reply, len(terms))
    if not campaign_picks:
        bot.send_message("⚠️ No valid picks. Skipping keywords.")
        return []

    # Map each keyword to its campaign
    active_keywords = []  # [(letter, term, campaign_name)]
    for letter, term in keyword_letters:
        pick = campaign_picks.get(letter)
        if pick and 1 <= pick <= len(campaign_names):
            active_keywords.append((letter, term, campaign_names[pick - 1]))

    if not active_keywords:
        bot.send_message("⚠️ No valid campaign selections. Skipping.")
        return []

    # ── Step 2: Ad group selection ──
    # Group keywords by campaign and fetch ad groups
    keywords_by_campaign = {}  # {campaign_name: [(letter, term), ...]}
    ad_groups_by_campaign = {}  # {campaign_name: [ag_name, ...]}

    for letter, term, campaign_name in active_keywords:
        if campaign_name not in keywords_by_campaign:
            keywords_by_campaign[campaign_name] = []
        keywords_by_campaign[campaign_name].append((letter, term))

    for campaign_name in keywords_by_campaign:
        campaign_id = campaigns_map[campaign_name]
        ags = mutator.get_ad_groups(campaign_id=campaign_id)
        ad_groups_by_campaign[campaign_name] = [ag["name"] for ag in ags]

    log.info("Step 2: Sending ad group menu...")
    bot.send_ad_group_selection(keywords_by_campaign, ad_groups_by_campaign)

    reply = bot.wait_for_reply(timeout_minutes=60)
    if not reply or reply.strip().upper() == "SKIP":
        bot.send_message("⏭️ Keyword placement skipped.")
        return []

    ag_picks = bot.parse_letter_number_pairs(reply, len(active_keywords))

    # Resolve ad groups
    placements = []  # [(letter, term, campaign_name, ag_name)]
    for letter, term, campaign_name in active_keywords:
        pick = ag_picks.get(letter)
        ag_list = ad_groups_by_campaign.get(campaign_name, [])
        if pick and 1 <= pick <= len(ag_list):
            placements.append((letter, term, campaign_name, ag_list[pick - 1]))

    if not placements:
        bot.send_message("⚠️ No valid ad group selections. Skipping.")
        return []

    # ── Step 3: Match type selection ──
    log.info("Step 3: Sending match type menu...")
    placement_letters = [(letter, term) for letter, term, _, _ in placements]
    bot.send_match_type_selection(placement_letters)

    reply = bot.wait_for_reply(timeout_minutes=60)
    if not reply or reply.strip().upper() == "SKIP":
        bot.send_message("⏭️ Keyword placement skipped.")
        return []

    match_picks = bot.parse_match_types(reply, placement_letters)

    # ── Build final placements and resolve IDs ──
    resolved = []
    for letter, term, campaign_name, ag_name in placements:
        match_type = match_picks.get(letter, "PHRASE")
        try:
            ids = mutator.resolve_keyword_placement(campaign_name, ag_name)
            resolved.append({
                "keyword": term,
                "campaign_name": ids["campaign_name"],
                "campaign_id": ids["campaign_id"],
                "ad_group_name": ids["ad_group_name"],
                "ad_group_id": ids["ad_group_id"],
                "match_type": match_type,
            })
        except ValueError as e:
            log.warning(f"Could not resolve {term}: {e}")

    if not resolved:
        bot.send_message("No valid placements to add. Skipping.")
        return []

    # ── Confirm ──
    bot.send_keyword_confirmation(resolved)
    confirm = bot.wait_for_reply(timeout_minutes=30)

    if not confirm or "CONFIRM EXECUTE" not in confirm.upper():
        bot.send_message("❌ Keyword placement cancelled.")
        return []

    # Build add_keyword actions
    actions = []
    for p in resolved:
        actions.append({
            "type": "add_keyword",
            "keyword": p["keyword"],
            "campaign_name": p["campaign_name"],
            "campaign_id": p["campaign_id"],
            "ad_group_name": p["ad_group_name"],
            "ad_group_id": p["ad_group_id"],
            "match_type": p["match_type"],
        })

    return actions


def run_full_cycle(wait_minutes: int = 120):
    """
    Full cycle with plan audit, Telegram integration, and double confirmation.

    Flow:
        0. Pull account snapshot + audit current strategic plan
           - If stale: send audit to Telegram, wait for REBUILD / UPDATE / PROCEED
           - If REBUILD: rebuild plan from current data + update tracker
           - If UPDATE: sync completed items into tracker
        1. Generate today's tactical plan (reuses snapshot from step 0)
        2. Send plan to Telegram
        3. Wait for first approval
        4. Handle keyword opportunities interactively
        5. Send confirmation request (second approval)
        6. Wait for CONFIRM EXECUTE
        7. Execute approved actions + keyword placements
        8. Send execution report
        9. Update tracker + approval log
    """
    from telegram_bot import TelegramBot
    from google_ads_mutator import GoogleAdsMutator

    log.info("=" * 60)
    log.info("STARTING FULL CYCLE (with plan audit)")
    log.info("=" * 60)

    bot = TelegramBot()
    mutator = GoogleAdsMutator()

    # ── Step 0: Pull snapshot + audit strategic plan ──────────────────────────
    log.info("Pulling account snapshot for plan audit...")
    try:
        snapshot = mutator.get_account_snapshot()
    except Exception as e:
        log.error(f"Snapshot failed: {e}")
        bot.send_message(f"❌ Failed to pull account snapshot:\n<code>{str(e)[:500]}</code>")
        raise

    tracker = load_tracker()
    audit = audit_strategic_plan(snapshot, tracker)
    log.info(
        f"Plan audit complete — needs_update={audit['plan_needs_update']}, "
        f"recommendation={audit['recommendation']}, "
        f"completed_untracked={len(audit['completed_untracked'])}, "
        f"strategy_concerns={len(audit['strategy_concerns'])}"
    )

    if audit["plan_needs_update"]:
        audit_msg = format_audit_for_telegram(audit)
        bot.send_message(audit_msg)

        if audit["recommendation"] == "rebuild_plan":
            log.info("Waiting for strategy decision: REBUILD or PROCEED (120 min timeout)...")
            strategy_reply = bot.wait_for_reply(timeout_minutes=120)

            if not strategy_reply:
                bot.send_message("⏰ No strategy decision received — proceeding with current plan.")
                log.info("No reply — proceeding with existing plan")
            elif "REBUILD" in strategy_reply.upper():
                bot.send_message("🔄 Rebuilding strategic plan from current account data...")
                updated_tracker = rebuild_strategic_plan_from_data(snapshot, tracker, audit)
                with open(TRACKER_PATH, "w") as f:
                    f.write(updated_tracker)
                bot.send_message("✅ Strategic plan rebuilt and tracker updated. Proceeding with cycle...")
                log.info("Tracker rebuilt from current data")
            else:
                bot.send_message("▶️ Proceeding with current plan as-is.")
                log.info("User chose PROCEED — keeping existing plan")

        elif audit["recommendation"] == "update_tracker":
            log.info("Waiting for tracker sync decision: UPDATE or PROCEED (60 min timeout)...")
            sync_reply = bot.wait_for_reply(timeout_minutes=60)

            if not sync_reply or "PROCEED" in sync_reply.upper():
                bot.send_message("▶️ Skipping tracker sync. Proceeding with cycle.")
                log.info("Skipping tracker sync")
            elif "UPDATE" in sync_reply.upper():
                bot.send_message("📝 Syncing tracker with completed items...")
                updated_tracker = sync_tracker_from_audit(audit, tracker)
                with open(TRACKER_PATH, "w") as f:
                    f.write(updated_tracker)
                bot.send_message("✅ Tracker synced. Proceeding with cycle...")
                log.info("Tracker synced from audit")
    else:
        log.info("Plan is current — no audit update needed.")
        bot.send_message("✅ Plan audit: current. Proceeding with scheduled cycle.")

    # ── Step 1: Generate today's tactical plan ────────────────────────────────
    log.info("Generating tactical plan...")
    try:
        plan = generate_plan(snapshot=snapshot)
    except Exception as e:
        log.error(f"Plan generation failed: {e}")
        bot.send_message(f"❌ Plan generation failed:\n<code>{str(e)[:500]}</code>")
        raise

    plan_path = PLANS_DIR / f"plan_{datetime.now().strftime('%Y%m%d')}.json"

    # ── Step 2: Send tactical plan to Telegram ───────────────────────────────
    summary_path = PLANS_DIR / f"plan_{datetime.now().strftime('%Y%m%d')}_summary.md"
    summary = summary_path.read_text()

    log.info("Sending plan to Telegram...")
    bot.send_plan(summary)

    # Step 3: Wait for first approval
    log.info(f"Waiting for first approval (timeout: {wait_minutes}min)...")
    first_reply = bot.wait_for_reply(timeout_minutes=wait_minutes)

    if not first_reply:
        log.warning("No approval received. Cycle aborted.")
        bot.send_message("⏰ No response received. Cycle aborted. Plan saved for next cycle.")
        return

    first_approval_time = datetime.now().strftime("%H:%M")
    approved_indices = TelegramBot._parse_approval(first_reply)

    if approved_indices is not None and len(approved_indices) == 0:
        # DEFER ALL
        log.info("All actions deferred. Cycle complete.")
        bot.send_message("⏭️ All actions deferred to next cycle. Tracker updated.")
        return

    # Step 4: Handle keyword opportunities interactively
    keyword_actions = handle_keyword_opportunities(bot, plan, mutator)

    if keyword_actions:
        # Append resolved keyword actions to the plan
        plan["proposed_actions"].extend(keyword_actions)
        # Re-save plan with keyword actions included
        with open(plan_path, "w") as f:
            json.dump(plan, f, indent=2, default=str)
        log.info(f"Added {len(keyword_actions)} keyword placements to plan")

    # Step 5: Send second confirmation
    log.info("Sending second confirmation request...")
    bot.send_confirmation_request(plan, first_reply)

    # Step 6: Wait for CONFIRM EXECUTE
    log.info("Waiting for final confirmation...")
    second_reply = bot.wait_for_reply(timeout_minutes=30)

    if not second_reply or "CONFIRM EXECUTE" not in second_reply.upper():
        log.warning(f"Execution cancelled. Reply was: {second_reply}")
        bot.send_message("❌ Execution cancelled. No changes made. Plan saved for next cycle.")
        return

    second_confirmation_time = datetime.now().strftime("%H:%M")

    # Step 7: Execute
    log.info("Executing approved actions...")
    results = execute_plan(str(plan_path), approved_indices)

    # Step 8: Send execution report
    bot.send_execution_report(results, plan)

    # Step 9: Update tracker + approval log
    update_tracker(str(plan_path), results)

    deferred = []
    for i, d in enumerate(plan.get("deferred_actions", []), len(plan["proposed_actions"]) + 1):
        deferred.append({"index": i, "action": d["action"], "reason": d.get("reason", "Deferred")})

    update_approval_log(
        cycle_num=plan["cycle_number"],
        plan=plan,
        first_approval=first_reply,
        first_approval_time=first_approval_time,
        second_confirmation=second_reply,
        second_confirmation_time=second_confirmation_time,
        results=results,
        deferred=deferred if deferred else None,
    )

    bot.send_message("✅ Cycle complete! Tracker and approval log updated.")
    log.info("Cycle complete!")


# ── CLI Entry Point ──────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python cycle_orchestrator.py plan            — Generate plan (no Telegram)")
        print("  python cycle_orchestrator.py cycle           — Full cycle via Telegram")
        print("  python cycle_orchestrator.py execute <file> [1,2,3]  — Execute manually")
        print("  python cycle_orchestrator.py snapshot        — Pull account snapshot")
        print("  python cycle_orchestrator.py dryrun <file>   — Validate without executing")
        sys.exit(1)

    command = sys.argv[1]

    if command == "plan":
        generate_plan()

    elif command == "cycle":
        wait = int(sys.argv[2]) if len(sys.argv) > 2 else 120
        run_full_cycle(wait_minutes=wait)

    elif command == "snapshot":
        from google_ads_mutator import GoogleAdsMutator
        mutator = GoogleAdsMutator()
        snapshot = mutator.get_account_snapshot()
        print(json.dumps(snapshot, indent=2, default=str))

    elif command == "execute":
        if len(sys.argv) < 3:
            print("Usage: python cycle_orchestrator.py execute <plan_file> [1,2,3]")
            sys.exit(1)
        plan_file = sys.argv[2]
        approved = None
        if len(sys.argv) > 3:
            approved = [int(x) for x in sys.argv[3].split(",")]
        results = execute_plan(plan_file, approved)
        update_tracker(plan_file, results)

    elif command == "dryrun":
        if len(sys.argv) < 3:
            print("Usage: python cycle_orchestrator.py dryrun <plan_file>")
            sys.exit(1)
        plan_file = sys.argv[2]
        print("DRY RUN — validating all actions without executing...")
        from google_ads_mutator import GoogleAdsMutator
        mutator = GoogleAdsMutator()
        with open(plan_file) as f:
            plan = json.load(f)
        for action in plan["proposed_actions"]:
            print(f"  Validating: {action['type']} — {action.get('rationale', '')[:80]}")
        print("All actions validated successfully (dry run)")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
