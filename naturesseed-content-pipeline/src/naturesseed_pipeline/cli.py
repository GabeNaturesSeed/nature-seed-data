"""CLI entry point — typer app exposed as `nspipe`."""

import csv
import sys
from datetime import datetime, timezone
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from naturesseed_pipeline.logging_config import setup_logging

app = typer.Typer(
    name="nspipe",
    help="Nature's Seed Content Pipeline — agentic content engine.",
    no_args_is_help=True,
)
console = Console()


# ── Command groups ────────────────────────────────────────────────────────────

db_app = typer.Typer(help="Database operations.")
app.add_typer(db_app, name="db")

audit_app = typer.Typer(help="Content audit and inventory sync.")
app.add_typer(audit_app, name="audit")

orphans_app = typer.Typer(help="Orphan product reference management.")
audit_app.add_typer(orphans_app, name="orphans")

research_app = typer.Typer(help="Keyword research and media signal capture.")
app.add_typer(research_app, name="research")

kw_app = typer.Typer(help="Keyword research operations.")
research_app.add_typer(kw_app, name="keywords")

competitors_app = typer.Typer(help="Competitor domain intelligence.")
kw_app.add_typer(competitors_app, name="competitors")

media_app = typer.Typer(help="Media listening and signal capture.")
research_app.add_typer(media_app, name="media")

media_sources_app = typer.Typer(help="Manage media sources.")
media_app.add_typer(media_sources_app, name="sources")

brief_app = typer.Typer(help="Content brief scoring, generation, and review.")
app.add_typer(brief_app, name="brief")

write_app = typer.Typer(help="Draft writing from approved briefs.")
app.add_typer(write_app, name="write")

review_app = typer.Typer(help="Supervisor review of drafts.")
app.add_typer(review_app, name="review")

images_app = typer.Typer(help="Image selection, generation, and optimization.")
app.add_typer(images_app, name="images")

publish_app = typer.Typer(help="Review, schedule, and publish to WordPress.")
app.add_typer(publish_app, name="publish")


# ── DB commands ───────────────────────────────────────────────────────────────

@db_app.command("init")
def db_init() -> None:
    """Create all tables (dev shortcut — use migrations in prod)."""
    from naturesseed_pipeline.db.models import Base
    from naturesseed_pipeline.db.session import engine

    Base.metadata.create_all(engine)
    typer.echo("Database initialized.")


@db_app.command("migrate")
def db_migrate(message: str = typer.Option("auto", "-m", help="Migration message")) -> None:
    """Generate an Alembic migration."""
    import subprocess

    subprocess.run(["alembic", "revision", "--autogenerate", "-m", message], check=True)
    typer.echo("Migration created.")


@db_app.command("upgrade")
def db_upgrade() -> None:
    """Run Alembic migrations to head."""
    import subprocess

    subprocess.run(["alembic", "upgrade", "head"], check=True)
    typer.echo("Database upgraded.")


# ── Audit commands ────────────────────────────────────────────────────────────

