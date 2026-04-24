"""Report stage — generates markdown + CSV files under docs/content-audit/YYYY-MM-DD/."""

import csv
from collections import defaultdict
from datetime import date
from io import StringIO
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    ContentInventory, ContentProductMention, ContentTopic,
    DecayFinding, OutboundLink, Topic,
)


def generate_topic_map(session: Session) -> str:
    topics = session.execute(select(Topic)).scalars().all()
    by_parent: dict[int | None, list[Topic]] = defaultdict(list)
    for t in topics:
        by_parent[t.parent_topic_id].append(t)

    topic_articles: dict[int, list[ContentInventory]] = defaultdict(list)
    for ct in session.execute(select(ContentTopic)).scalars().all():
        row = session.get(ContentInventory, ct.content_inventory_id)
        if row:
            topic_articles[ct.topic_id].append(row)

    mentions_by_content: dict[int, list[str]] = defaultdict(list)
    for m in session.execute(select(ContentProductMention)).scalars().all():
        mentions_by_content[m.content_inventory_id].append(m.product_name)

    lines = ["# Topic Map", ""]
    for top in sorted(by_parent[None], key=lambda x: x.name):
        lines.append(f"## {top.name} (`{top.slug}`)")
        subs = sorted(by_parent[top.id], key=lambda x: x.name)
        if subs:
            for sub in subs:
                lines.append(f"### {sub.name} (`{sub.slug}`)")
                for row in sorted(topic_articles[sub.id], key=lambda r: r.title):
                    prods = mentions_by_content.get(row.id, [])
                    prod_str = f" — _products: {', '.join(prods)}_" if prods else ""
                    lines.append(f"- [{row.title}]({row.url}){prod_str}")
        direct = [r for r in topic_articles[top.id]
                  if r.id not in {x.id for sub in subs for x in topic_articles[sub.id]}]
        if direct:
            if not subs:
                lines.append("")
            lines.append("**Articles without subtopic:**")
            for row in sorted(direct, key=lambda r: r.title):
                lines.append(f"- [{row.title}]({row.url})")
        lines.append("")
    return "\n".join(lines)


def _topic_map_csv(session: Session) -> str:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["content_id", "title", "url", "post_type",
                "topic_slug", "subtopic_slug", "product_slug"])

    top_level = {t.id: t for t in session.execute(select(Topic)).scalars().all()
                 if t.parent_topic_id is None}

    assignments = session.execute(select(ContentTopic)).scalars().all()
    by_content: dict[int, list[Topic]] = defaultdict(list)
    for ct in assignments:
        topic = session.get(Topic, ct.topic_id)
        if topic:
            by_content[ct.content_inventory_id].append(topic)

    mentions = session.execute(select(ContentProductMention)).scalars().all()
    prods_by_content: dict[int, list[str]] = defaultdict(list)
    for m in mentions:
        prods_by_content[m.content_inventory_id].append(m.product_slug)

    for row in session.execute(select(ContentInventory)).scalars().all():
        topics = by_content.get(row.id, [])
        tl = next((t for t in topics if t.id in top_level), None)
        sub = next((t for t in topics if t.parent_topic_id is not None), None)
        prods = prods_by_content.get(row.id) or [""]
        for p in prods:
            w.writerow([row.id, row.title, row.url, row.post_type,
                       tl.slug if tl else "",
                       sub.slug if sub else "", p])
    return buf.getvalue()


def generate_per_article(session: Session) -> str:
    findings = defaultdict(list)
    for f in session.execute(select(DecayFinding).where(
        DecayFinding.status == "open"
    )).scalars().all():
        findings[f.content_inventory_id].append(f)

    mentions = defaultdict(list)
    for m in session.execute(select(ContentProductMention)).scalars().all():
        mentions[m.content_inventory_id].append(m.product_name)

    lines = ["# Per-Article Audit", ""]
    for row in session.execute(select(ContentInventory).order_by(ContentInventory.title)).scalars().all():
        lines.append(f"## {row.title}")
        lines.append(f"- URL: {row.url}")
        lines.append(f"- Type: {row.post_type} | Words: {row.word_count or 0}")
        prods = mentions.get(row.id, [])
        if prods:
            lines.append(f"- Products: {', '.join(prods)}")
        flist = findings.get(row.id, [])
        if flist:
            lines.append("- Decay findings:")
            for f in flist:
                lines.append(f"  - **{f.rule_name}** ({f.severity}): {f.suggested_action}")
        lines.append("")
    return "\n".join(lines)


