#!/usr/bin/env python3
"""
Nature's Seed - Klaviyo Catalog Price + Availability Sync

Backfills price (and fixes url / availability / image) on the Klaviyo custom
catalog items, which are keyed by WC SKU (external_id). Price is sourced from
the WC per-variation `price` (WC leaves regular_price blank); url and image
come from the parent product because a variation has no page of its own.

Klaviyo bulk-update updates EXISTING items only (it does not create), so SKUs
present in WC but missing from the catalog are LOGGED, not created.

Safe by default: prints a dry-run summary unless --execute is passed.

Usage:
    python -m feeds.sync.sync_klaviyo_catalog            # dry-run (no writes)
    python -m feeds.sync.sync_klaviyo_catalog --execute  # live push (needs KLAVIYO_API)
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from feeds.env_loader import load_env

KLAVIYO_BASE = "https://a.klaviyo.com/api"
DEFAULT_REVISION = "2024-10-15"          # override with KLAVIYO_REVISION if the account needs it
INTEGRATION = "$custom"
CATALOG = "$default"
BATCH_SIZE = 100                         # Klaviyo bulk-update hard limit
SELLABLE = {"instock", "onbackorder"}    # onbackorder is still sellable (house rule)

MASTER_PATH = Path(__file__).parent.parent / "feed_master.json"
LOG_PATH = Path(__file__).parent / f"{datetime.now(timezone.utc).date().isoformat()}-klaviyo-sync-log.json"


# --------------------------------------------------------------------------
# Pure helpers (unit-tested)
# --------------------------------------------------------------------------

def item_id_for(sku: str) -> str:
    """Klaviyo compound catalog-item id for a WC SKU."""
    return f"{INTEGRATION}:::{CATALOG}:::{sku}"


def _to_price(value):
    """Parse a WC price into a positive float, else None."""
    try:
        f = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def _is_published(stock_status) -> bool:
    return str(stock_status or "").strip().lower() in SELLABLE


def build_sku_attrs(master: dict) -> dict:
    """Map every publishable WC SKU -> {price, url, published[, image_full_url]}.

    Variation-keyed: price/availability from the variation, url/image from the
    parent (a variation has no page of its own). Simple products use their own
    fields. Draft products and SKU-less variations are skipped.
    """
    out = {}
    for p in master.get("products", {}).values():
        if p.get("status") != "publish":
            continue
        parent_url = p.get("url") or ""
        images = p.get("images") or []
        parent_img = images[0] if images else ""
        variations = p.get("variations") or []
        rows = variations if variations else [None]
        for v in rows:
            src = v if v is not None else p
            sku = src.get("sku")
            if not sku:
                continue
            price = _to_price(src.get("price"))
            if price is None:
                continue
            attrs = {
                "price": price,
                "url": parent_url,
                "published": _is_published(src.get("stock_status")),
            }
            if parent_img:
                attrs["image_full_url"] = parent_img
            out[sku] = attrs
    return out


def build_catalog_item_update(item_id: str, attrs: dict) -> dict:
    """One catalog-item object for the bulk-update job body."""
    return {"type": "catalog-item", "id": item_id, "attributes": dict(attrs)}


def build_bulk_update_payload(items: list) -> dict:
    """Wrap up to 100 catalog-item objects in the bulk-update-job envelope."""
    return {"data": {"type": "catalog-item-bulk-update-job",
                     "attributes": {"items": {"data": items}}}}


def chunked(seq, size=BATCH_SIZE):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def compute_changes(targets: dict, existing: dict):
    """Given WC targets {sku: attrs} and live catalog {sku: current},
    return (updates, report). Only SKUs already in the catalog are updated;
    the rest are reported as coverage gaps (bulk-update cannot create).
    """
    updates = []
    missing_from_catalog = []
    price_fixes = 0
    url_fixes = 0
    unpublish = []
    for sku, attrs in targets.items():
        cur = existing.get(sku)
        if not cur:
            missing_from_catalog.append(sku)
            continue
        if cur.get("price") in (None, "", 0) or _to_price(cur.get("price")) != attrs["price"]:
            price_fixes += 1
        if attrs.get("url") and cur.get("url") != attrs["url"]:
            url_fixes += 1
        if attrs.get("published") is False and cur.get("published") is True:
            unpublish.append(sku)
        updates.append(build_catalog_item_update(item_id_for(sku), attrs))
    orphans = [s for s in existing if s not in targets]
    report = {
        "targets": len(targets),
        "catalog_items": len(existing),
        "will_update": len(updates),
        "price_fixes": price_fixes,
        "url_fixes": url_fixes,
        "will_unpublish": unpublish,
        "missing_from_catalog": missing_from_catalog,
        "orphans_in_catalog": orphans,
    }
    return updates, report


# --------------------------------------------------------------------------
# Network (integration; needs KLAVIYO_API - runs in CI or with the key)
# --------------------------------------------------------------------------

def _headers(env):
    key = env.get("KLAVIYO_API") or env.get("KLAVIYO_API_KEY")
    if not key:
        raise RuntimeError("KLAVIYO_API (or KLAVIYO_API_KEY) not set in env")
    return {
        "Authorization": f"Klaviyo-API-Key {key}",
        "revision": env.get("KLAVIYO_REVISION") or DEFAULT_REVISION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def fetch_existing_items(env) -> dict:
    """Return {sku: {id, price, url, published, title}} for every catalog item."""
    headers = _headers(env)
    out = {}
    # Build the URL by hand: requests percent-encodes brackets, which Klaviyo rejects.
    url = (f"{KLAVIYO_BASE}/catalog-items?page[size]=100"
           "&fields[catalog-item]=external_id,price,url,published,title")
    while url:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for it in data.get("data", []):
            a = it.get("attributes", {})
            sku = a.get("external_id")
            if sku:
                out[sku] = {"id": it.get("id"), "price": a.get("price"),
                            "url": a.get("url"), "published": a.get("published"),
                            "title": a.get("title")}
        url = data.get("links", {}).get("next")
        if url:
            time.sleep(0.3)
    return out


def _post_job(env, payload):
    return requests.post(f"{KLAVIYO_BASE}/catalog-item-bulk-update-jobs",
                         headers=_headers(env), json=payload, timeout=30)


def _poll_job(env, job_id, tries=30):
    url = (f"{KLAVIYO_BASE}/catalog-item-bulk-update-jobs/{job_id}"
           "?fields[catalog-item-bulk-update-job]=status,completed_count,failed_count,errors")
    for _ in range(tries):
        resp = requests.get(url, headers=_headers(env), timeout=30)
        resp.raise_for_status()
        a = resp.json().get("data", {}).get("attributes", {})
        if a.get("status") in ("complete", "cancelled"):
            return a
        time.sleep(1.0)
    return {"status": "timeout"}


def sync(execute=False):
    env = load_env()
    master = json.loads(MASTER_PATH.read_text())
    targets = build_sku_attrs(master)
    existing = fetch_existing_items(env)
    updates, report = compute_changes(targets, existing)

    print(f"[klaviyo-catalog] targets={report['targets']} catalog={report['catalog_items']} "
          f"to_update={report['will_update']} price_fixes={report['price_fixes']} "
          f"url_fixes={report['url_fixes']} unpublish={len(report['will_unpublish'])} "
          f"missing_from_catalog={len(report['missing_from_catalog'])} "
          f"orphans={len(report['orphans_in_catalog'])}")

    results = []
    if not execute:
        print("[klaviyo-catalog] DRY-RUN (no writes). Pass --execute to push.")
        for obj in updates[:5]:
            print("  sample:", obj["id"], obj["attributes"])
    else:
        for batch in chunked(updates):
            resp = _post_job(env, build_bulk_update_payload(batch))
            if resp.status_code not in (200, 201, 202):
                results.append({"status": resp.status_code, "error": resp.text[:500], "n": len(batch)})
                print(f"  batch FAILED [{resp.status_code}]: {resp.text[:200]}")
                continue
            job_id = (resp.json().get("data") or {}).get("id")
            outcome = _poll_job(env, job_id) if job_id else {"status": "no_job_id"}
            results.append({"job_id": job_id, "n": len(batch), **outcome})
            print(f"  batch {len(batch)} -> job {job_id} {outcome.get('status')} "
                  f"ok={outcome.get('completed_count')} fail={outcome.get('failed_count')}")
            time.sleep(0.5)

    summary = {"synced_at": datetime.now(timezone.utc).isoformat(),
               "execute": execute, "report": report, "results": results}
    LOG_PATH.write_text(json.dumps(summary, indent=2))
    print(f"[klaviyo-catalog] summary -> {LOG_PATH}")
    return summary


def main():
    ap = argparse.ArgumentParser(description="Sync WC prices to the Klaviyo catalog")
    ap.add_argument("--execute", action="store_true", help="Actually push (default: dry-run)")
    args = ap.parse_args()
    sync(execute=args.execute)


if __name__ == "__main__":
    main()