@audit_app.command("sync")
def audit_sync_cmd(
    since: Optional[str] = typer.Option(None, "--since", help="Incremental YYYY-MM-DD"),
) -> None:
    """Pull posts + pages + products into content_inventory and wc_catalog_snapshot."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.audit.sync import run_sync
    session = SessionLocal()
    try:
        counts = run_sync(session, since=since)
        session.commit()
        console.print(f"[bold]Sync complete[/bold] — {counts}")
    finally:
        session.close()


@audit_app.command("classify")
def audit_classify_cmd(
    export_proposals: Optional[str] = typer.Option(
        None, "--export-proposals",
        help="Dump pending subtopic proposals to a markdown file at the given path"),
    import_approvals: Optional[str] = typer.Option(
        None, "--import-approvals",
        help="Read an edited markdown file and apply approvals / rejections"),
    approve_all: bool = typer.Option(
        False, "--approve-all",
        help="Non-interactive: approve every pending subtopic without review"),
    reclassify: bool = typer.Option(
        False, "--reclassify",
        help="Re-run the full classify pipeline (seed + pass1 + pass2 + pass4)"),
) -> None:
    """Four-pass classify: seed + pass 1 deterministic + pass 2 LLM proposal + pass 4 subtopic match.

    Subtopic approval is a markdown-file workflow: run --export-proposals to write a review
    file, edit it (delete sections to reject, edit names/keywords to refine), then run
    --import-approvals to apply your edits. Use --approve-all for non-interactive approval.
    """
    from pathlib import Path
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.integrations.wordpress import WooCommerceClient
    from naturesseed_pipeline.pipelines.audit.classify import (
        seed_topics_from_wc_categories, run_classify_pass1, run_classify_pass2,
        run_classify_pass4, approve_all_subtopics, AnthropicSubtopicProposer,
        export_pending_subtopics_to_markdown, import_subtopic_approvals_from_markdown,
    )

    session = SessionLocal()
    try:
        if export_proposals:
            n = export_pending_subtopics_to_markdown(session, Path(export_proposals))
            console.print(f"Wrote {n} pending subtopic(s) to [bold]{export_proposals}[/bold]")
            console.print("Review the file, then run: "
                          f"[bold]nspipe audit classify --import-approvals {export_proposals}[/bold]")
            return

        if import_approvals:
            counts = import_subtopic_approvals_from_markdown(session, Path(import_approvals))
            session.commit()
            console.print(f"[bold]Approvals imported[/bold] — {counts}")
            console.print("Re-run [bold]nspipe audit classify[/bold] to run Pass 4 with the approved subtopics.")
            return

        if approve_all:
            n = approve_all_subtopics(session); session.commit()
            console.print(f"Approved {n} subtopic(s).")
            return

        # Full classify: seed + pass1 + pass2 + pass4 (pass4 skips non-approved anyway)
        wc = WooCommerceClient()
        try:
            cats = wc._paginate("products/categories") or []
        finally:
            wc.close()
        added = seed_topics_from_wc_categories(session, cats)
        cat_map = {int(c["id"]): c.get("slug", "") for c in cats if c.get("id")}
        assigned = run_classify_pass1(session, wp_cat_id_to_slug=cat_map)
        try:
            proposed = run_classify_pass2(session, proposer=AnthropicSubtopicProposer())
        except Exception as e:
            proposed = 0
            console.print(f"[yellow]Pass 2 (LLM subtopic proposal) skipped: {e}[/yellow]")
        sub_assigned = run_classify_pass4(session)
        session.commit()
        console.print(f"Topics added: {added}, top-level assignments: {assigned}, "
                      f"LLM proposals: {proposed}, subtopic assignments: {sub_assigned}")
        if proposed:
            console.print("\nReview subtopic proposals:\n"
                          "  [bold]nspipe audit classify --export-proposals docs/content-audit/subtopic-proposals.md[/bold]")
    finally:
        session.close()


@audit_app.command("tag-products")
def audit_tag_products_cmd() -> None:
    """Tag articles with active + inactive product + species mentions."""
    from naturesseed_pipeline.config import settings
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.audit.tag_products import run_tag_products
    session = SessionLocal()
    try:
        counts = run_tag_products(session, fuzzy_threshold=settings.audit_fuzzy_match_threshold)
        session.commit()
        console.print(f"[bold]Tag products complete[/bold] — {counts}")
    finally:
        session.close()


@audit_app.command("scan-links")
def audit_scan_links_cmd(
    skip_http: bool = typer.Option(False, "--skip-http", help="Extract only, no HTTP checks"),
    recheck_all: bool = typer.Option(False, "--recheck-all", help="Ignore 30-day cache"),
) -> None:
    """Extract outbound links + HTTP-check them."""
    from urllib.parse import urlparse
    from naturesseed_pipeline.config import settings
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.audit.scan_links import run_scan_links
    session = SessionLocal()
    try:
        site_host = urlparse(settings.wc_base_url).netloc
        cache_days = 0 if recheck_all else settings.audit_http_check_cache_days
        counts = run_scan_links(session, site_host=site_host, cache_days=cache_days,
                                skip_http=skip_http)
        session.commit()
        console.print(f"[bold]Scan links complete[/bold] — {counts}")
    finally:
        session.close()


@audit_app.command("scan-decay")
def audit_scan_decay_cmd(
    rule: Optional[str] = typer.Option(None, "--rule", help="Run only a single rule"),
    article: Optional[int] = typer.Option(None, "--article", help="Run against a single article id"),
) -> None:
    """Run all decay rules, reconcile findings, rebuild refresh_queue."""
    from naturesseed_pipeline.audit_rules import discover_rules
    from naturesseed_pipeline.config import settings
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.audit.llm import CliClaudeClient
    from naturesseed_pipeline.pipelines.audit.scan_decay import run_scan_decay
    session = SessionLocal()
    try:
        rules = discover_rules()
        # Route LLM calls through `claude -p` (Max-plan auth) instead of API.
        try:
            llm_client = CliClaudeClient()
        except RuntimeError as e:
            console.print(f"[yellow]LLM-assisted rules disabled: {e}[/yellow]")
            llm_client = None
        counts = run_scan_decay(
            session, rules=rules,
            current_shipping=settings.audit_current_shipping,
            llm_client=llm_client, llm_model=settings.audit_llm_model,
            llm_token_budget=settings.audit_llm_max_tokens_per_rule,
            only_article_id=article, only_rule_name=rule,
        )
        session.commit()
        console.print(f"[bold]Scan decay complete[/bold] — {counts}")
    finally:
        session.close()


@audit_app.command("report")
def audit_report_v2_cmd(
    out_dir: str = typer.Option("docs/content-audit",
                                 "--out", help="Report output root"),
) -> None:
    """Generate markdown + CSV reports (new 6-stage pipeline version)."""
    from pathlib import Path
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.audit.report import run_report
    session = SessionLocal()
    try:
        out = run_report(session, out_root=Path(out_dir))
        console.print(f"[bold]Reports written to {out}[/bold]")
    finally:
        session.close()


# ── Orphan subcommands ────────────────────────────────────────────────────────

@orphans_app.command("list")
def orphans_list() -> None:
    """List flagged orphan references grouped by content."""
    from sqlalchemy import select

    from naturesseed_pipeline.db.models import ContentInventory, OrphanReference
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        refs = session.execute(
            select(OrphanReference)
            .where(OrphanReference.status == "flagged")
            .order_by(OrphanReference.content_inventory_id)
        ).scalars().all()

        if not refs:
            console.print("No flagged orphan references.")
            return

        # Group by content
        grouped: dict[int, list] = {}
        for ref in refs:
            grouped.setdefault(ref.content_inventory_id, []).append(ref)

        for cid, group in grouped.items():
            content = session.get(ContentInventory, cid)
            if not content:
                continue
            console.print()
            console.print(f"[bold]{content.title}[/bold]")
            console.print(f"  URL: {content.url}")
            console.print(f"  Type: {content.post_type} | Status: {content.status}")
            for ref in group:
                color = "red" if ref.match_confidence >= 0.95 else "yellow"
                console.print(
                    f"  [{color}][{ref.reference_type}][/{color}] "
                    f"{ref.reference_value} "
                    f"(confidence: {ref.match_confidence:.0%})"
                )
                if ref.snippet:
                    console.print(f"    > {ref.snippet}")

        console.print()
        console.print(f"Total: {len(refs)} flags across {len(grouped)} content items")
    finally:
        session.close()


@orphans_app.command("review")
def orphans_review() -> None:
    """Interactive review of flagged orphan references."""
    from rapidfuzz import fuzz as rfuzz
    from sqlalchemy import select

    from naturesseed_pipeline.db.models import (
        ContentInventory,
        OrphanReference,
        Redirect,
        RefreshQueue,
    )
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.integrations.wordpress import WordPressClient

    session = SessionLocal()
    try:
        refs = session.execute(
            select(OrphanReference)
            .where(OrphanReference.status == "flagged")
            .order_by(OrphanReference.content_inventory_id, OrphanReference.id)
        ).scalars().all()

        if not refs:
            console.print("No flagged orphan references to review.")
            return

        total = len(refs)
        console.print(f"[bold]{total} orphan references to review[/bold]")
        console.print("[k]eep  [u]pdate  [a]rchive  [r]edirect  [s]kip")
        console.print()

        wp_client = None  # lazy init only if archive is needed

        for i, ref in enumerate(refs, 1):
            content = session.get(ContentInventory, ref.content_inventory_id)
            if not content:
                continue

            console.print(f"[bold]--- {i}/{total} ---[/bold]")
            console.print(f"[bold]{content.title}[/bold]  ({content.post_type})")
            console.print(f"URL: {content.url}")
            console.print()

            color = "red" if ref.match_confidence >= 0.95 else "yellow"
            console.print(
                f"  Reference: [{color}][{ref.reference_type}][/{color}] "
                f"{ref.reference_value}"
            )
            console.print(f"  Confidence: {ref.match_confidence:.0%}")
            if ref.matched_inactive_product_id:
                console.print(f"  Matched inactive product ID: {ref.matched_inactive_product_id}")
            if ref.snippet:
                console.print(f"  Snippet: {ref.snippet}")
            console.print()

            choice = ""
            while choice not in ("k", "u", "a", "r", "s"):
                choice = input("  [k]eep [u]pdate [a]rchive [r]edirect [s]kip > ").strip().lower()

            now = datetime.now(timezone.utc)

            if choice == "k":
                ref.status = "kept"
                ref.user_decision_at = now
                notes = input("  Notes (optional): ").strip()
                if notes:
                    ref.user_notes = notes

            elif choice == "u":
                ref.status = "update_requested"
                ref.user_decision_at = now
                reason = input("  Reason for refresh: ").strip() or "Orphan product reference"
                session.add(RefreshQueue(
                    content_inventory_id=ref.content_inventory_id,
                    reason=reason,
                    orphan_reference_id=ref.id,
                ))

            elif choice == "a":
                confirm = input(
                    f"  Set '{content.title}' to DRAFT status? [y/N] "
                ).strip().lower()
                if confirm == "y" and content.wp_post_id:
                    if wp_client is None:
                        wp_client = WordPressClient()
                    try:
                        wp_client.update_post_status(content.wp_post_id, "draft")
                        console.print("  [green]Archived (set to draft)[/green]")
                    except Exception as e:
                        console.print(f"  [red]Failed to archive: {e}[/red]")
                ref.status = "archived"
                ref.user_decision_at = now

            elif choice == "r":
                target = input("  Redirect target URL: ").strip()
                if not target:
                    console.print("  Skipped — no URL provided.")
                    continue
                ref.status = "redirected"
                ref.user_decision_at = now
                ref.redirect_target_url = target
                session.add(Redirect(
                    source_url=content.url,
                    target_url=target,
                    orphan_reference_id=ref.id,
                ))

            else:  # skip
                pass

            session.commit()
            console.print()

        if wp_client:
            wp_client.close()
        console.print("[bold]Review complete.[/bold]")
    finally:
        session.close()


@orphans_app.command("export")
def orphans_export(
    output: str = typer.Option("orphan_references.csv", "-o", help="Output CSV path"),
) -> None:
    """Export flagged orphan references to CSV."""
    from sqlalchemy import select

    from naturesseed_pipeline.db.models import ContentInventory, OrphanReference
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        refs = session.execute(
            select(OrphanReference).order_by(OrphanReference.content_inventory_id)
        ).scalars().all()

        with open(output, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "content_title", "content_url", "content_type", "reference_type",
                "reference_value", "matched_product_id", "confidence", "snippet",
                "status", "user_notes", "redirect_target",
            ])
            for ref in refs:
                content = session.get(ContentInventory, ref.content_inventory_id)
                writer.writerow([
                    content.title if content else "",
                    content.url if content else "",
                    content.post_type if content else "",
                    ref.reference_type,
                    ref.reference_value,
                    ref.matched_inactive_product_id or "",
                    f"{ref.match_confidence:.2f}",
                    ref.snippet or "",
                    ref.status,
                    ref.user_notes or "",
                    ref.redirect_target_url or "",
                ])

        console.print(f"Exported {len(refs)} references to {output}")
    finally:
        session.close()


# ── Research: keyword subcommands ─────────────────────────────────────────────

@kw_app.command("seeds")
def kw_seeds_add(
    seeds: str = typer.Argument(..., help='Comma-separated seed keywords'),
) -> None:
    """Expand seed keywords into candidates with volumes and gap scores."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.research_keywords import run_seed_research

    seed_list = [s.strip() for s in seeds.split(",") if s.strip()]
    if not seed_list:
        console.print("[red]No seeds provided.[/red]")
        raise typer.Exit(1)

    session = SessionLocal()
    try:
        result = run_seed_research(session, seed_list)
        console.print()
        console.print("[bold]Seed research complete[/bold]")
        console.print(f"  Keyword candidates: {result['candidates']}")
        console.print(f"  New competitors:    {result['competitors_new']}")
    finally:
        session.close()


