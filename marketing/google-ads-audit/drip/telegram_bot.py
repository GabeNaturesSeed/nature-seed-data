"""
Telegram Bot — Nature's Seed Google Ads Drip Automation
========================================================
Sends optimization plans to Telegram and polls for approval.
Uses raw HTTP API — no framework dependencies.

Setup:
    1. Message @BotFather on Telegram → /newbot → get token
    2. Message your bot → run `python telegram_bot.py setup` → get chat_id
    3. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env

Usage:
    from telegram_bot import TelegramBot
    bot = TelegramBot()
    bot.send_plan(plan_summary_text)
    bot.send_message("Changes executed successfully!")
"""

import json
import logging
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("telegram_bot")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_env():
    """Load .env from project root."""
    env = {}
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        raise FileNotFoundError(f".env not found at {env_file}")
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip().strip("'\"")
    return env


# Telegram message size limit
MAX_MESSAGE_LENGTH = 4096


class TelegramBot:
    """Simple Telegram bot using raw HTTP API."""

    def __init__(self):
        env = _load_env()
        self.token = env.get("TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_BOT_API")
        self.chat_id = env.get("TELEGRAM_CHAT_ID")

        if not self.token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN not found in .env. "
                "Create a bot via @BotFather and add the token."
            )
        if not self.chat_id:
            raise ValueError(
                "TELEGRAM_CHAT_ID not found in .env. "
                "Run `python telegram_bot.py setup` to get your chat ID."
            )

        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def _api_call(self, method: str, data: dict) -> dict:
        """Make an API call to Telegram."""
        url = f"{self.base_url}/{method}"
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            log.error(f"Telegram API error: {e.code} — {body}")
            if e.code == 429:
                retry = json.loads(body).get("parameters", {}).get("retry_after", 5)
                log.info(f"Rate limited. Waiting {retry}s...")
                time.sleep(retry)
                return self._api_call(method, data)
            raise

    def send_message(self, text: str, parse_mode: str = "HTML") -> dict:
        """
        Send a message, automatically splitting if >4096 chars.
        Uses HTML parse mode by default (safer than MarkdownV2 escaping).
        """
        chunks = self._split_message(text)
        results = []
        for i, chunk in enumerate(chunks):
            result = self._api_call("sendMessage", {
                "chat_id": self.chat_id,
                "text": chunk,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            })
            results.append(result)
            if i < len(chunks) - 1:
                time.sleep(0.1)  # Small delay between chunks
        return results[-1] if results else {}

    def send_plan(self, plan_markdown: str) -> list:
        """
        Send an optimization plan to Telegram.
        Converts markdown to HTML for cleaner rendering.
        """
        html = self._markdown_to_telegram_html(plan_markdown)

        # Add header
        header = (
            "🔔 <b>Google Ads Optimization Plan</b>\n"
            f"📅 {datetime.now().strftime('%A, %B %d, %Y')}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        # Add footer with approval instructions
        footer = (
            "\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 <b>To approve, reply with:</b>\n"
            "• <code>APPROVE ALL</code> — approve everything\n"
            "• <code>APPROVE 1,2,4</code> — approve specific actions\n"
            "• <code>REJECT 3</code> — reject specific actions\n"
            "• <code>DEFER ALL</code> — postpone to next cycle\n"
            "• <code>MODIFY 2: [your notes]</code> — request changes\n\n"
            "⚠️ <b>Requires 2 confirmations before execution.</b>"
        )

        full_message = header + html + footer
        chunks = self._split_message(full_message)
        results = []
        for i, chunk in enumerate(chunks):
            result = self._api_call("sendMessage", {
                "chat_id": self.chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            })
            results.append(result)
            if i < len(chunks) - 1:
                time.sleep(0.1)
        return results

    def send_execution_report(self, results: list, plan: dict) -> dict:
        """Send execution results after changes are applied."""
        lines = [
            "✅ <b>Execution Report</b>",
            f"📅 {datetime.now().strftime('%A, %B %d, %Y %H:%M')}",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
        ]

        for r in results:
            action = plan["proposed_actions"][r["action_index"] - 1]
            if r["status"] == "success":
                lines.append(f"✅ Action {r['action_index']}: {action['type']} — <b>SUCCESS</b>")
            elif r["status"] == "skipped":
                lines.append(f"⏭️ Action {r['action_index']}: {action['type']} — skipped")
            elif r["status"] == "error":
                lines.append(f"❌ Action {r['action_index']}: {action['type']} — ERROR: {r.get('error', '?')}")
            elif r["status"] == "manual_required":
                lines.append(f"📋 Action {r['action_index']}: {action['type']} — manual review needed")

        lines.append("\n📊 Tracker updated. Changes logged.")

        return self.send_message("\n".join(lines))

    def send_confirmation_request(self, plan: dict, approval_response: str) -> dict:
        """
        Send a second confirmation request before execution.
        This is the double-confirmation step.
        """
        lines = [
            "⚠️ <b>FINAL CONFIRMATION REQUIRED</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"You approved: <code>{approval_response}</code>\n",
            "This will execute the following LIVE changes:\n",
        ]

        # Show what will be executed
        approved_indices = self._parse_approval(approval_response)
        for i, action in enumerate(plan["proposed_actions"], 1):
            if approved_indices is None or i in approved_indices:
                if action["type"] in ("budget_increase", "budget_decrease"):
                    lines.append(
                        f"  {i}. 💰 {action['campaign']}: "
                        f"${action['current']:.0f} → ${action['proposed']:.0f}/day"
                    )
                elif action["type"] == "add_negatives":
                    lines.append(f"  {i}. 🚫 Add {action['count']} negative keywords")
                elif action["type"] == "pause_keywords":
                    lines.append(f"  {i}. ⏸️ Pause {action['count']} keywords")
                elif action["type"] == "keyword_opportunities":
                    lines.append(f"  {i}. 📋 Review keyword opportunities (manual)")

        lines.append(
            "\n\n🔐 Reply <code>CONFIRM EXECUTE</code> to proceed."
            "\n❌ Reply <code>CANCEL</code> to abort."
        )

        return self.send_message("\n".join(lines))

    def send_keyword_opportunities(self, terms: list, campaigns: list) -> dict:
        """
        Send keyword opportunities with numbered campaign list.
        User replies with letter-number pairs: a3, b3, c1

        Args:
            terms: list of keyword opportunity dicts
            campaigns: list of campaign name strings (numbered for selection)
        """
        import html as html_mod
        lines = [
            "📋 <b>KEYWORD PLACEMENT — Step 1 of 3</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            "Which <b>campaign</b> should each keyword go to?\n",
            "<b>Keywords:</b>",
        ]

        # Letter each keyword: a, b, c, ...
        for i, t in enumerate(terms):
            letter = chr(ord('a') + i)
            rev = t.get("revenue", 0)
            roas = t.get("roas", 0)
            source = html_mod.escape(t.get("campaign", "Unknown"))
            lines.append(
                f"  <b>{letter}.</b> {html_mod.escape(t['term'])} — ${rev:,.0f} rev, {roas}x ROAS (via {source})"
            )

        lines.append("\n<b>Campaigns:</b>")
        for j, c_name in enumerate(campaigns, 1):
            lines.append(f"  <b>{j}.</b> {html_mod.escape(c_name)}")

        lines.append(
            "\n<b>Reply with letter+number pairs:</b>"
            "\n<code>a3, b3, c1, d3</code>"
            "\n\nor <code>SKIP</code> to skip all."
        )

        return self.send_message("\n".join(lines))

    def send_ad_group_selection(self, keywords_by_campaign: dict, ad_groups_by_campaign: dict) -> dict:
        """
        Send ad group selection for each keyword, grouped by campaign.
        User replies with letter+number pairs: a5, b2, c3

        Args:
            keywords_by_campaign: {campaign_name: [(letter, keyword_term), ...]}
            ad_groups_by_campaign: {campaign_name: [ag_name, ...]}
        """
        import html as html_mod
        lines = [
            "📋 <b>KEYWORD PLACEMENT — Step 2 of 3</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            "Which <b>ad group</b> for each keyword?\n",
        ]

        for campaign_name, keyword_pairs in keywords_by_campaign.items():
            lines.append(f"<b>Campaign: {html_mod.escape(campaign_name)}</b>")
            lines.append("  Keywords:")
            for letter, term in keyword_pairs:
                lines.append(f"    <b>{letter}.</b> {html_mod.escape(term)}")
            lines.append("  Ad groups:")
            for j, ag in enumerate(ad_groups_by_campaign[campaign_name], 1):
                lines.append(f"    <b>{j}.</b> {html_mod.escape(ag)}")
            lines.append("")

        lines.append(
            "<b>Reply with letter+number pairs:</b>"
            "\n<code>a5, b2, c3</code>"
        )

        return self.send_message("\n".join(lines))

    def send_match_type_selection(self, keywords: list) -> dict:
        """
        Send match type selection for all keywords.
        User replies with letter+type: a-E, b-P, c-E or just 'E' for all.

        Args:
            keywords: list of (letter, keyword_term) pairs
        """
        import html as html_mod
        lines = [
            "📋 <b>KEYWORD PLACEMENT — Step 3 of 3</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            "What <b>match type</b> for each keyword?\n",
        ]

        for letter, term in keywords:
            lines.append(f"  <b>{letter}.</b> {html_mod.escape(term)}")

        lines.append(
            "\n<b>Match types:</b>"
            "\n  <b>E</b> = Exact  |  <b>P</b> = Phrase  |  <b>B</b> = Broad\n"
            "\n<b>Reply with:</b>"
            "\n• <code>E</code> — same type for ALL"
            "\n• <code>a-E, b-P, c-E</code> — per keyword"
        )

        return self.send_message("\n".join(lines))

    @staticmethod
    def parse_letter_number_pairs(text: str, num_keywords: int) -> dict:
        """
        Parse letter+number replies like 'a3, b3, c1'.
        Returns dict: {letter: number} e.g. {'a': 3, 'b': 3, 'c': 1}
        """
        import re
        text = text.strip().upper()
        pairs = {}
        # Match patterns like A3, B12, C1
        for match in re.finditer(r'([A-Z])(\d+)', text):
            letter = match.group(1).lower()
            number = int(match.group(2))
            pairs[letter] = number
        return pairs

    @staticmethod
    def parse_match_types(text: str, keywords: list) -> dict:
        """
        Parse match type replies. Supports:
        - 'E' → all keywords get EXACT
        - 'a-E, b-P, c-E' → per keyword

        Returns dict: {letter: match_type}
        """
        import re
        text = text.strip().upper()
        match_map = {"E": "EXACT", "P": "PHRASE", "B": "BROAD",
                     "EXACT": "EXACT", "PHRASE": "PHRASE", "BROAD": "BROAD"}

        # Single letter = apply to all
        if text in match_map:
            return {letter: match_map[text] for letter, _ in keywords}

        # Per-keyword: a-E, b-P, c-E
        result = {}
        for match in re.finditer(r'([A-Z])\s*[-:]\s*([EPB]|EXACT|PHRASE|BROAD)', text):
            letter = match.group(1).lower()
            mtype = match_map.get(match.group(2), "PHRASE")
            result[letter] = mtype

        # Default unspecified to PHRASE
        for letter, _ in keywords:
            if letter not in result:
                result[letter] = "PHRASE"

        return result

    @staticmethod
    def parse_keyword_placements(text: str) -> list:
        """
        Legacy parser for free-text keyword placement replies.
        Format: keyword, campaign > ad_group, match_type

        Returns list of dicts: {keyword, campaign_name, ad_group_name, match_type}
        """
        if text.strip().upper() == "SKIP":
            return []

        placements = []

        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            parts = line.split(",", 1)
            if len(parts) < 2:
                continue

            keyword = parts[0].strip()
            rest = parts[1].strip()

            if ">" not in rest:
                continue

            campaign_part, ag_match = rest.split(">", 1)
            campaign_name = campaign_part.strip()

            ag_match = ag_match.strip()
            if "," in ag_match:
                last_comma = ag_match.rfind(",")
                ad_group_name = ag_match[:last_comma].strip()
                match_type = ag_match[last_comma + 1:].strip().upper()
            else:
                ad_group_name = ag_match
                match_type = "PHRASE"

            match_type_map = {
                "EXACT": "EXACT", "PHRASE": "PHRASE", "BROAD": "BROAD",
                "E": "EXACT", "P": "PHRASE", "B": "BROAD",
            }
            match_type = match_type_map.get(match_type, "PHRASE")

            placements.append({
                "keyword": keyword,
                "campaign_name": campaign_name,
                "ad_group_name": ad_group_name,
                "match_type": match_type,
            })

        return placements

    def send_keyword_confirmation(self, placements: list) -> dict:
        """Send confirmation of resolved keyword placements before execution."""
        lines = [
            "⚠️ <b>KEYWORD PLACEMENT CONFIRMATION</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            "The following keywords will be added:\n",
        ]

        for p in placements:
            lines.append(
                f"  • <b>{p['keyword']}</b> ({p['match_type']})"
            )
            lines.append(
                f"    → {p['campaign_name']} &gt; {p['ad_group_name']}"
            )
            if p.get("ad_group_id"):
                lines.append(f"    ✅ Ad group found (ID: {p['ad_group_id']})")
            elif p.get("create_ad_group"):
                lines.append(f"    🆕 Ad group will be created")
            if p.get("error"):
                lines.append(f"    ❌ {p['error']}")

        lines.append(
            "\n\nReply <code>CONFIRM EXECUTE</code> to add these keywords."
            "\nReply <code>CANCEL</code> to skip."
        )

        return self.send_message("\n".join(lines))

    def get_updates(self, offset: int = 0, timeout: int = 30) -> list:
        """Poll for new messages (long polling)."""
        result = self._api_call("getUpdates", {
            "offset": offset,
            "timeout": timeout,
            "allowed_updates": ["message"],
        })
        return result.get("result", [])

    def wait_for_reply(self, timeout_minutes: int = 60) -> str:
        """
        Wait for a reply from the user.
        Returns the message text, or None if timeout.
        """
        log.info(f"Waiting for reply (timeout: {timeout_minutes}min)...")
        offset = 0
        deadline = time.time() + (timeout_minutes * 60)

        # First, clear any old updates
        updates = self.get_updates(offset=0, timeout=0)
        if updates:
            offset = updates[-1]["update_id"] + 1

        while time.time() < deadline:
            updates = self.get_updates(offset=offset, timeout=30)
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = str(msg.get("chat", {}).get("id", ""))

                if chat_id == str(self.chat_id) and text:
                    log.info(f"Received reply: {text}")
                    return text

        log.warning("Timeout waiting for reply")
        return None

    @staticmethod
    def _parse_approval(text: str) -> list:
        """
        Parse approval response text.
        Returns list of approved action indices, or None for APPROVE ALL.
        """
        text = text.strip().upper()

        if text == "APPROVE ALL":
            return None  # None means all

        if text.startswith("APPROVE"):
            # "APPROVE 1,2,4"
            nums = text.replace("APPROVE", "").strip()
            return [int(n.strip()) for n in nums.split(",") if n.strip().isdigit()]

        if text == "DEFER ALL":
            return []  # Empty list means none

        return None

    @staticmethod
    def _split_message(text: str) -> list:
        """Split a message into chunks respecting the 4096 char limit."""
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]

        chunks = []
        current = ""

        for line in text.split("\n"):
            if len(current) + len(line) + 1 > MAX_MESSAGE_LENGTH:
                if current:
                    chunks.append(current)
                current = line
            else:
                current = current + "\n" + line if current else line

        if current:
            chunks.append(current)

        return chunks

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special chars in plain text (not our tags)."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _markdown_to_telegram_html(md: str) -> str:
        """
        Convert simplified markdown to Telegram HTML.
        Handles headers, bold, code, and tables (as pre blocks).
        """
        lines = []
        in_table = False

        for line in md.split("\n"):
            # Escape HTML entities first, then apply our formatting
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Headers
            if line.startswith("### "):
                if in_table:
                    lines.append("</pre>")
                    in_table = False
                lines.append(f"\n<b>{line[4:]}</b>")
            elif line.startswith("## "):
                if in_table:
                    lines.append("</pre>")
                    in_table = False
                lines.append(f"\n<b>{'━' * 20}</b>")
                lines.append(f"<b>{line[3:]}</b>")
            elif line.startswith("# "):
                if in_table:
                    lines.append("</pre>")
                    in_table = False
                lines.append(f"\n🔷 <b>{line[2:]}</b>")

            # Tables → preformatted
            elif line.startswith("|"):
                if line.startswith("|---") or line.startswith("| ---"):
                    continue  # Skip separator rows
                if not in_table:
                    lines.append("<pre>")
                    in_table = True
                # Clean table row
                cells = [c.strip() for c in line.split("|")[1:-1]]
                lines.append("  ".join(f"{c:<15}" for c in cells))

            # Bold text
            elif "**" in line:
                converted = line
                while "**" in converted:
                    converted = converted.replace("**", "<b>", 1)
                    converted = converted.replace("**", "</b>", 1)
                if in_table:
                    lines.append("</pre>")
                    in_table = False
                lines.append(converted)

            # Code blocks
            elif line.startswith("```"):
                continue  # Skip code fences

            # Bullet points
            elif line.strip().startswith("- "):
                if in_table:
                    lines.append("</pre>")
                    in_table = False
                lines.append(f"  • {line.strip()[2:]}")
            elif line.strip().startswith("  - "):
                lines.append(f"    ◦ {line.strip()[4:]}")

            # Horizontal rules
            elif line.startswith("---"):
                if in_table:
                    lines.append("</pre>")
                    in_table = False
                lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")

            else:
                if in_table:
                    lines.append("</pre>")
                    in_table = False
                lines.append(line)

        if in_table:
            lines.append("</pre>")

        return "\n".join(lines)


