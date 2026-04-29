#!/usr/bin/env python3
"""
Nature's Seed — Feed Audit Digest
Loads feed_master.json, runs all channel adapters, writes daily digest markdown.

Usage:
    python3 -m feeds.digest.run_audit
"""

import json
from datetime import date
from pathlib import Path

from feeds.env_loader import load_env
from feeds.adapters.walmart import WalmartAdapter
from feeds.adapters.amazon import AmazonAdapter
from feeds.adapters.google_merchant import GoogleMerchantAdapter
from feeds.adapters.klaviyo import KlaviyoAdapter
from feeds.adapters.shopper_approved import ShopperApprovedAdapter
from feeds.adapters.reddit import RedditAdapter
from feeds.adapters.facebook import FacebookAdapter
from feeds.adapters.pinterest import PinterestAdapter

MASTER_PATH = Path(__file__).parent.parent / "feed_master.json"
DIGEST_DIR = Path(__file__).parent


def build_digest_markdown(results, date: str) -> str:
    lines = [f"# Feed Health — {date}\n"]

    # Summary table
    lines.append("## Summary\n")
    lines.append("| Channel | Coverage | Drift | Quality Issues |")
    lines.append("|---|---|---|---|")
    for r in results:
        if r.error:
            lines.append(f"| {r.channel} | ERROR | ERROR | {r.error} |")
        else:
            cov = f"{r.coverage.channel_total}/{r.coverage.wc_total}"
            drift = len(r.drift.drifted)
            quality = len(r.quality.incomplete)
            lines.append(f"| {r.channel} | {cov} | {drift} | {quality} |")

    lines.append("")

    # Action items
    lines.append("## Action Items\n")
    has_actions = False
    for r in results:
        if r.error:
            lines.append(f"- [ ] **{r.channel}**: investigate error — {r.error}")
            has_actions = True
            continue
        for d in r.drift.drifted:
            lines.append(f"- [ ] **{r.channel}**: sync {d['field']} on `{d['sku']}` (WC: {d['wc']} | channel: {d['channel']})")
            has_actions = True
        if r.coverage.missing_skus:
            n = len(r.coverage.missing_skus)
            lines.append(f"- [ ] **{r.channel}**: {n} WC SKUs not listed — {', '.join(r.coverage.missing_skus[:5])}{'...' if n > 5 else ''}")
            has_actions = True
        for q in r.quality.incomplete[:5]:
            lines.append(f"- [ ] **{r.channel}**: `{q['sku']}` missing fields: {', '.join(q['missing_fields'])}")
            has_actions = True

    if not has_actions:
        lines.append("_No action items — all channels healthy._")

    # Detail sections
    for r in results:
        if r.error or not r.coverage.missing_skus:
            continue
        lines.append(f"\n### {r.channel} — Missing SKUs\n")
        for sku in r.coverage.missing_skus:
            lines.append(f"- {sku}")

    return "\n".join(lines) + "\n"


def run_audit():
    env = load_env()

    with open(MASTER_PATH) as f:
        master = json.load(f)

    print(f"[AUDIT] feed_master: {master['meta']['product_count']} products, generated {master['meta']['generated_at']}")

    adapters = [
        WalmartAdapter(env),
        AmazonAdapter(env),
        GoogleMerchantAdapter(env),
        KlaviyoAdapter(env),
        ShopperApprovedAdapter(env),
        RedditAdapter(env),
        FacebookAdapter(env),
        PinterestAdapter(env),
    ]

    results = []
    for adapter in adapters:
        print(f"  [{adapter.channel}] running...")
        result = adapter.run(master)
        if result.error:
            print(f"    ERROR: {result.error}")
        else:
            print(f"    coverage: {result.coverage.channel_total}/{result.coverage.wc_total} | drift: {len(result.drift.drifted)} | quality: {len(result.quality.incomplete)}")
        results.append(result)

    today = date.today().isoformat()
    digest = build_digest_markdown(results, date=today)
    out_path = DIGEST_DIR / f"{today}-feed-health.md"
    with open(out_path, "w") as f:
        f.write(digest)
    print(f"\n[DONE] Digest written to {out_path}")
    return results


if __name__ == "__main__":
    run_audit()