@kw_app.command("expand-inventory")
def kw_expand_inventory() -> None:
    """Find adjacent keywords from existing content target_keywords."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.research_keywords import run_inventory_expansion

    session = SessionLocal()
    try:
        result = run_inventory_expansion(session)
        console.print()
        console.print("[bold]Inventory expansion complete[/bold]")
        console.print(f"  Candidates found: {result['candidates']}")
        if "seeds_used" in result:
            console.print(f"  Seeds used:       {result['seeds_used']}")
        if "message" in result:
            console.print(f"  {result['message']}")
    finally:
        session.close()


@kw_app.command("gsc-gaps")
def kw_gsc_gaps() -> None:
    """List page 2-5 quick-win keywords from GSC data."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.research_keywords import run_gsc_gap_discovery

    session = SessionLocal()
    try:
        opportunities = run_gsc_gap_discovery(session)
        if not opportunities:
            console.print("No GSC gap opportunities found.")
            return

        console.print()
        console.print(f"[bold]PAGE 2-5 QUICK WINS ({len(opportunities)} keywords)[/bold]")
        console.print()

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Keyword", style="bold", max_width=40)
        table.add_column("Position", justify="right")
        table.add_column("Impressions", justify="right")
        table.add_column("Clicks", justify="right")
        table.add_column("Page", max_width=50)

        for opp in opportunities[:50]:
            table.add_row(
                opp["query"],
                f"{opp['position']:.1f}",
                str(opp["impressions"]),
                str(opp["clicks"]),
                opp.get("page", ""),
            )
        console.print(table)
    finally:
        session.close()