def _per_article_csv(session: Session) -> str:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["content_id", "title", "url", "post_type", "status",
                "word_count", "products_count", "open_findings", "critical_findings"])
    findings = defaultdict(list)
    for f in session.execute(select(DecayFinding).where(DecayFinding.status == "open")).scalars().all():
        findings[f.content_inventory_id].append(f)
    prod_counts = defaultdict(int)
    for m in session.execute(select(ContentProductMention)).scalars().all():
        prod_counts[m.content_inventory_id] += 1
    for row in session.execute(select(ContentInventory)).scalars().all():
        flist = findings.get(row.id, [])
        crit = sum(1 for f in flist if f.severity == "critical")
        w.writerow([row.id, row.title, row.url, row.post_type, row.status,
                   row.word_count or 0, prod_counts[row.id],
                   len(flist), crit])
    return buf.getvalue()


def _decay_findings_csv(session: Session) -> str:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["content_id", "title", "url", "rule_name", "severity",
                "snippet", "suggested_action"])
    for f in session.execute(select(DecayFinding).where(DecayFinding.status == "open")).scalars().all():
        row = session.get(ContentInventory, f.content_inventory_id)
        w.writerow([f.content_inventory_id, row.title if row else "",
                   row.url if row else "",
                   f.rule_name, f.severity,
                   (f.snippet or "")[:300], f.suggested_action or ""])
    return buf.getvalue()


def generate_internal_linking(session: Session) -> str:
    rows = session.execute(select(ContentInventory).order_by(ContentInventory.title)).scalars().all()
    id_to_row = {r.id: r for r in rows}

    outbound = defaultdict(list)
    for link in session.execute(select(OutboundLink).where(
        OutboundLink.link_type.in_(["internal_content", "internal_product"])
    )).scalars().all():
        outbound[link.content_inventory_id].append(link)

    inbound = defaultdict(list)
    for link in session.execute(select(OutboundLink).where(
        OutboundLink.target_content_id.isnot(None)
    )).scalars().all():
        inbound[link.target_content_id].append(link)

    lines = ["# Internal Linking Map", "", "## Outbound links per article", ""]
    for row in rows:
        lines.append(f"### {row.title}")
        for link in outbound.get(row.id, []):
            target = id_to_row.get(link.target_content_id)
            target_desc = target.title if target else link.href
            lines.append(f"- → {target_desc} ({link.href})")
        lines.append("")

    lines += ["", "## Inbound links (what links TO each article)", ""]
    for row in rows:
        incoming = inbound.get(row.id, [])
        if not incoming:
            continue
        lines.append(f"### {row.title}")
        for link in incoming:
            source = id_to_row.get(link.content_inventory_id)
            lines.append(f"- ← {source.title if source else '?'}")
        lines.append("")
    return "\n".join(lines)


def _internal_linking_csv(session: Session) -> str:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["source_content_id", "target_content_id", "anchor_text", "href"])
    for link in session.execute(select(OutboundLink).where(
        OutboundLink.link_type.in_(["internal_content", "internal_product"])
    )).scalars().all():
        w.writerow([link.content_inventory_id, link.target_content_id or "",
                   link.anchor_text or "", link.href])
    return buf.getvalue()


def generate_summary(session: Session) -> str:
    content_count = session.execute(
        select(ContentInventory.id)
    ).scalars().all()
    findings = session.execute(
        select(DecayFinding).where(DecayFinding.status == "open")
    ).scalars().all()
    by_rule: dict[str, int] = defaultdict(int)
    for f in findings:
        by_rule[f.rule_name] += 1

    lines = ["# Audit Summary", ""]
    lines.append(f"- Total articles: {len(content_count)}")
    lines.append(f"- Total open decay findings: {len(findings)}")
    lines.append("")
    lines.append("## Findings by rule")
    for name, count in sorted(by_rule.items(), key=lambda x: -x[1]):
        lines.append(f"- {name}: {count}")
    return "\n".join(lines)


def run_report(session: Session, out_root: Path, date_str: str | None = None) -> Path:
    date_str = date_str or date.today().isoformat()
    out_dir = Path(out_root) / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "topic-map.md").write_text(generate_topic_map(session))
    (out_dir / "topic-map.csv").write_text(_topic_map_csv(session))
    (out_dir / "per-article.md").write_text(generate_per_article(session))
    (out_dir / "per-article.csv").write_text(_per_article_csv(session))
    (out_dir / "decay-findings.csv").write_text(_decay_findings_csv(session))
    (out_dir / "internal-linking.md").write_text(generate_internal_linking(session))
    (out_dir / "internal-linking.csv").write_text(_internal_linking_csv(session))
    (out_dir / "summary.md").write_text(generate_summary(session))
    return out_dir
