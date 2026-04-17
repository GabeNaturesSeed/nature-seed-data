"""Klaviyo Strategy Framework — operational layer.

Modules:
    klaviyo_client: REST API wrapper (auth, pagination, retry)
    deliverability_gates: 4-gate status check for mode switching
    kpi_calculator: primary/secondary metric computation
    review_generator: weekly review markdown builder

Reference spec: docs/superpowers/specs/2026-04-17-klaviyo-strategy-design.md
"""