@kw_app.command("list")
def kw_list(
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
    top: int = typer.Option(50, "--top", help="Number of results"),
) -> None:
    """List keyword candidates."""
    from sqlalchemy import select as sa_select

    from naturesseed_pipeline.db.models import KeywordCandidate
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        query = sa_select(KeywordCandidate).order_by(
            KeywordCandidate.search_volume.desc()
        ).limit(top)
        if status:
            query = query.where(KeywordCandidate.status == status)

        candidates = session.execute(query).scalars().all()

        if not candidates:
            console.print("No keyword candidates found.")
            return

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Keyword", style="bold", max_width=40)
        table.add_column("Volume", justify="right")
        table.add_column("Difficulty", justify="right")
        table.add_column("Intent")
        table.add_column("Gap", justify="right")
        table.add_column("Source")
        table.add_column("Status")

        for c in candidates:
            table.add_row(
                c.keyword,
                str(c.search_volume or "-"),
                f"{c.keyword_difficulty:.0f}" if c.keyword_difficulty else "-",
                c.intent or "-",
                f"{c.gap_score:.1f}" if c.gap_score is not None else "-",
                c.source or "-",
                c.status,
            )
        console.print(table)
        console.print(f"\nShowing {len(candidates)} candidates")
    finally:
        session.close()


@kw_app.command("providers")
def kw_providers() -> None:
    """Show active/gated keyword research providers."""
    from naturesseed_pipeline.pipelines.research_keywords import get_provider_status

    statuses = get_provider_status()
    console.print()
    console.print("[bold]KEYWORD RESEARCH PROVIDERS[/bold]")
    for name, status in statuses.items():
        color = "green" if status == "ACTIVE" else "yellow" if "GATED" in status else "red"
        console.print(f"  {name}: [{color}]{status}[/{color}]")


@kw_app.command("enrich")
def kw_enrich(
    with_provider: str = typer.Option("dataforseo", "--with", help="Provider to enrich with"),
    top: int = typer.Option(100, "--top", help="Number of candidates to enrich"),
) -> None:
    """Enrich existing candidates with DataForSEO SERP + difficulty."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.research_keywords import run_dataforseo_enrichment

    if with_provider != "dataforseo":
        console.print(f"[red]Unknown provider: {with_provider}. Only 'dataforseo' supported.[/red]")
        raise typer.Exit(1)

    session = SessionLocal()
    try:
        result = run_dataforseo_enrichment(session, top_n=top)
        console.print(f"Enriched {result['enriched']} candidates with DataForSEO data.")
    finally:
        session.close()


@competitors_app.command("list")
def competitors_list() -> None:
    """List top competitor domains from Ads auction insights."""
    from sqlalchemy import select as sa_select

    from naturesseed_pipeline.db.models import CompetitorDomain
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        domains = session.execute(
            sa_select(CompetitorDomain)
            .order_by(CompetitorDomain.keyword_overlap_count.desc())
            .limit(50)
        ).scalars().all()

        if not domains:
            console.print("No competitor domains discovered yet.")
            console.print("Run [bold]nspipe research keywords seeds add[/bold] first.")
            return

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Domain", style="bold")
        table.add_column("Keyword Overlap", justify="right")
        table.add_column("Source")
        table.add_column("First Seen")

        for d in domains:
            table.add_row(
                d.domain,
                str(d.keyword_overlap_count),
                d.source,
                d.discovered_at.strftime("%Y-%m-%d") if d.discovered_at else "-",
            )
        console.print(table)
    finally:
        session.close()


# ── Research: media subcommands ───────────────────────────────────────────────

@media_app.command("run")
def media_run() -> None:
    """Pull signals from all configured media sources."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.research_media import run_listener_sweep

    session = SessionLocal()
    try:
        result = run_listener_sweep(session)
        console.print()
        console.print("[bold]Media listener sweep complete[/bold]")
        console.print(f"  Total fetched:  {result['total_fetched']}")
        console.print(f"  New signals:    {result['new_signals']}")
        if result["by_source"]:
            for src, count in sorted(result["by_source"].items()):
                console.print(f"    {src}: {count}")
    finally:
        session.close()


@media_app.command("top")
def media_top(
    since: str = typer.Option("7d", "--since", help="Time window: 7d, 30d, etc."),
) -> None:
    """Show top-scoring media signals."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.research_media import get_top_signals

    days = int(since.rstrip("d")) if since.endswith("d") else 7

    session = SessionLocal()
    try:
        signals = get_top_signals(session, since_days=days)

        if not signals:
            console.print("No signals found.")
            return

        console.print()
        console.print(f"[bold]TOP MEDIA SIGNALS (last {days} days)[/bold]")
        console.print()

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Source", max_width=15)
        table.add_column("Title", max_width=45)
        table.add_column("Rel", justify="right")
        table.add_column("Trend", justify="right")
        table.add_column("Date")

        for s in signals[:50]:
            rel_color = "green" if (s.relevance_score or 0) >= 0.7 else "yellow"
            trend_color = "green" if (s.trending_score or 0) >= 0.6 else "dim"
            table.add_row(
                f"{s.source_type}/{s.source_name or ''}",
                (s.title or "")[:45],
                f"[{rel_color}]{s.relevance_score:.1f}[/{rel_color}]",
                f"[{trend_color}]{s.trending_score:.1f}[/{trend_color}]",
                s.captured_at.strftime("%m/%d") if s.captured_at else "-",
            )
        console.print(table)
    finally:
        session.close()


@media_app.command("promote")
def media_promote(
    min_relevance: float = typer.Option(0.7, "--min-relevance"),
    min_trend: float = typer.Option(0.6, "--min-trend"),
) -> None:
    """Promote high-scoring signals to keyword candidates."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.research_media import promote_signals_to_keywords

    session = SessionLocal()
    try:
        result = promote_signals_to_keywords(session, min_relevance, min_trend)
        console.print(f"Promoted {result['promoted']} signals to keyword candidates "
                       f"(from {result['eligible']} eligible)")
    finally:
        session.close()


