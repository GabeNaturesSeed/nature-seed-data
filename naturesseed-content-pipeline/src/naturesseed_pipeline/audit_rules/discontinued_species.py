"""Rule #2 — species mentioned but not in any publish-status product."""

from sqlalchemy import select

from naturesseed_pipeline.audit_rules.base import AuditContext, Finding
from naturesseed_pipeline.db.models import OrphanReference, WcCatalogSnapshot


class DiscontinuedSpeciesRule:
    name = "DiscontinuedSpeciesRule"
    severity = "critical"

    def _active_species(self, ctx: AuditContext) -> set[str]:
        def build():
            active = ctx.session.execute(
                select(WcCatalogSnapshot).where(WcCatalogSnapshot.status == "publish")
            ).scalars().all()
            out: set[str] = set()
            for p in active:
                for sp in p.species_list or []:
                    out.add(sp.strip().lower())
            return out
        return ctx.cached("active_species", build)

    def check(self, content, ctx: AuditContext) -> list[Finding]:
        active = self._active_species(ctx)
        rows = ctx.session.execute(
            select(OrphanReference).where(
                OrphanReference.content_inventory_id == content.id,
                OrphanReference.reference_type == "species_mention",
                OrphanReference.status == "flagged",
            )
        ).scalars().all()
        findings: list[Finding] = []
        for r in rows:
            if r.reference_value.strip().lower() in active:
                continue
            findings.append(Finding(
                rule_name=self.name, severity=self.severity,
                snippet=r.snippet or "",
                suggested_action=(
                    f"Species '{r.reference_value}' is not sold in any active product — "
                    f"remove mention or update to a currently-carried species"
                ),
            ))
        return findings