# ── Setup Helper ─────────────────────────────────────────────────────────────

def setup():
    """Interactive setup: get chat_id by receiving a message from the user."""
    env = _load_env()
    token = env.get("TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_BOT_API")

    if not token:
        print("=" * 50)
        print("TELEGRAM BOT SETUP")
        print("=" * 50)
        print()
        print("Step 1: Create a bot")
        print("  1. Open Telegram and message @BotFather")
        print("  2. Send /newbot")
        print("  3. Name it: Nature's Seed Ads Bot")
        print("  4. Username: NaturesSeedAdsBot (must end in 'bot')")
        print("  5. Copy the API token BotFather gives you")
        print()
        print("Step 2: Add to .env")
        print("  Add this line to your .env file:")
        print("  TELEGRAM_BOT_TOKEN='your-token-here'")
        print()
        print("Then run this setup again.")
        return

    print(f"Bot token found: {token[:10]}...")
    print()
    print("Now send any message to your bot in Telegram.")
    print("Waiting for your message...")

    base_url = f"https://api.telegram.org/bot{token}"

    # Poll for message
    offset = 0
    for attempt in range(12):  # 12 × 10s = 2 minutes
        url = f"{base_url}/getUpdates?offset={offset}&timeout=10"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        for update in data.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            chat = msg.get("chat", {})
            user = msg.get("from", {})

            if chat.get("id"):
                chat_id = chat["id"]
                name = user.get("first_name", "Unknown")
                print()
                print(f"✅ Got message from {name}!")
                print(f"   Chat ID: {chat_id}")
                print()
                print("Add this to your .env file:")
                print(f"   TELEGRAM_CHAT_ID='{chat_id}'")
                print()

                # Send confirmation
                confirm_url = f"{base_url}/sendMessage"
                payload = json.dumps({
                    "chat_id": chat_id,
                    "text": "✅ Bot connected! Nature's Seed Google Ads optimization plans will be sent here.",
                    "parse_mode": "HTML",
                }).encode()
                req = urllib.request.Request(
                    confirm_url, data=payload,
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req)
                return

    print("⏰ Timeout — no message received. Make sure you messaged the bot.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup()
    else:
        print("Usage:")
        print("  python telegram_bot.py setup  — Set up bot and get chat_id")
        print()
        print("Or use in code:")
        print("  from telegram_bot import TelegramBot")
        print("  bot = TelegramBot()")
        print("  bot.send_message('Hello!')")