@media_sources_app.command("list")
def media_sources_list() -> None:
    """List configured media sources."""
    from naturesseed_pipeline.pipelines.research_media import list_sources

    sources = list_sources()
    if not sources:
        console.print("No sources configured. Edit config/media_sources.yaml")
        return

    for source_type, items in sources.items():
        console.print(f"\n[bold]{source_type.upper()}[/bold]")
        for item in items:
            console.print(f"  {item['name']}  ({item['id']})")


@media_sources_app.command("add")
def media_sources_add(
    source_type: str = typer.Option(..., "--type", help="youtube, reddit, or rss"),
    name: str = typer.Option(..., "--name", help="Display name"),
    identifier: str = typer.Option(..., "--id", help="Channel ID, subreddit, or RSS URL"),
) -> None:
    """Add a new media source."""
    from naturesseed_pipeline.pipelines.research_media import add_source

    add_source(source_type, name, identifier)
    console.print(f"Added {source_type} source: {name} ({identifier})")


# ── Brief commands ────────────────────────────────────────────────────────────

@brief_app.command("score-backlog")
def brief_score_backlog(
    top: int = typer.Option(50, "--top", help="Show top N"),
) -> None:
    """Score and rank keyword backlog by priority."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.scoring import rank_backlog

    session = SessionLocal()
    try:
        ranked = rank_backlog(session, limit=top)
        if not ranked:
            console.print("No keyword candidates to score.")
            return

        console.print()
        console.print(f"[bold]KEYWORD BACKLOG — TOP {len(ranked)}[/bold]")
        console.print()

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("ID", justify="right")
        table.add_column("Keyword", style="bold", max_width=35)
        table.add_column("Score", justify="right")
        table.add_column("Volume", justify="right")
        table.add_column("Diff", justify="right")
        table.add_column("Gap", justify="right")
        table.add_column("Intent")

        for kw, score in ranked:
            table.add_row(
                str(kw.id),
                kw.keyword[:35],
                f"[bold]{score:.3f}[/bold]",
                str(kw.search_volume or "-"),
                f"{kw.keyword_difficulty:.0f}" if kw.keyword_difficulty else "-",
                f"{kw.gap_score:.1f}" if kw.gap_score is not None else "-",
                kw.intent or "-",
            )
        console.print(table)
    finally:
        session.close()


@brief_app.command("generate")
def brief_generate(
    keyword_id: int = typer.Option(..., "--keyword-id", help="KeywordCandidate ID"),
    no_scrape: bool = typer.Option(False, "--no-scrape", help="Skip competitor scraping"),
) -> None:
    """Generate a brief for a specific keyword candidate."""
    from naturesseed_pipeline.agents.brief_generator import generate_brief
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        brief = generate_brief(session, keyword_id, scrape_competitors=not no_scrape)
        if brief:
            console.print(f"Brief generated: ID={brief.id}, topic='{brief.topic}'")
        else:
            console.print("[red]Failed to generate brief.[/red]")
    finally:
        session.close()


@brief_app.command("generate-top")
def brief_generate_top(
    count: int = typer.Option(5, "--count", help="Number of briefs to generate"),
    no_scrape: bool = typer.Option(False, "--no-scrape", help="Skip competitor scraping"),
) -> None:
    """Generate briefs for the top N scored keyword candidates."""
    from naturesseed_pipeline.agents.brief_generator import generate_top_briefs
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        briefs = generate_top_briefs(session, count=count, scrape=not no_scrape)
        console.print()
        console.print(f"[bold]Generated {len(briefs)} briefs[/bold]")
        for b in briefs:
            console.print(f"  ID={b.id}  {b.topic}  (priority: {b.priority_score or '-'})")
        if briefs:
            console.print()
            console.print("Run [bold]nspipe brief review[/bold] to approve/reject.")
    finally:
        session.close()


@brief_app.command("show")
def brief_show(
    brief_id: int = typer.Argument(..., help="Brief ID"),
) -> None:
    """Pretty-print a brief as markdown."""
    from naturesseed_pipeline.agents.brief_generator import format_brief_markdown
    from naturesseed_pipeline.db.models import BriefQueue
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        brief = session.get(BriefQueue, brief_id)
        if not brief:
            console.print(f"[red]Brief {brief_id} not found.[/red]")
            raise typer.Exit(1)
        from rich.markdown import Markdown
        md = format_brief_markdown(brief)
        console.print(Markdown(md))
    finally:
        session.close()


@brief_app.command("review")
def brief_review() -> None:
    """Interactive review of pending briefs — approve/reject/skip."""
    from sqlalchemy import select as sa_select

    from naturesseed_pipeline.agents.brief_generator import format_brief_markdown
    from naturesseed_pipeline.db.models import BriefQueue
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        briefs = session.execute(
            sa_select(BriefQueue)
            .where(BriefQueue.status == "pending")
            .order_by(BriefQueue.priority_score.desc())
        ).scalars().all()

        if not briefs:
            console.print("No pending briefs to review.")
            return

        total = len(briefs)
        console.print(f"[bold]{total} pending briefs[/bold]")
        console.print("[a]pprove  [r]eject  [s]kip  [v]iew full")
        console.print()

        for i, brief in enumerate(briefs, 1):
            b = brief.brief_json or {}
            console.print(f"[bold]--- {i}/{total} ---[/bold]")
            console.print(f"[bold]{brief.topic}[/bold]  (ID: {brief.id})")
            console.print(f"  Priority: {brief.priority_score or '-'}")
            console.print(f"  Intent: {b.get('search_intent', '-')}")
            console.print(f"  Word count: {b.get('recommended_word_count', '-')}")

            titles = b.get("suggested_title_options", [])
            if titles:
                console.print(f"  Title: {titles[0]}")

            outline = b.get("outline", [])
            if outline:
                console.print(f"  Sections: {len(outline)}")
                for s in outline[:3]:
                    console.print(f"    - {s.get('heading', '')}")
                if len(outline) > 3:
                    console.print(f"    ... +{len(outline) - 3} more")

            console.print()

            choice = ""
            while choice not in ("a", "r", "s", "v"):
                choice = input("  [a]pprove [r]eject [s]kip [v]iew > ").strip().lower()

            if choice == "v":
                from rich.markdown import Markdown
                console.print(Markdown(format_brief_markdown(brief)))
                choice = ""
                while choice not in ("a", "r", "s"):
                    choice = input("  [a]pprove [r]eject [s]kip > ").strip().lower()

            if choice == "a":
                brief.status = "approved"
                brief.approved_at = datetime.now(timezone.utc)
                console.print("  [green]Approved[/green]")
            elif choice == "r":
                brief.status = "rejected"
                console.print("  [red]Rejected[/red]")

            session.commit()
            console.print()

        console.print("[bold]Review complete.[/bold]")
    finally:
        session.close()


# ── Write commands ────────────────────────────────────────────────────────────

@write_app.command("from-brief")
def write_from_brief_cmd(
    brief_id: int = typer.Argument(..., help="Brief ID to write from"),
    no_fetch: bool = typer.Option(False, "--no-fetch", help="Skip source fetching in fact-check"),
) -> None:
    """Run full write pipeline: writer -> fact_checker -> editor -> supervisor."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.write import write_from_brief_pipeline

    session = SessionLocal()
    try:
        result = write_from_brief_pipeline(session, brief_id, fetch_sources=not no_fetch)
        console.print()
        if "error" in result:
            console.print(f"[red]{result['error']}[/red]")
            return
        console.print(f"[bold]Draft created: ID={result['draft_id']}[/bold]")
        console.print(f"  Status: {result.get('final_status', 'unknown')}")
        stages = result.get("stages", {})
        for stage, info in stages.items():
            if stage != "status":
                console.print(f"  {stage}: {info}")
    finally:
        session.close()


