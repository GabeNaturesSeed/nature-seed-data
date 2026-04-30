import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from feeds.digest.run_audit import run_audit


def test_run_audit_writes_latest_results_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Minimal feed_master
    master = {"meta": {"product_count": 1, "generated_at": "2026-01-01"}, "products": {}}
    master_path = tmp_path / "feeds" / "feed_master.json"
    master_path.parent.mkdir(parents=True)
    master_path.write_text(json.dumps(master))

    digest_dir = tmp_path / "feeds" / "digest"
    digest_dir.mkdir()

    with patch("feeds.digest.run_audit.MASTER_PATH", master_path), \
         patch("feeds.digest.run_audit.DIGEST_DIR", digest_dir), \
         patch("feeds.digest.run_audit.WalmartAdapter") as wa, \
         patch("feeds.digest.run_audit.AmazonAdapter") as aa, \
         patch("feeds.digest.run_audit.GoogleMerchantAdapter") as ga, \
         patch("feeds.digest.run_audit.KlaviyoAdapter") as ka, \
         patch("feeds.digest.run_audit.ShopperApprovedAdapter") as sa, \
         patch("feeds.digest.run_audit.RedditAdapter") as ra, \
         patch("feeds.digest.run_audit.FacebookAdapter") as fa, \
         patch("feeds.digest.run_audit.PinterestAdapter") as pa:

        from feeds.adapters.base_adapter import AdapterResult, CoverageResult, DriftResult, QualityResult
        mock_result = AdapterResult(
            channel="walmart",
            coverage=CoverageResult(wc_total=10, channel_total=8, missing_skus=["A", "B"]),
            drift=DriftResult(drifted=[]),
            quality=QualityResult(incomplete=[]),
        )
        for adapter_cls in [wa, aa, ga, ka, sa, ra, fa, pa]:
            instance = MagicMock()
            instance.channel = "walmart"
            instance.run.return_value = mock_result
            adapter_cls.return_value = instance

        run_audit()

    results_path = digest_dir / "latest_results.json"
    assert results_path.exists(), "latest_results.json not written"
    data = json.loads(results_path.read_text())
    assert isinstance(data, list)
    assert data[0]["channel"] == "walmart"
    assert data[0]["coverage"]["wc_total"] == 10
