from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CoverageResult:
    wc_total: int
    channel_total: int
    missing_skus: list = field(default_factory=list)


@dataclass
class DriftResult:
    drifted: list = field(default_factory=list)  # [{sku, field, wc, channel}]


@dataclass
class QualityResult:
    incomplete: list = field(default_factory=list)  # [{sku, missing_fields}]


@dataclass
class AdapterResult:
    channel: str
    error: str = ""
    coverage: CoverageResult = None
    drift: DriftResult = None
    quality: QualityResult = None

    @property
    def ok(self):
        return not self.error


class BaseAdapter(ABC):
    channel: str = ""

    def __init__(self, env: dict):
        self.env = env

    @abstractmethod
    def fetch_channel_products(self) -> list:
        """Pull current product data from the channel. Returns list of dicts with at least 'sku'."""

    @abstractmethod
    def get_required_fields(self) -> list:
        """Return list of field names that must be non-empty on every channel product."""

    def _active_wc_skus(self, master: dict) -> dict:
        """Return {sku: product_record} for all published WC products (including variation SKUs)."""
        skus = {}
        for p in master["products"].values():
            if p["status"] != "publish":
                continue
            if p["sku"]:
                skus[p["sku"]] = p
            for v in p.get("variations", []):
                if v["sku"]:
                    skus[v["sku"]] = p
        return skus

    def coverage_check(self, master: dict) -> CoverageResult:
        wc_skus = self._active_wc_skus(master)
        channel_products = self.fetch_channel_products()
        channel_skus = {p["sku"] for p in channel_products if p.get("sku")}
        missing = [sku for sku in wc_skus if sku not in channel_skus]
        return CoverageResult(
            wc_total=len(wc_skus),
            channel_total=len(channel_skus),
            missing_skus=missing,
        )

    def drift_check(self, master: dict, channel_products: list) -> DriftResult:
        wc_by_sku = self._active_wc_skus(master)
        channel_by_sku = {p["sku"]: p for p in channel_products if p.get("sku")}
        drifted = []
        for sku, wc_p in wc_by_sku.items():
            ch_p = channel_by_sku.get(sku)
            if not ch_p:
                continue
            for f in ("price", "stock_status"):
                wc_val = str(wc_p.get(f, ""))
                ch_val = str(ch_p.get(f, ""))
                if wc_val and ch_val and wc_val != ch_val:
                    drifted.append({"sku": sku, "field": f, "wc": wc_val, "channel": ch_val})
        return DriftResult(drifted=drifted)

    def quality_check(self, channel_products: list) -> QualityResult:
        required = self.get_required_fields()
        incomplete = []
        for p in channel_products:
            missing = [f for f in required if not p.get(f)]
            if missing:
                incomplete.append({"sku": p.get("sku", "?"), "missing_fields": missing})
        return QualityResult(incomplete=incomplete)

    def run(self, master: dict) -> AdapterResult:
        result = AdapterResult(channel=self.channel)
        try:
            channel_products = self.fetch_channel_products()
            wc_skus = self._active_wc_skus(master)
            channel_skus = {p["sku"] for p in channel_products if p.get("sku")}
            missing = [sku for sku in wc_skus if sku not in channel_skus]
            result.coverage = CoverageResult(
                wc_total=len(wc_skus),
                channel_total=len(channel_skus),
                missing_skus=missing,
            )
            result.drift = self.drift_check(master, channel_products)
            result.quality = self.quality_check(channel_products)
        except Exception as e:
            result.error = str(e)
        return result