@write_app.command("next")
def write_next_cmd(
    no_fetch: bool = typer.Option(False, "--no-fetch", help="Skip source fetching"),
) -> None:
    """Write draft from the next approved brief in queue."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.write import write_next_approved_brief

    session = SessionLocal()
    try:
        result = write_next_approved_brief(session, fetch_sources=not no_fetch)
        if not result:
            console.print("No approved briefs in queue.")
            return
        console.print(f"[bold]Draft created: ID={result.get('draft_id')}[/bold]")
        console.print(f"  Status: {result.get('final_status', 'unknown')}")
    finally:
        session.close()


# ── Review (supervisor) commands ──────────────────────────────────────────────

@review_app.command("queue")
def review_queue() -> None:
    """List drafts pending supervisor review."""
    from sqlalchemy import select as sa_select

    from naturesseed_pipeline.db.models import Draft
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        drafts = session.execute(
            sa_select(Draft)
            .where(Draft.status.in_(["supervisor_pending", "reviewed", "needs_revision"]))
            .order_by(Draft.created_at.desc())
        ).scalars().all()

        if not drafts:
            console.print("No drafts pending review.")
            return

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("ID", justify="right")
        table.add_column("Title", max_width=40)
        table.add_column("Status")
        table.add_column("Fact Issues", justify="right")
        table.add_column("Edit Issues", justify="right")
        table.add_column("Created")

        for d in drafts:
            fact_issues = 0
            if d.fact_check_notes and isinstance(d.fact_check_notes, dict):
                fact_issues = d.fact_check_notes.get("unsupported", 0) + d.fact_check_notes.get("placeholders", 0)
            edit_issues = 0
            if d.editorial_notes and isinstance(d.editorial_notes, dict):
                edit_issues = len(d.editorial_notes.get("remaining_issues", []))

            color = "green" if d.status == "reviewed" else "yellow" if d.status == "supervisor_pending" else "red"
            table.add_row(
                str(d.id),
                (d.title or "")[:40],
                f"[{color}]{d.status}[/{color}]",
                str(fact_issues),
                str(edit_issues),
                d.created_at.strftime("%m/%d %H:%M") if d.created_at else "-",
            )
        console.print(table)
    finally:
        session.close()


@review_app.command("show")
def review_show(
    draft_id: int = typer.Argument(..., help="Draft ID"),
) -> None:
    """Render a draft with fact-check and editorial notes."""
    from naturesseed_pipeline.db.models import Draft
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        draft = session.get(Draft, draft_id)
        if not draft:
            console.print(f"[red]Draft {draft_id} not found.[/red]")
            raise typer.Exit(1)

        from rich.markdown import Markdown
        from rich.panel import Panel

        console.print(Panel(f"[bold]{draft.title}[/bold]\nStatus: {draft.status}", title=f"Draft #{draft.id}"))
        console.print()

        if draft.content_markdown:
            console.print(Markdown(draft.content_markdown))

        if draft.fact_check_notes and isinstance(draft.fact_check_notes, dict):
            console.print()
            console.print("[bold yellow]FACT CHECK NOTES[/bold yellow]")
            fc = draft.fact_check_notes
            console.print(f"  Supported: {fc.get('supported', 0)}  Unsupported: {fc.get('unsupported', 0)}  Placeholders: {fc.get('placeholders', 0)}")
            for detail in fc.get("details", [])[:10]:
                status_color = "green" if detail["status"] == "supported" else "red"
                console.print(f"  [{status_color}]{detail['status']}[/{status_color}] {detail.get('claim', '')[:60]}")

        if draft.editorial_notes and isinstance(draft.editorial_notes, dict):
            console.print()
            console.print("[bold yellow]EDITORIAL NOTES[/bold yellow]")
            en = draft.editorial_notes
            rd = en.get("readability", {})
            console.print(f"  Readability: FK={rd.get('flesch_reading_ease', '?')} Grade={rd.get('flesch_kincaid_grade', '?')}")
            kd = en.get("keyword_density", {})
            console.print(f"  Keyword density: {kd.get('density_pct', '?')}%")
            for fix in en.get("auto_fixes", []):
                console.print(f"  [green]Auto-fixed:[/green] {fix}")
            for issue in en.get("remaining_issues", []):
                console.print(f"  [red]Issue:[/red] {issue}")
    finally:
        session.close()


@review_app.command("open")
def review_open(
    draft_id: int = typer.Argument(..., help="Draft ID"),
) -> None:
    """Open draft markdown in $EDITOR for direct editing."""
    import os
    import tempfile

    from naturesseed_pipeline.db.models import Draft
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        draft = session.get(Draft, draft_id)
        if not draft or not draft.content_markdown:
            console.print(f"[red]Draft {draft_id} not found or empty.[/red]")
            raise typer.Exit(1)

        editor = os.environ.get("EDITOR", "nano")
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write(draft.content_markdown)
            tmp_path = f.name

        os.system(f"{editor} {tmp_path}")

        with open(tmp_path) as f:
            updated = f.read()

        if updated != draft.content_markdown:
            draft.content_markdown = updated
            session.commit()
            console.print(f"[green]Draft {draft_id} updated.[/green]")
        else:
            console.print("No changes made.")

        os.unlink(tmp_path)
    finally:
        session.close()


@review_app.command("approve")
def review_approve(
    draft_id: int = typer.Argument(..., help="Draft ID"),
) -> None:
    """Approve a draft and move to publish queue."""
    from naturesseed_pipeline.db.models import Draft, PublishQueue
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        draft = session.get(Draft, draft_id)
        if not draft:
            console.print(f"[red]Draft {draft_id} not found.[/red]")
            raise typer.Exit(1)

        draft.status = "approved"
        draft.approved_at = datetime.now(timezone.utc)
        session.add(PublishQueue(
            draft_id=draft.id,
            publish_status="scheduled_pending",
        ))
        session.commit()
        console.print(f"[green]Draft {draft_id} approved and added to publish queue.[/green]")
    finally:
        session.close()


@review_app.command("reject")
def review_reject(
    draft_id: int = typer.Argument(..., help="Draft ID"),
    reason: str = typer.Option("", "--reason", help="Rejection reason"),
) -> None:
    """Reject a draft."""
    from naturesseed_pipeline.db.models import Draft
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        draft = session.get(Draft, draft_id)
        if not draft:
            console.print(f"[red]Draft {draft_id} not found.[/red]")
            raise typer.Exit(1)
        draft.status = "rejected"
        draft.reviewer_notes = reason or None
        session.commit()
        console.print(f"Draft {draft_id} rejected.")
    finally:
        session.close()


@review_app.command("request-changes")
def review_request_changes(
    draft_id: int = typer.Argument(..., help="Draft ID"),
    notes: str = typer.Option("", "--notes", help="Change request notes"),
) -> None:
    """Request changes on a draft."""
    from naturesseed_pipeline.db.models import Draft
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        draft = session.get(Draft, draft_id)
        if not draft:
            console.print(f"[red]Draft {draft_id} not found.[/red]")
            raise typer.Exit(1)
        draft.status = "changes_requested"
        draft.reviewer_notes = notes or None
        session.commit()
        console.print(f"Changes requested on draft {draft_id}.")
    finally:
        session.close()


# ── Image commands ────────────────────────────────────────────────────────────

@images_app.command("index-library")
def images_index_library() -> None:
    """Index WordPress media library for image reuse."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.integrations.image_library import index_media_library

    session = SessionLocal()
    try:
        count = index_media_library(session)
        console.print(f"Indexed {count} new media items.")
    finally:
        session.close()


