"""Media research pipeline — listener sweep, classification, promotion to keywords."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.agents.media_listener import classify_signal
from naturesseed_pipeline.db.models import KeywordCandidate, MediaSignal
from naturesseed_pipeline.integrations.media_sources import (
    RawSignal,
    fetch_all,
    load_media_config,
)

log = structlog.get_logger()


def run_listener_sweep(
    session: Session,
    config: dict[str, Any] | None = None,
    signals: list[RawSignal] | None = None,
) -> dict[str, Any]:
    """Pull signals from all sources, classify, and store in media_signals.

    Deduplicates by URL. Returns counts by source type.
    """
    if signals is None:
        signals = fetch_all(config)

    # Get existing URLs for dedup
    existing_urls: set[str] = set(
        session.execute(
            select(MediaSignal.url).where(MediaSignal.url.isnot(None))
        ).scalars().all()
    )

    counts: dict[str, int] = {}
    new_count = 0

    for signal in signals:
        if signal.url in existing_urls:
            continue

        classification = classify_signal(signal)

        row = MediaSignal(
            source_type=signal.source_type,
            source_name=signal.source_name,
            title=signal.title,
            url=signal.url,
            captured_text=signal.text[:5000] if signal.text else None,
            relevance_score=classification["relevance_score"],
            trending_score=classification["trending_score"],
            captured_at=signal.published_at or datetime.now(timezone.utc),
            status="new",
        )
        session.add(row)
        existing_urls.add(signal.url)
        new_count += 1
        counts[signal.source_type] = counts.get(signal.source_type, 0) + 1

    session.commit()
    log.info("listener_sweep_complete", new=new_count, by_source=counts)
    return {"new_signals": new_count, "by_source": counts, "total_fetched": len(signals)}


def get_top_signals(
    session: Session,
    since_days: int = 7,
    min_relevance: float = 0.0,
    limit: int = 50,
) -> list[MediaSignal]:
    """Get top signals sorted by combined relevance + trend score."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)

    rows = session.execute(
        select(MediaSignal)
        .where(
            MediaSignal.captured_at >= cutoff,
            MediaSignal.relevance_score >= min_relevance,
        )
        .order_by(
            (MediaSignal.relevance_score + MediaSignal.trending_score).desc()
        )
        .limit(limit)
    ).scalars().all()

    return list(rows)


def promote_signals_to_keywords(
    session: Session,
    min_relevance: float = 0.7,
    min_trend: float = 0.6,
) -> dict[str, Any]:
    """Promote high-scoring signals to keyword_candidates.

    Signals above both thresholds get their extracted topic added as a
    seed keyword candidate, closing the loop back to the keyword researcher.
    """
    signals = session.execute(
        select(MediaSignal)
        .where(
            MediaSignal.relevance_score >= min_relevance,
            MediaSignal.trending_score >= min_trend,
            MediaSignal.status == "new",
        )
        .order_by(
            (MediaSignal.relevance_score + MediaSignal.trending_score).desc()
        )
    ).scalars().all()

    promoted = 0
    for signal in signals:
        # Extract topic from title
        classification = classify_signal(RawSignal(
            source_type=signal.source_type,
            source_name=signal.source_name or "",
            title=signal.title or "",
            url=signal.url or "",
            text=signal.captured_text or "",
        ))
        topic = classification["topic"]

        if not topic or len(topic) < 3:
            continue

        # Check if keyword already exists
        existing = session.execute(
            select(KeywordCandidate).where(KeywordCandidate.keyword == topic)
        ).scalar_one_or_none()

        if not existing:
            session.add(KeywordCandidate(
                keyword=topic,
                source=f"media_{signal.source_type}",
                status="new",
            ))
            promoted += 1

        signal.status = "promoted"

    session.commit()
    log.info("signals_promoted", promoted=promoted, eligible=len(signals))
    return {"promoted": promoted, "eligible": len(signals)}


def add_source(
    source_type: str,
    name: str,
    identifier: str,
    config_path: str | None = None,
) -> None:
    """Add a source to media_sources.yaml."""
    import yaml

    path = config_path or "config/media_sources.yaml"
    config = load_media_config(path)

    if source_type == "youtube":
        channels = config.setdefault("youtube", {}).setdefault("channels", [])
        channels.append({"name": name, "id": identifier})
    elif source_type == "reddit":
        subs = config.setdefault("reddit", {}).setdefault("subreddits", [])
        if identifier not in subs:
            subs.append(identifier)
    elif source_type == "rss":
        feeds = config.setdefault("rss", {}).setdefault("feeds", [])
        feeds.append({"name": name, "url": identifier})
    else:
        raise ValueError(f"Unknown source type: {source_type}")

    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    log.info("source_added", type=source_type, name=name)


def list_sources(config_path: str | None = None) -> dict[str, list[dict[str, str]]]:
    """List all configured media sources."""
    config = load_media_config(config_path)
    sources: dict[str, list[dict[str, str]]] = {}

    for ch in config.get("youtube", {}).get("channels", []):
        sources.setdefault("youtube", []).append(
            {"name": ch.get("name", ""), "id": ch.get("id", "")}
        )
    for sub in config.get("reddit", {}).get("subreddits", []):
        sources.setdefault("reddit", []).append({"name": f"r/{sub}", "id": sub})
    for feed in config.get("rss", {}).get("feeds", []):
        sources.setdefault("rss", []).append(
            {"name": feed.get("name", ""), "id": feed.get("url", "")}
        )

    trends_cat = config.get("trends", {}).get("category")
    if trends_cat:
        sources["trends"] = [{"name": "Google Trends", "id": f"cat={trends_cat}"}]

    return sources
