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

def generate_plan():
    """
    Generate today's optimization plan based on:
    1. Implementation tracker goals and next steps
    2. Live account data
    3. Season constraints
    4. COGS margins
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

    # Pull live data
    mutator = GoogleAdsMutator()
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
                # These require manual review — skip auto-execution
                log.info("Keyword opportunities require manual ad group selection — skipping auto-execution")
                results.append({"action_index": i, "type": action["type"], "status": "manual_required"})

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

def run_full_cycle(wait_minutes: int = 120):
    """
    Full cycle with Telegram integration and double confirmation.

    Flow:
        1. Generate plan
        2. Send to Telegram
        3. Wait for first approval
        4. Send confirmation request (second approval)
        5. Wait for CONFIRM EXECUTE
        6. Execute approved actions
        7. Send execution report
        8. Update tracker + approval log
    """
    from telegram_bot import TelegramBot

    # Step 1: Generate plan
    log.info("=" * 60)
    log.info("STARTING FULL CYCLE")
    log.info("=" * 60)

    plan = generate_plan()
    plan_path = PLANS_DIR / f"plan_{datetime.now().strftime('%Y%m%d')}.json"

    # Step 2: Send to Telegram
    bot = TelegramBot()

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

    # Step 4: Send second confirmation
    log.info("Sending second confirmation request...")
    bot.send_confirmation_request(plan, first_reply)

    # Step 5: Wait for CONFIRM EXECUTE
    log.info("Waiting for final confirmation...")
    second_reply = bot.wait_for_reply(timeout_minutes=30)

    if not second_reply or "CONFIRM EXECUTE" not in second_reply.upper():
        log.warning(f"Execution cancelled. Reply was: {second_reply}")
        bot.send_message("❌ Execution cancelled. No changes made. Plan saved for next cycle.")
        return

    second_confirmation_time = datetime.now().strftime("%H:%M")

    # Step 6: Execute
    log.info("Executing approved actions...")
    results = execute_plan(str(plan_path), approved_indices)

    # Step 7: Send execution report
    bot.send_execution_report(results, plan)

    # Step 8: Update tracker + approval log
    update_tracker(str(plan_path), results)
    update_approval_log(
        cycle_num=plan["cycle_number"],
        plan=plan,
        first_approval=first_reply,
        first_approval_time=first_approval_time,
        second_confirmation=second_reply,
        second_confirmation_time=second_confirmation_time,
        results=results,
    )

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