@images_app.command("attach")
def images_attach(
    draft_id: int = typer.Argument(..., help="Draft ID"),
) -> None:
    """Select and attach images to a draft."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.images import attach_images_to_draft

    session = SessionLocal()
    try:
        result = attach_images_to_draft(session, draft_id)
        if "error" in result:
            console.print(f"[red]{result['error']}[/red]")
            return
        console.print()
        console.print(f"[bold]Images attached to draft {draft_id}[/bold]")
        console.print(f"  Total slots: {result['total_slots']}")
        console.print(f"  From library: {result['from_library']}")
        console.print(f"  Generated: {result['generated']}")
        console.print(f"  Unresolved: {result['unresolved']}")
        console.print(f"  With alt text: {result['with_alt_text']}")
    finally:
        session.close()


@images_app.command("preview")
def images_preview(
    draft_id: int = typer.Argument(..., help="Draft ID"),
) -> None:
    """Preview image assignments for a draft."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.images import preview_image_assignments

    session = SessionLocal()
    try:
        assignments = preview_image_assignments(session, draft_id)
        if not assignments:
            console.print("No image assignments found. Run [bold]nspipe images attach[/bold] first.")
            return

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Slot")
        table.add_column("Source")
        table.add_column("URL / Path", max_width=50)
        table.add_column("Alt Text", max_width=40)

        for a in assignments:
            source_color = "green" if a.get("source") == "library" else "yellow" if a.get("source") == "generated" else "red"
            table.add_row(
                a.get("slot", ""),
                f"[{source_color}]{a.get('source', 'none')}[/{source_color}]",
                (a.get("url") or a.get("local_path") or "-")[:50],
                (a.get("alt_text") or "-")[:40],
            )
        console.print(table)
    finally:
        session.close()


# ── Publish commands ──────────────────────────────────────────────────────────

@publish_app.command("schedule")
def publish_schedule_cmd(
    draft_id: int = typer.Argument(..., help="Draft ID to schedule"),
) -> None:
    """Schedule a draft for publishing."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.schedule import schedule_draft

    session = SessionLocal()
    try:
        pq = schedule_draft(session, draft_id)
        if pq and pq.scheduled_for:
            console.print(f"[green]Draft {draft_id} scheduled for {pq.scheduled_for.strftime('%Y-%m-%d %H:%M')}[/green]")
        else:
            console.print("[red]Failed to schedule.[/red]")
    finally:
        session.close()


@publish_app.command("calendar")
def publish_calendar(
    days: int = typer.Option(30, "--days", help="Days ahead to show"),
) -> None:
    """Show upcoming editorial calendar."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.schedule import get_calendar

    session = SessionLocal()
    try:
        cal = get_calendar(session, days=days)
        if not cal:
            console.print("No scheduled posts.")
            return

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Date")
        table.add_column("Title", max_width=40)
        table.add_column("Status")
        table.add_column("Draft ID", justify="right")

        for item in cal:
            dt = item["scheduled_for"]
            table.add_row(
                dt.strftime("%Y-%m-%d %H:%M") if dt else "-",
                (item["title"] or "")[:40],
                item["status"],
                str(item["draft_id"]),
            )
        console.print(table)
    finally:
        session.close()


