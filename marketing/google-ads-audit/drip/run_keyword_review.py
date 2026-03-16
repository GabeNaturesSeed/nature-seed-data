#!/usr/bin/env python3
"""
One-off: Run keyword opportunities review via Telegram.
Sends the 8 keyword opportunities, waits for placement instructions,
resolves IDs, confirms, and executes.
"""
import html
import json
import sys
import logging
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("keyword_review")

DRIP_DIR = Path(__file__).resolve().parent
PLANS_DIR = DRIP_DIR / "plans"

sys.path.insert(0, str(DRIP_DIR))

from telegram_bot import TelegramBot
from google_ads_mutator import GoogleAdsMutator
from cycle_orchestrator import handle_keyword_opportunities

def main():
    # Use latest plan, or pass a date as arg: python run_keyword_review.py 20260310
    if len(sys.argv) > 1:
        plan_date = sys.argv[1]
    else:
        # Find most recent plan
        import glob
        plans = sorted(glob.glob(str(PLANS_DIR / "plan_*.json")))
        plans = [p for p in plans if "summary" not in p]
        if not plans:
            log.error("No plan files found.")
            return
        plan_date = None
        plan_path = Path(plans[-1])
        log.info(f"Using latest plan: {plan_path.name}")

    if plan_date:
        plan_path = PLANS_DIR / f"plan_{plan_date}.json"

    with open(plan_path) as f:
        plan = json.load(f)

    bot = TelegramBot()
    mutator = GoogleAdsMutator()

    log.info("Starting keyword opportunities review via Telegram...")
    keyword_actions = handle_keyword_opportunities(bot, plan, mutator)

    if not keyword_actions:
        log.info("No keyword actions to execute. Done.")
        return

    log.info(f"Executing {len(keyword_actions)} keyword additions...")

    results = []
    for action in keyword_actions:
        try:
            result = mutator.add_keyword_to_ad_group(
                ad_group_id=action["ad_group_id"],
                keyword_text=action["keyword"],
                match_type=action["match_type"],
                validate_only=False,
            )
            results.append({"keyword": action["keyword"], "status": "success", "result": result})
            log.info(f"  ✅ Added '{action['keyword']}' ({action['match_type']}) to {action['ad_group_name']}")
        except Exception as e:
            # Retry once after 3s for transient 500 errors
            if "500" in str(e) or "Internal error" in str(e):
                log.info(f"  ⏳ Retrying '{action['keyword']}' after transient error...")
                time.sleep(3)
                try:
                    result = mutator.add_keyword_to_ad_group(
                        ad_group_id=action["ad_group_id"],
                        keyword_text=action["keyword"],
                        match_type=action["match_type"],
                        validate_only=False,
                    )
                    results.append({"keyword": action["keyword"], "status": "success", "result": result})
                    log.info(f"  ✅ Retry succeeded: '{action['keyword']}'")
                    continue
                except Exception as e2:
                    e = e2  # Use retry error
            results.append({"keyword": action["keyword"], "status": "error", "error": str(e)})
            log.error(f"  ❌ Failed '{action['keyword']}': {e}")
        time.sleep(1)

    # Save results
    from datetime import datetime
    results_path = PLANS_DIR / f"results_keyword_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    # Report to Telegram (HTML-escape error messages)
    success = [r for r in results if r["status"] == "success"]
    errors = [r for r in results if r["status"] == "error"]

    report = "<b>🔑 Keyword Placement Results</b>\n\n"
    report += f"✅ Added: {len(success)}\n"
    if errors:
        report += f"❌ Errors: {len(errors)}\n"
    report += "\n"

    for r in success:
        report += f"• <b>{html.escape(r['keyword'])}</b> — added\n"
    for r in errors:
        safe_err = html.escape(str(r['error'])[:100])
        report += f"• <b>{html.escape(r['keyword'])}</b> — {safe_err}\n"

    bot.send_message(report)
    log.info(f"Done! {len(success)} keywords added, {len(errors)} errors.")

    mutator.save_change_log()

if __name__ == "__main__":
    main()
