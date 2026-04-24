"""Pipeline configuration — reads from .env via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///content_pipeline.db"

    # WordPress / WooCommerce — shared base URL
    wc_base_url: str = ""
    wp_username: str = ""
    wp_app_password: str = ""
    wc_ck: str = ""
    wc_cs: str = ""

    # Google Ads API
    google_cloud_project: str = ""
    google_ads_developer_token: str = ""
    google_ads_customer_id: str = ""
    google_ads_login_customer_id: str = ""

    # Google Search Console
    gsc_property_url: str = ""

    # DataForSEO (feature-gated — leave blank to disable)
    dataforseo_login: str = ""
    dataforseo_password: str = ""

    # YouTube
    youtube_api_key: str = ""

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "naturesseed-content-pipeline/1.0"

    # Anthropic
    anthropic_api_key: str = ""

    # OpenAI (image generation, vision)
    openai_api_key: str = ""
    stability_api_key: str = ""

    # Image settings
    image_max_width: int = 1600
    image_similarity_threshold: float = 0.6

    # Media sources config
    media_sources_config: str = "config/media_sources.yaml"

    # Keyword scoring weights (0-1, must sum to ~1.0 for interpretability)
    score_weight_volume: float = 0.25
    score_weight_intent: float = 0.20
    score_weight_difficulty: float = 0.15
    score_weight_gap: float = 0.20
    score_weight_seasonality: float = 0.10
    score_weight_media: float = 0.10

    # Research provider routing — which provider to prefer per method
    research_provider_priority: dict[str, list[str]] = {
        "volume": ["google_ads", "dataforseo"],
        "expand": ["google_ads"],
        "difficulty": ["dataforseo", "google_ads"],
        "serp": ["dataforseo"],
        "related": ["google_ads"],
        "seasonality": ["google_ads", "trends"],
        "competitor_domains": ["google_ads"],
    }

    @property
    def db_path(self) -> Path:
        return Path(self.database_url.replace("sqlite:///", ""))

    @property
    def wp_api_base(self) -> str:
        return f"{self.wc_base_url.rstrip('/')}/wp-json/wp/v2"

    @property
    def wc_api_base(self) -> str:
        return f"{self.wc_base_url.rstrip('/')}/wp-json/wc/v3"

    @property
    def dataforseo_available(self) -> bool:
        return bool(self.dataforseo_login and self.dataforseo_password)

    @property
    def google_ads_available(self) -> bool:
        return bool(self.google_ads_developer_token and self.google_ads_customer_id)

    @property
    def gsc_available(self) -> bool:
        return bool(self.gsc_property_url)


settings = Settings()
