from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    Base, ContentInventory, ContentTopic, ContentProductMention,
    DecayFinding, OutboundLink, Topic,
)
from naturesseed_pipeline.pipelines.audit.report import (
    generate_topic_map, generate_per_article, generate_internal_linking,
    generate_summary, run_report,
)


def _seeded_session() -> Session:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    s = Session(eng)
    top = Topic(name="Grass Seed", slug="grass-seed", source="wc_category", approved=1)
    s.add(top); s.flush()
    sub = Topic(name="Cool-Season", slug="cool-season", parent_topic_id=top.id,
               source="llm_proposed", approved=1)
    s.add(sub); s.flush()

    a1 = ContentInventory(wp_post_id=1, url="https://naturesseed.com/a/",
                         title="Article A", slug="a", post_type="post",
                         word_count=500, status="publish")
    a2 = ContentInventory(wp_post_id=2, url="https://naturesseed.com/b/",
                         title="Article B", slug="b", post_type="post",
                         word_count=200, status="publish")
    s.add_all([a1, a2]); s.flush()
    s.add_all([
        ContentTopic(content_inventory_id=a1.id, topic_id=top.id,
                    assigned_by="auto", confidence=1.0),
        ContentTopic(content_inventory_id=a1.id, topic_id=sub.id,
                    assigned_by="auto", confidence=0.8),
        ContentTopic(content_inventory_id=a2.id, topic_id=top.id,
                    assigned_by="auto", confidence=1.0),
    ])
    s.add(ContentProductMention(content_inventory_id=a1.id, wp_product_id=1,
                               product_slug="foo", product_name="Foo",
                               match_type="exact", confidence=0.9))
    s.add(DecayFinding(content_inventory_id=a2.id, rule_name="ThinContentRule",
                      severity="info", snippet="word_count=200",
                      suggested_action="expand", status="open"))
    s.add(OutboundLink(content_inventory_id=a1.id,
                      href="https://naturesseed.com/b/",
                      anchor_text="B", link_type="internal_content",
                      target_content_id=a2.id))
    s.commit()
    return s


def test_topic_map_contains_topics_and_articles():
    s = _seeded_session()
    md = generate_topic_map(s)
    assert "Grass Seed" in md
    assert "Cool-Season" in md
    assert "Article A" in md and "Article B" in md


def test_per_article_lists_findings_and_products():
    s = _seeded_session()
    md = generate_per_article(s)
    assert "Foo" in md
    assert "ThinContentRule" in md


def test_internal_linking_shows_edges():
    s = _seeded_session()
    md = generate_internal_linking(s)
    assert "Article A" in md and "Article B" in md


def test_summary_counts_present():
    s = _seeded_session()
    md = generate_summary(s)
    assert "Articles" in md or "articles" in md


def test_run_report_writes_all_files(tmp_path: Path):
    s = _seeded_session()
    out_dir = run_report(s, out_root=tmp_path, date_str="2026-04-24")
    dirlist = list(p.name for p in out_dir.iterdir())
    expected = {
        "topic-map.md", "topic-map.csv",
        "per-article.md", "per-article.csv",
        "decay-findings.csv", "internal-linking.md",
        "internal-linking.csv", "summary.md",
    }
    assert expected.issubset(set(dirlist))