@publish_app.command("run")
def publish_run() -> None:
    """Push all scheduled posts that are due to WordPress."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.publish import run_scheduled_batch

    session = SessionLocal()
    try:
        results = run_scheduled_batch(session)
        console.print(f"Published {len(results)} posts.")
        for r in results:
            status = "[green]ok[/green]" if "error" not in r else f"[red]{r['error']}[/red]"
            console.print(f"  Draft {r.get('draft_id')}: {status}")
    finally:
        session.close()


@publish_app.command("dry-run")
def publish_dry_run(
    draft_id: int = typer.Argument(..., help="Draft ID"),
) -> None:
    """Show what would be sent to WordPress without actually publishing."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.publish import publish_draft

    session = SessionLocal()
    try:
        result = publish_draft(session, draft_id, dry_run=True)
        console.print()
        console.print("[bold]DRY RUN — would publish:[/bold]")
        for k, v in result.items():
            if k == "html_preview":
                console.print(f"  {k}: {str(v)[:200]}...")
            else:
                console.print(f"  {k}: {v}")
    finally:
        session.close()


# ── Refresh commands ──────────────────────────────────────────────────────────

refresh_app = typer.Typer(help="Content refresh — find and update decaying content.")
app.add_typer(refresh_app, name="refresh")


@refresh_app.command("scan")
def refresh_scan() -> None:
    """Scan for decaying content and add to refresh queue."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.refresh import scan_and_queue

    session = SessionLocal()
    try:
        added = scan_and_queue(session)
        console.print(f"Added {added} items to refresh queue.")
    finally:
        session.close()


@refresh_app.command("queue")
def refresh_queue_cmd() -> None:
    """List pending refresh items."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.refresh import get_refresh_queue

    session = SessionLocal()
    try:
        items = get_refresh_queue(session)
        if not items:
            console.print("No pending refreshes.")
            return

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("ID", justify="right")
        table.add_column("Title", max_width=35)
        table.add_column("Reason", max_width=45)
        table.add_column("Created")

        for item in items:
            table.add_row(
                str(item["refresh_id"]),
                (item["title"] or "")[:35],
                (item["reason"] or "")[:45],
                item["created_at"].strftime("%m/%d") if item["created_at"] else "-",
            )
        console.print(table)
    finally:
        session.close()


@refresh_app.command("plan")
def refresh_plan(
    refresh_id: int = typer.Argument(..., help="Refresh queue ID"),
) -> None:
    """Generate a refresh brief for a queued item."""
    from naturesseed_pipeline.agents.refresh_planner import plan_refresh
    from naturesseed_pipeline.db.session import SessionLocal

    session = SessionLocal()
    try:
        brief = plan_refresh(session, refresh_id)
        if brief:
            console.print(f"[green]Refresh brief created: ID={brief.id}, topic='{brief.topic}'[/green]")
        else:
            console.print("[red]Failed to plan refresh.[/red]")
    finally:
        session.close()


@refresh_app.command("execute")
def refresh_execute(
    refresh_id: int = typer.Argument(..., help="Refresh queue ID"),
) -> None:
    """Full refresh pipeline: plan -> write -> review -> publish-update."""
    from naturesseed_pipeline.agents.refresh_planner import plan_refresh
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.write import write_from_brief_pipeline

    session = SessionLocal()
    try:
        # Step 1: Plan
        brief = plan_refresh(session, refresh_id)
        if not brief:
            console.print("[red]Failed to plan refresh.[/red]")
            return

        # Step 2: Approve brief automatically for refresh
        brief.status = "approved"
        session.commit()

        # Step 3: Write
        result = write_from_brief_pipeline(session, brief.id, fetch_sources=False)
        if "error" in result:
            console.print(f"[red]{result['error']}[/red]")
            return

        console.print(f"[green]Refresh draft created: ID={result['draft_id']}[/green]")
        console.print(f"  Status: {result.get('final_status')}")
        console.print("  Run [bold]nspipe review show[/bold] to review before publishing.")
    finally:
        session.close()


# ── Orchestrator commands ─────────────────────────────────────────────────────

run_app = typer.Typer(help="Pipeline orchestration — daily, weekly, refresh runs.")
app.add_typer(run_app, name="run")


@run_app.command("daily")
def run_daily_cmd() -> None:
    """Daily: audit sync + analytics sync + media listener sweep."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.orchestrator import run_daily

    session = SessionLocal()
    try:
        results = run_daily(session)
        console.print()
        console.print("[bold]DAILY RUN COMPLETE[/bold]")
        for step, result in results.items():
            status = "[green]ok[/green]" if "error" not in result else f"[red]error[/red]"
            console.print(f"  {step}: {status}")
    finally:
        session.close()


@run_app.command("weekly")
def run_weekly_cmd(
    briefs: int = typer.Option(5, "--briefs", help="Number of briefs to generate"),
) -> None:
    """Weekly: keyword expansion + scoring + generate top N briefs."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.orchestrator import run_weekly

    session = SessionLocal()
    try:
        results = run_weekly(session, brief_count=briefs)
        console.print()
        console.print("[bold]WEEKLY RUN COMPLETE[/bold]")
        for step, result in results.items():
            status = "[green]ok[/green]" if "error" not in result else f"[red]error[/red]"
            console.print(f"  {step}: {status}")
    finally:
        session.close()


@run_app.command("refresh")
def run_refresh_cmd() -> None:
    """Quarterly: refresh scan for decaying content."""
    from naturesseed_pipeline.db.session import SessionLocal
    from naturesseed_pipeline.pipelines.orchestrator import run_refresh

    session = SessionLocal()
    try:
        results = run_refresh(session)
        console.print()
        console.print("[bold]REFRESH SCAN COMPLETE[/bold]")
        for step, result in results.items():
            status = "[green]ok[/green]" if "error" not in result else f"[red]error[/red]"
            console.print(f"  {step}: {status}")
    finally:
        session.close()


# ── Top-level callback ────────────────────────────────────────────────────────

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Nature's Seed Content Pipeline."""
    setup_logging("DEBUG" if verbose else "INFO")
