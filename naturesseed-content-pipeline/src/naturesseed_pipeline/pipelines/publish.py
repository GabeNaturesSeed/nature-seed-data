"""Publish pipeline — push approved drafts to WordPress.

Uploads images → converts markdown to HTML → injects schema → runs internal
linking → creates/updates WP post → updates publish_queue.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import Draft, PublishQueue, RefreshHistory
from naturesseed_pipeline.integrations.schema import generate_schema, inject_schema
from naturesseed_pipeline.integrations.wordpress import (
    WordPressClient,
    markdown_to_html,
)
from naturesseed_pipeline.pipelines.internal_links import add_internal_links

log = structlog.get_logger()


def _upload_draft_images(
    wp: WordPressClient,
    draft: Draft,
) -> int | None:
    """Upload featured image (hero slot) and return media_id."""
    assignments = draft.image_assignments
    if not assignments:
        return None

    for a in assignments:
        if a.get("slot") == "hero":
            local_path = a.get("local_path")
            url = a.get("url")

            if local_path:
                try:
                    result = wp.upload_media(
                        local_path,
                        title=draft.title,
                        alt_text=a.get("alt_text", ""),
                    )
                    return result.get("id")
                except Exception as e:
                    log.warning("image_upload_failed", error=str(e))
            elif url:
                # Library image — find its WP media ID from URL
                # Already in WP, just need to find the ID
                log.info("using_library_image", url=url)

    return None


def _strip_meta_comment(html: str) -> str:
    """Remove the meta_description HTML comment."""
    return re.sub(r"<!-- meta_description: .+? -->", "", html).strip()


def publish_draft(
    session: Session,
    draft_id: int,
    wp: WordPressClient | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Full publish pipeline for a single draft.

    Steps:
    1. Upload images to WP
    2. Convert markdown → HTML
    3. Inject schema markup
    4. Run internal linking pass
    5. Create/update WP post
    6. Update publish_queue

    Returns a summary dict. In dry_run mode, returns what would be sent.
    """
    draft = session.get(Draft, draft_id)
    if not draft or not draft.content_markdown:
        return {"error": "Draft not found or empty"}

    brief = draft.brief
    is_refresh = brief.is_refresh if brief else False
    original_wp_id = brief.original_wp_post_id if brief else None

    # Step 1: Convert markdown to HTML
    html = markdown_to_html(draft.content_markdown)
    html = _strip_meta_comment(html)

    # Step 2: Internal linking
    html, links = add_internal_links(session, html)

    # Step 3: Schema markup
    schema_block = generate_schema(
        html,
        title=draft.title,
        description=draft.meta_description or "",
        image_url=None,
    )
    html = inject_schema(html, schema_block)

    # Step 4: Generate slug
    slug = re.sub(r"[^a-z0-9]+", "-", draft.title.lower()).strip("-")[:80]

    # Get publish queue entry
    pq = session.execute(
        select(PublishQueue).where(PublishQueue.draft_id == draft_id)
    ).scalar_one_or_none()

    scheduled_for = pq.scheduled_for.isoformat() if pq and pq.scheduled_for else None

    result: dict[str, Any] = {
        "draft_id": draft_id,
        "title": draft.title,
        "slug": slug,
        "html_length": len(html),
        "internal_links": len(links),
        "schema_type": "detected",
        "is_refresh": is_refresh,
        "scheduled_for": scheduled_for,
    }

    if dry_run:
        result["html_preview"] = html[:500] + "..." if len(html) > 500 else html
        result["mode"] = "dry_run"
        return result

    # Step 5: Upload to WP
    close_wp = wp is None
    if wp is None:
        wp = WordPressClient()

    try:
        # Upload featured image
        featured_id = _upload_draft_images(wp, draft)
        result["featured_media_id"] = featured_id

        if is_refresh and original_wp_id:
            # Update existing post
            wp_result = wp.update_post(
                original_wp_id,
                title=draft.title,
                content_html=html,
            )
            result["wp_post_id"] = original_wp_id
            result["action"] = "updated"

            # Log refresh history
            session.add(RefreshHistory(
                content_inventory_id=0,  # TODO: look up from brief
                wp_post_id=original_wp_id,
                brief_id=brief.id if brief else None,
                draft_id=draft_id,
                changes_summary=f"Refresh published: {draft.title}",
                published_at=datetime.now(timezone.utc),
            ))
        else:
            # Create new post
            wp_result = wp.create_post(
                title=draft.title,
                content_html=html,
                slug=slug,
                excerpt=draft.meta_description or "",
                meta_description=draft.meta_description or "",
                featured_media_id=featured_id,
                status="future" if scheduled_for else "draft",
                scheduled_for=scheduled_for,
            )
            result["wp_post_id"] = wp_result.get("id")
            result["action"] = "created"

        # Update publish queue
        if pq:
            pq.wp_post_id = result.get("wp_post_id")
            pq.publish_status = "published"
            pq.published_at = datetime.now(timezone.utc)

        draft.status = "published"
        session.commit()

        log.info("draft_published", **{k: v for k, v in result.items() if k != "html_preview"})

    except Exception as e:
        log.error("publish_failed", draft_id=draft_id, error=str(e))
        result["error"] = str(e)
        if pq:
            pq.publish_status = "failed"
            session.commit()
    finally:
        if close_wp:
            wp.close()

    return result


def run_scheduled_batch(session: Session) -> list[dict[str, Any]]:
    """Process all approved drafts with scheduled_for <= now."""
    now = datetime.now(timezone.utc)
    items = session.execute(
        select(PublishQueue)
        .where(
            PublishQueue.publish_status == "scheduled_pending",
            PublishQueue.scheduled_for <= now,
        )
        .order_by(PublishQueue.scheduled_for)
    ).scalars().all()

    results: list[dict[str, Any]] = []
    for item in items:
        result = publish_draft(session, item.draft_id)
        results.append(result)

    log.info("scheduled_batch_complete", published=len(results))
    return results
