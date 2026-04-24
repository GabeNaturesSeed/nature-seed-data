"""Tag articles with product and species mentions.

- Active product mentions → content_product_mentions
- Inactive (status='draft') product mentions → orphan_references (inactive_product)
- Species names not in any publish-status product's species_list → orphan_references (species_mention)
"""

import re

import structlog
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from naturesseed_pipeline.db.models import (
    ContentInventory, ContentProductMention, OrphanReference,
)
from naturesseed_pipeline.pipelines.audit.product_match import (
    ProductMatcher, build_matcher, find_product_mentions,
)

log = structlog.get_logger()

# Broad vocabulary of grass/seed/forage species to detect in content,
# even when not represented in the current catalog.
_KNOWN_SPECIES: frozenset[str] = frozenset({
    "fescue", "tall fescue", "fine fescue", "creeping red fescue", "chewings fescue",
    "hard fescue", "sheep fescue",
    "rye", "ryegrass", "perennial ryegrass", "annual ryegrass", "italian ryegrass",
    "bluegrass", "kentucky bluegrass", "rough bluegrass", "canada bluegrass",
    "bentgrass", "creeping bentgrass", "colonial bentgrass",
    "bermudagrass", "bermuda grass", "zoysiagrass", "zoysia grass",
    "buffalograss", "buffalo grass", "st augustine grass", "centipede grass",
    "bahiagrass", "bahia grass", "carpetgrass",
    "orchardgrass", "orchard grass",
    "timothy", "bromegrass", "brome grass", "smooth brome", "meadow brome",
    "wheatgrass", "crested wheatgrass", "intermediate wheatgrass", "pubescent wheatgrass",
    "slender wheatgrass",
    "clover", "red clover", "white clover", "alsike clover", "sweet clover",
    "crimson clover", "arrowleaf clover", "subterranean clover",
    "alfalfa", "sainfoin", "birdsfoot trefoil", "trefoil",
    "vetch", "hairy vetch", "common vetch", "crown vetch",
    "chicory", "plantain", "yarrow", "wildflower",
    "sunflower", "buckwheat", "phacelia", "borage",
    "sorghum", "sudangrass", "sudan grass", "sorghum sudan",
    "millet", "foxtail millet", "pearl millet", "japanese millet",
    "oats", "wheat", "barley", "triticale", "rye grain", "winter rye",
    "flax", "linseed", "canola", "mustard",
    "radish", "turnip", "rape", "rapeseed",
    "cowpea", "soybean", "field pea", "sunn hemp", "hemp",
})


def _collect_species(matcher: ProductMatcher) -> set[str]:
    """Merge catalog species_list entries with the built-in vocabulary."""
    species: set[str] = set(_KNOWN_SPECIES)
    for rec in matcher.all_records:
        for s in rec.species_list or []:
            if s:
                species.add(s.strip().lower())
    return species


def _find_species_mentions(text: str, all_species: set[str]) -> list[tuple[str, str]]:
    """Return (species, snippet) tuples for every species string found in text."""
    if not text:
        return []
    text_lower = text.lower()
    hits: list[tuple[str, str]] = []
    for sp in all_species:
        if len(sp) < 4:
            continue
        pattern = r"\b" + re.escape(sp) + r"\b"
        m = re.search(pattern, text_lower)
        if m:
            lo = max(0, m.start() - 40); hi = min(len(text), m.end() + 40)
            hits.append((sp, text[lo:hi]))
    return hits


def run_tag_products(session: Session, fuzzy_threshold: float) -> dict[str, int]:
    matcher = build_matcher(session)
    all_species = _collect_species(matcher)

    content_rows = session.execute(select(ContentInventory)).scalars().all()

    counts = {"articles": 0, "product_mentions": 0, "inactive_orphans": 0,
              "species_orphans": 0}

    for row in content_rows:
        counts["articles"] += 1

        # Wipe prior auto-populated rows for this content (keep user-decided)
        session.execute(
            delete(ContentProductMention)
            .where(ContentProductMention.content_inventory_id == row.id)
        )
        session.execute(
            delete(OrphanReference).where(
                OrphanReference.content_inventory_id == row.id,
                OrphanReference.reference_type.in_(["inactive_product", "species_mention"]),
                OrphanReference.user_decision_at.is_(None),
            )
        )
        session.flush()

        matches = find_product_mentions(
            row.content_text or "", row.content_html or "",
            matcher, fuzzy_threshold,
        )
        for m in matches:
            if m.is_active:
                session.add(ContentProductMention(
                    content_inventory_id=row.id, wp_product_id=m.wp_product_id,
                    product_slug=m.product_slug, product_name=m.product_name,
                    mention_count=1, first_snippet=m.snippet,
                    match_type=m.match_type, confidence=m.confidence,
                ))
                counts["product_mentions"] += 1
            else:
                session.add(OrphanReference(
                    content_inventory_id=row.id,
                    reference_type="inactive_product",
                    reference_value=m.product_slug,
                    matched_inactive_product_id=m.wp_product_id,
                    match_confidence=m.confidence,
                    snippet=m.snippet,
                    status="flagged",
                ))
                counts["inactive_orphans"] += 1

        # Species mentions: only flag if species not already covered by an active match
        covered_species = {
            sp.strip().lower()
            for match in matches if match.is_active
            for sp in (matcher.by_slug.get(match.product_slug).species_list or [])
        }
        for species, snippet in _find_species_mentions(row.content_text or "", all_species):
            if species in covered_species:
                continue
            session.add(OrphanReference(
                content_inventory_id=row.id,
                reference_type="species_mention",
                reference_value=species,
                match_confidence=1.0,
                snippet=snippet,
                status="flagged",
            ))
            counts["species_orphans"] += 1

        session.flush()

    log.info("audit.tag_products.done", **counts)
    return counts
