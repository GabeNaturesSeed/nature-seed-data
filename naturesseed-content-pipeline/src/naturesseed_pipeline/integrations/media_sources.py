"""Media source integrations: YouTube, Reddit, RSS, Google Trends.

Each source returns a list of RawSignal dicts that the media listener agent
classifies and stores as media_signals rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
import yaml

from naturesseed_pipeline.config import settings

log = structlog.get_logger()


@dataclass
class RawSignal:
    """Raw signal from any media source before classification."""

    source_type: str  # youtube, reddit, rss, trends
    source_name: str
    title: str
    url: str
    text: str  # description, selftext, summary, etc.
    published_at: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def load_media_config(path: str | None = None) -> dict[str, Any]:
    """Load media_sources.yaml config."""
    config_path = Path(path or settings.media_sources_config)
    if not config_path.exists():
        log.warning("media_config_not_found", path=str(config_path))
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


# ── YouTube ───────────────────────────────────────────────────────────────────

def fetch_youtube(config: dict[str, Any] | None = None, max_per_channel: int = 10) -> list[RawSignal]:
    """Pull latest uploads from configured YouTube channels via Data API v3."""
    if not settings.youtube_api_key:
        log.warning("youtube_api_key_missing")
        return []

    try:
        from googleapiclient.discovery import build
    except ImportError:
        log.warning("googleapiclient_not_installed")
        return []

    if config is None:
        config = load_media_config()

    channels = config.get("youtube", {}).get("channels", [])
    if not channels:
        return []

    signals: list[RawSignal] = []
    try:
        youtube = build("youtube", "v3", developerKey=settings.youtube_api_key)

        for ch in channels:
            ch_id = ch.get("id", "")
            ch_name = ch.get("name", ch_id)
            if not ch_id:
                continue

            try:
                response = (
                    youtube.search()
                    .list(
                        channelId=ch_id,
                        part="snippet",
                        order="date",
                        maxResults=max_per_channel,
                        type="video",
                    )
                    .execute()
                )

                for item in response.get("items", []):
                    snippet = item.get("snippet", {})
                    video_id = item.get("id", {}).get("videoId", "")
                    signals.append(RawSignal(
                        source_type="youtube",
                        source_name=ch_name,
                        title=snippet.get("title", ""),
                        url=f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
                        text=snippet.get("description", ""),
                        published_at=_parse_iso(snippet.get("publishedAt")),
                        extra={"channel_id": ch_id, "video_id": video_id},
                    ))
            except Exception as e:
                log.warning("youtube_channel_failed", channel=ch_name, error=str(e))

    except Exception as e:
        log.error("youtube_api_failed", error=str(e))

    log.info("youtube_fetch_complete", signals=len(signals))
    return signals


# ── Reddit ────────────────────────────────────────────────────────────────────

def fetch_reddit(config: dict[str, Any] | None = None, limit: int = 25) -> list[RawSignal]:
    """Pull latest posts from configured subreddits via PRAW."""
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        log.warning("reddit_credentials_missing")
        return []

    try:
        import praw
    except ImportError:
        log.warning("praw_not_installed")
        return []

    if config is None:
        config = load_media_config()

    subreddits = config.get("reddit", {}).get("subreddits", [])
    if not subreddits:
        return []

    signals: list[RawSignal] = []
    try:
        reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )

        for sub_name in subreddits:
            try:
                subreddit = reddit.subreddit(sub_name)
                for post in subreddit.hot(limit=limit):
                    signals.append(RawSignal(
                        source_type="reddit",
                        source_name=f"r/{sub_name}",
                        title=post.title,
                        url=f"https://reddit.com{post.permalink}",
                        text=post.selftext[:2000] if post.selftext else "",
                        published_at=datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                        extra={
                            "score": post.score,
                            "num_comments": post.num_comments,
                            "upvote_ratio": post.upvote_ratio,
                        },
                    ))
            except Exception as e:
                log.warning("reddit_sub_failed", subreddit=sub_name, error=str(e))

    except Exception as e:
        log.error("reddit_api_failed", error=str(e))

    log.info("reddit_fetch_complete", signals=len(signals))
    return signals


# ── RSS ───────────────────────────────────────────────────────────────────────

def fetch_rss(config: dict[str, Any] | None = None) -> list[RawSignal]:
    """Pull latest entries from configured RSS feeds."""
    try:
        import feedparser
    except ImportError:
        log.warning("feedparser_not_installed")
        return []

    if config is None:
        config = load_media_config()

    feeds = config.get("rss", {}).get("feeds", [])
    if not feeds:
        return []

    signals: list[RawSignal] = []
    for feed_info in feeds:
        feed_url = feed_info.get("url", "")
        feed_name = feed_info.get("name", feed_url)
        if not feed_url:
            continue

        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:20]:
                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    from time import mktime
                    pub_date = datetime.fromtimestamp(
                        mktime(entry.published_parsed), tz=timezone.utc
                    )

                summary = entry.get("summary", "")
                # Strip HTML from summary
                try:
                    from bs4 import BeautifulSoup
                    summary = BeautifulSoup(summary, "html.parser").get_text(
                        separator=" ", strip=True
                    )
                except Exception:
                    pass

                signals.append(RawSignal(
                    source_type="rss",
                    source_name=feed_name,
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    text=summary[:2000],
                    published_at=pub_date,
                ))
        except Exception as e:
            log.warning("rss_feed_failed", feed=feed_name, error=str(e))

    log.info("rss_fetch_complete", signals=len(signals))
    return signals


# ── Google Trends ─────────────────────────────────────────────────────────────

def fetch_trends(config: dict[str, Any] | None = None) -> list[RawSignal]:
    """Pull rising queries from Google Trends in Home & Garden category.

    Uses pytrends — wraps in try/except because pytrends breaks periodically.
    Failure is non-fatal.
    """
    if config is None:
        config = load_media_config()

    trends_config = config.get("trends", {})
    category = trends_config.get("category", 11)  # Home & Garden
    geo = trends_config.get("geo", "US")

    signals: list[RawSignal] = []
    try:
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl="en-US", tz=360)
        trending = pytrends.trending_searches(pn="united_states")

        # Also get real-time trending for the category
        try:
            pytrends.build_payload(
                kw_list=["gardening"],
                cat=category,
                timeframe="now 7-d",
                geo=geo,
            )
            related = pytrends.related_queries()
            rising = related.get("gardening", {}).get("rising")
            if rising is not None and not rising.empty:
                for _, row in rising.iterrows():
                    query = row.get("query", "")
                    signals.append(RawSignal(
                        source_type="trends",
                        source_name="Google Trends Rising",
                        title=query,
                        url=f"https://trends.google.com/trends/explore?q={query.replace(' ', '+')}",
                        text=f"Rising query in Home & Garden: {query}",
                        extra={"value": str(row.get("value", ""))},
                    ))
        except Exception as e:
            log.warning("trends_related_failed", error=str(e))

    except Exception as e:
        log.warning("trends_fetch_failed", error=str(e))

    log.info("trends_fetch_complete", signals=len(signals))
    return signals


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_all(config: dict[str, Any] | None = None) -> list[RawSignal]:
    """Fetch signals from all configured sources."""
    if config is None:
        config = load_media_config()
    signals: list[RawSignal] = []
    signals.extend(fetch_youtube(config))
    signals.extend(fetch_reddit(config))
    signals.extend(fetch_rss(config))
    signals.extend(fetch_trends(config))
    log.info("all_sources_complete", total=len(signals))
    return signals
