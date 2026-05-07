#!/usr/bin/env python3
# docs/resource_classifier/classify_resources.py
"""
Classify all Nature's Seed resource pages using claude CLI.

Usage:
    python classify_resources.py [--batch-size 8] [--dry-run] [--reset]

Outputs:
    docs/resource-classifier/classifications.csv
    docs/resource-classifier/taxonomy-key.csv
    docs/resource-classifier/checkpoint.json
"""
import argparse
import time
from pathlib import Path

from docs.resource_classifier.checkpoint import load_checkpoint, save_checkpoint
from docs.resource_classifier.classifier import call_claude, ClassifierError
from docs.resource_classifier.env_loader import load_env
from docs.resource_classifier.fetcher import fetch_all_posts
from docs.resource_classifier.writer import append_classifications, rebuild_taxonomy_key

OUTPUT_DIR = Path(__file__).parent.parent / "resource-classifier"
CLASSIFICATIONS_CSV = OUTPUT_DIR / "classifications.csv"
TAXONOMY_KEY_CSV = OUTPUT_DIR / "taxonomy-key.csv"
CHECKPOINT_JSON = OUTPUT_DIR / "checkpoint.json"
# parents[0]=docs/resource_classifier, parents[1]=docs, parents[2]=naturesseed-content-pipeline
PROJECT_ROOT = Path(__file__).parents[2]
ENV_PATH = PROJECT_ROOT.parent / ".env"
DB_PATH = PROJECT_ROOT / "content_pipeline.db"


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify Nature's Seed resource pages")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true", help="Fetch articles, print first batch prompt, exit")
    parser.add_argument("--reset", action="store_true", help="Delete checkpoint and restart from scratch")
    parser.add_argument("--max-batches", type=int, default=None, help="Stop after N batches (for testing)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    env = load_env(ENV_PATH)

    if args.reset:
        for f in (CHECKPOINT_JSON, CLASSIFICATIONS_CSV, TAXONOMY_KEY_CSV):
            if f.exists():
                f.unlink()
        print("Checkpoint and output CSVs reset.")

    print("Loading articles from content_inventory DB...")
    posts = fetch_all_posts(env, db_path=DB_PATH)
    print(f"Loaded {len(posts)} articles.")

    batches = [posts[i:i + args.batch_size] for i in range(0, len(posts), args.batch_size)]
    print(f"Total batches: {len(batches)} (batch size {args.batch_size})")

    if args.dry_run:
        from docs.resource_classifier.prompt import build_prompt
        print("\n--- DRY RUN: First batch prompt ---\n")
        print(build_prompt(batches[0])[:2000])
        print("\n[dry run complete — no claude calls made]")
        return

    completed = load_checkpoint(CHECKPOINT_JSON)
    print(f"Resuming — {len(completed)}/{len(batches)} batches already done.")

    for i, batch in enumerate(batches):
        if args.max_batches is not None and i >= args.max_batches:
            print(f"Reached --max-batches={args.max_batches}, stopping.")
            break

        if i in completed:
            continue

        print(f"Batch {i + 1}/{len(batches)} ({len(batch)} articles)...", end=" ", flush=True)
        try:
            results = call_claude(batch)
        except ClassifierError as e:
            print(f"ERROR — skipping batch {i}: {e}")
            continue

        # Merge original post metadata back (title, url) in case claude omits them
        post_lookup = {p["post_id"]: p for p in batch}
        for r in results:
            pid = r.get("post_id")
            if pid and pid in post_lookup:
                r.setdefault("title", post_lookup[pid]["title"])
                r.setdefault("url", post_lookup[pid]["url"])

        if len(results) != len(batch):
            print(f"WARN: batch {i} expected {len(batch)} results, got {len(results)}")

        append_classifications(CLASSIFICATIONS_CSV, results)
        completed.add(i)
        save_checkpoint(CHECKPOINT_JSON, completed)
        print(f"done. ({len(completed)}/{len(batches)} complete)")

        time.sleep(0.3)  # rate limit

    rebuild_taxonomy_key(CLASSIFICATIONS_CSV, TAXONOMY_KEY_CSV)
    print(f"\nDone. {len(completed)} batches classified.")
    print(f"  classifications: {CLASSIFICATIONS_CSV}")
    print(f"  taxonomy key:    {TAXONOMY_KEY_CSV}")


if __name__ == "__main__":
    main()
