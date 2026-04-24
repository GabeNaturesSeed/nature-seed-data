"""Scan-decay stage — runs all rules, reconciles stale findings,
summarizes open findings into refresh_queue."""

import hashlib
from datetime import datetime, timezone
from typing import Sequence

import structlog
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from naturesseed_pipeline.audit_rules.base import AuditContext, DecayRule
from naturesseed_pipeline.db.models import ContentInventory, DecayFinding, RefreshQueue

log = structlog.get_logger()


def _snippet_hash(snippet: str) -> str:
    return hashlib.sha256(snippet.encode("utf-8")).hexdigest()[:16]


def run_scan_decay(
    session: Session,
    rules: Sequence[DecayRule],
    current_shipping: str,
    llm_client,
    llm_model: str = "claude-sonnet-4-6",
    llm_token_budget: int = 50_000,
    only_article_id: int | None = None,
    only_rule_name: str | None = None,
) -> dict[str, int]:
    """Run all decay rules. Mark prior open findings stale, rewrite or resolve them,
    then rebuild refresh_queue."""
    if only_rule_name:
        rules = [r for r in rules if r.name == only_rule_name]

    # Step 1: stale-out existing open findings for the scope being scanned
    stale_q = update(DecayFinding).where(DecayFinding.status == "open")
    if only_article_id:
        stale_q = stale_q.where(DecayFinding.content_inventory_id == only_article_id)
    session.execute(stale_q.values(status="stale"))
    session.flush()

    ctx = AuditContext(
        session=session,
        current_shipping=current_shipping,
        llm_client=llm_client,
        llm_model=llm_model,
        llm_token_budget_remaining=llm_token_budget,
    )
    # Share thin-content threshold through cache for ThinContentRule
    try:
        from naturesseed_pipeline.config import settings
        ctx._cache["thin_word_count"] = settings.audit_thin_word_count
    except Exception:
        ctx._cache["thin_word_count"] = 300

    # Step 2: run rules per article
    content_q = select(ContentInventory)
    if only_article_id:
        content_q = content_q.where(ContentInventory.id == only_article_id)
    articles = session.execute(content_q).scalars().all()

    counts: dict[str, int] = {
        "findings_open": 0,
        "findings_reopened": 0,
        "findings_new": 0,
    }

    for article in articles:
        for rule in rules:
            try:
                findings = rule.check(article, ctx)
            except Exception as e:
                log.error("rule.error", rule=rule.name, article=article.id, error=str(e))
                continue

            for f in findings:
                sh = _snippet_hash(f.snippet)
                existing = session.execute(
                    select(DecayFinding).where(
                        DecayFinding.content_inventory_id == article.id,
                        DecayFinding.rule_name == f.rule_name,
                    )
                ).scalars().all()
                match = next(
                    (e for e in existing if _snippet_hash(e.snippet or "") == sh),
                    None,
                )
                if match is None:
                    session.add(DecayFinding(
                        content_inventory_id=article.id,
                        rule_name=f.rule_name,
                        severity=f.severity,
                        snippet=f.snippet,
                        suggested_action=f.suggested_action,
                        status="open",
                    ))
                    counts["findings_new"] += 1
                else:
                    match.status = "open"
                    match.suggested_action = f.suggested_action
                    match.detected_at = datetime.now(timezone.utc)
                    match.resolved_at = None
                    counts["findings_reopened"] += 1
        session.flush()

    # Step 3: stale → resolved
    now = datetime.now(timezone.utc)
    stale_scope_q = select(DecayFinding).where(DecayFinding.status == "stale")
    if only_article_id:
        stale_scope_q = stale_scope_q.where(
            DecayFinding.content_inventory_id == only_article_id
        )
    stale = session.execute(stale_scope_q).scalars().all()
    for f in stale:
        f.status = "resolved"
        f.resolved_at = now
    session.flush()

    # Step 4: rebuild refresh_queue — clear pending rows for scope, then re-insert
    del_q = delete(RefreshQueue).where(RefreshQueue.status == "pending")
    if only_article_id:
        del_q = del_q.where(
            RefreshQueue.content_inventory_id == only_article_id
        )
    session.execute(del_q)

    open_scope_q = select(DecayFinding).where(DecayFinding.status == "open")
    if only_article_id:
        open_scope_q = open_scope_q.where(
            DecayFinding.content_inventory_id == only_article_id
        )
    open_findings = session.execute(open_scope_q).scalars().all()

    by_content: dict[int, list[DecayFinding]] = {}
    for f in open_findings:
        by_content.setdefault(f.content_inventory_id, []).append(f)

    for cid, flist in by_content.items():
        rule_names = sorted({f.rule_name for f in flist})
        session.add(RefreshQueue(
            content_inventory_id=cid,
            reason=f"{len(flist)} decay findings: " + ", ".join(rule_names),
            status="pending",
        ))

    counts["findings_open"] = len(open_findings)
    log.info("audit.scan_decay.done", **counts)
    return counts
