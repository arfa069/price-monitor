"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pricemonitor"

    # Redis - supports password in URL format: redis://:password@host:port/0
    # or use separate redis_password field below
    redis_url: str = "redis://localhost:6379/0"
    redis_password: str = ""  # Alternative: specify password separately

    # Feishu (fallback/default webhook)
    feishu_webhook_url: str = ""

    # Crawler settings
    crawl_frequency_hours: int = 1
    data_retention_days: int = 365

    # Proxy settings (optional, for rotating IPs to avoid anti-bot detection)
    crawl_proxy_url: str = ""  # e.g. "http://user:pass@host:port" or "socks5://host:port"
    crawl_proxy_enabled: bool = False

    # App settings
    app_name: str = "Price Monitor"
    debug: bool = False

    @property
    def redis_url_with_password(self) -> str:
        """Build Redis URL with password if redis_password is set."""
        if self.redis_password:
            # Insert password into URL: redis://host:6379/0 -> redis://:password@host:6379/0
            from urllib.parse import urlparse
            parsed = urlparse(self.redis_url)
            return f"redis://:{self.redis_password}@{parsed.hostname}:{parsed.port or 6379}/{parsed.path.lstrip('/')}"
        return self.redis_url


settings = Settings()