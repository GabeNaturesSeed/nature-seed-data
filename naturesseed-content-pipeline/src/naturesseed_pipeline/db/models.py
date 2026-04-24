"""SQLAlchemy ORM models for the content pipeline."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class ContentInventory(Base):
    __tablename__ = "content_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wp_post_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text)
    content_text: Mapped[str | None] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text)
    post_type: Mapped[str] = mapped_column(String(50), nullable=False, default="post")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="publish")
    categories: Mapped[dict | None] = mapped_column(JSON)
    tags: Mapped[dict | None] = mapped_column(JSON)
    word_count: Mapped[int | None] = mapped_column(Integer)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    modified_at: Mapped[datetime | None] = mapped_column(DateTime)
    target_keyword: Mapped[str | None] = mapped_column(String(300))
    performance_metrics: Mapped[dict | None] = mapped_column(JSON)
    last_audited_at: Mapped[datetime | None] = mapped_column(DateTime)

    metrics: Mapped[list["PerformanceMetric"]] = relationship(back_populates="content")
    orphan_refs: Mapped[list["OrphanReference"]] = relationship(back_populates="content")


class KeywordCandidate(Base):
    __tablename__ = "keyword_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    search_volume: Mapped[int | None] = mapped_column(Integer)
    keyword_difficulty: Mapped[float | None] = mapped_column(Float)
    difficulty_source: Mapped[str | None] = mapped_column(String(50))
    intent: Mapped[str | None] = mapped_column(String(50))
    seasonality: Mapped[dict | None] = mapped_column(JSON)
    source: Mapped[str | None] = mapped_column(String(100))
    related_keywords: Mapped[dict | None] = mapped_column(JSON)
    serp_features: Mapped[dict | None] = mapped_column(JSON)
    gap_score: Mapped[float | None] = mapped_column(Float)
    best_ranking_url: Mapped[str | None] = mapped_column(String(500))
    best_ranking_position: Mapped[float | None] = mapped_column(Float)
    competition_index: Mapped[float | None] = mapped_column(Float)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    priority_score: Mapped[float | None] = mapped_column(Float)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")


class GscQueryPerformance(Base):
    __tablename__ = "gsc_query_performance"
    __table_args__ = (
        UniqueConstraint("query", "page", "date", "device", "country", name="uq_gsc_row"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    page: Mapped[str] = mapped_column(String(500), nullable=False)
    date: Mapped[str] = mapped_column(String(10), nullable=False)
    device: Mapped[str] = mapped_column(String(20), nullable=False, default="DESKTOP")
    country: Mapped[str] = mapped_column(String(10), nullable=False, default="USA")
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class CompetitorDomain(Base):
    __tablename__ = "competitor_domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="ads_auction")
    discovered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    keyword_overlap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime)


class MediaSignal(Base):
    __tablename__ = "media_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(200))
    title: Mapped[str | None] = mapped_column(String(500))
    url: Mapped[str | None] = mapped_column(String(500))
    captured_text: Mapped[str | None] = mapped_column(Text)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    trending_score: Mapped[float | None] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")


class BriefQueue(Base):
    __tablename__ = "brief_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword_candidate_id: Mapped[int | None] = mapped_column(
        ForeignKey("keyword_candidates.id")
    )
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    target_keyword: Mapped[str | None] = mapped_column(String(300))
    brief_json: Mapped[dict | None] = mapped_column(JSON)
    priority_score: Mapped[float | None] = mapped_column(Float)
    is_refresh: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    original_wp_post_id: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)

    drafts: Mapped[list["Draft"]] = relationship(back_populates="brief")


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brief_id: Mapped[int] = mapped_column(ForeignKey("brief_queue.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_markdown: Mapped[str | None] = mapped_column(Text)
    citations: Mapped[dict | None] = mapped_column(JSON)
    fact_check_notes: Mapped[dict | None] = mapped_column(JSON)
    editorial_notes: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)

    image_assignments: Mapped[dict | None] = mapped_column(JSON)
    meta_description: Mapped[str | None] = mapped_column(String(320))
    reviewer_notes: Mapped[str | None] = mapped_column(Text)

    brief: Mapped["BriefQueue"] = relationship(back_populates="drafts")
    publish_items: Mapped[list["PublishQueue"]] = relationship(back_populates="draft")


class PublishQueue(Base):
    __tablename__ = "publish_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), nullable=False)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime)
    wp_post_id: Mapped[int | None] = mapped_column(Integer)
    publish_status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    published_at: Mapped[datetime | None] = mapped_column(DateTime)

    draft: Mapped["Draft"] = relationship(back_populates="publish_items")


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_inventory_id: Mapped[int] = mapped_column(
        ForeignKey("content_inventory.id"), nullable=False
    )
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    impressions: Mapped[int | None] = mapped_column(Integer)
    clicks: Mapped[int | None] = mapped_column(Integer)
    avg_position: Mapped[float | None] = mapped_column(Float)
    conversions: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(50), nullable=False)

    content: Mapped["ContentInventory"] = relationship(back_populates="metrics")


class OrphanReference(Base):
    __tablename__ = "orphan_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_inventory_id: Mapped[int] = mapped_column(
        ForeignKey("content_inventory.id"), nullable=False
    )
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_value: Mapped[str] = mapped_column(String(500), nullable=False)
    matched_inactive_product_id: Mapped[int | None] = mapped_column(Integer)
    match_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    snippet: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="flagged")
    user_decision_at: Mapped[datetime | None] = mapped_column(DateTime)
    user_notes: Mapped[str | None] = mapped_column(Text)
    redirect_target_url: Mapped[str | None] = mapped_column(String(500))

    content: Mapped["ContentInventory"] = relationship(back_populates="orphan_refs")


class RefreshQueue(Base):
    __tablename__ = "refresh_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_inventory_id: Mapped[int] = mapped_column(
        ForeignKey("content_inventory.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    orphan_reference_id: Mapped[int | None] = mapped_column(
        ForeignKey("orphan_references.id")
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Redirect(Base):
    __tablename__ = "redirects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    target_url: Mapped[str] = mapped_column(String(500), nullable=False)
    orphan_reference_id: Mapped[int | None] = mapped_column(
        ForeignKey("orphan_references.id")
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    applied_at: Mapped[datetime | None] = mapped_column(DateTime)


class MediaIndex(Base):
    __tablename__ = "media_index"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wp_media_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    alt_text: Mapped[str | None] = mapped_column(String(500))
    caption: Mapped[str | None] = mapped_column(Text)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(50))
    description_text: Mapped[str | None] = mapped_column(Text)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RefreshHistory(Base):
    __tablename__ = "refresh_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_inventory_id: Mapped[int] = mapped_column(
        ForeignKey("content_inventory.id"), nullable=False
    )
    wp_post_id: Mapped[int] = mapped_column(Integer, nullable=False)
    brief_id: Mapped[int | None] = mapped_column(ForeignKey("brief_queue.id"))
    draft_id: Mapped[int | None] = mapped_column(ForeignKey("drafts.id"))
    changes_summary: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    wc_category_slug: Mapped[str | None] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    approved: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    keywords: Mapped[list | None] = mapped_column(JSON)


class ContentTopic(Base):
    __tablename__ = "content_topics"
    __table_args__ = (
        UniqueConstraint("content_inventory_id", "topic_id", name="uq_content_topic"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_inventory_id: Mapped[int] = mapped_column(
        ForeignKey("content_inventory.id"), nullable=False
    )
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    assigned_by: Mapped[str] = mapped_column(String(20), nullable=False)


class ContentProductMention(Base):
    __tablename__ = "content_product_mentions"
    __table_args__ = (
        UniqueConstraint("content_inventory_id", "wp_product_id",
                         name="uq_content_product_mention"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_inventory_id: Mapped[int] = mapped_column(
        ForeignKey("content_inventory.id"), nullable=False
    )
    wp_product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_slug: Mapped[str] = mapped_column(String(300), nullable=False)
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_snippet: Mapped[str | None] = mapped_column(Text)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class OutboundLink(Base):
    __tablename__ = "outbound_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_inventory_id: Mapped[int] = mapped_column(
        ForeignKey("content_inventory.id"), nullable=False, index=True
    )
    href: Mapped[str] = mapped_column(String(2000), nullable=False)
    anchor_text: Mapped[str | None] = mapped_column(String(500))
    link_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_content_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_inventory.id"), index=True
    )
    http_status: Mapped[int | None] = mapped_column(Integer)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)


class DecayFinding(Base):
    __tablename__ = "decay_findings"
    __table_args__ = (
        Index("ix_decay_content_status", "content_inventory_id", "status"),
        Index("ix_decay_rule_status", "rule_name", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_inventory_id: Mapped[int] = mapped_column(
        ForeignKey("content_inventory.id"), nullable=False
    )
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    snippet: Mapped[str | None] = mapped_column(Text)
    suggested_action: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    detected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)


class WcCatalogSnapshot(Base):
    __tablename__ = "wc_catalog_snapshot"

    wp_product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    species_list: Mapped[list | None] = mapped_column(JSON)
    price: Mapped[float | None] = mapped_column(Float)
    permalink: Mapped[str | None] = mapped_column(String(500))
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
