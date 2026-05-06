"""Application configuration using Pydantic Settings."""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_env_file = next(
    (p for p in (
        Path(__file__).parent.parent.parent / ".env",
        Path(__file__).parent.parent / ".env",
    ) if p.exists()),
    None,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = SettingsConfigDict(env_file=_env_file, extra="ignore")

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

    # Taobao-specific options
    taobao_js_deep_scan_enabled: bool = False

    # Platform cookies (optional, for bypassing login walls)
    jd_cookie: str = ""  # Cookie string for JD login session

    # CDP (Chrome DevTools Protocol) browser connection
    # When enabled, connects to an existing browser via CDP instead of launching a new one.
    # This allows using a real browser session (with cookies/login already set).
    # Usage: start Edge/Chrome with --remote-debugging-port=9222, login to JD, then enable this.
    cdp_enabled: bool = False
    cdp_url: str = "http://127.0.0.1:9222"  # CDP endpoint for existing browser

    # JWT settings
    jwt_secret_key: str = "your-secret-key-change-in-production"

    # App settings
    app_name: str = "Price Monitor"
    debug: bool = False

    # LLM job match settings
    job_match_provider: str = "minimax"
    job_match_model: str = "MiniMax-M2.7"
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimaxi.com/anthropic"
    # Backward-compatible aliases for older configs.
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434"

    @field_validator("jwt_secret_key")
    @classmethod
    def _check_jwt_secret(cls, v: str) -> str:
        if v in ("your-secret-key-change-in-production", "change-this-to-a-random-secret-key", ""):
            raise ValueError(
                "JWT_SECRET_KEY 不能使用默认值。请设置一个随机强密钥，"
                "或在 .env 文件中配置 JWT_SECRET_KEY。"
            )
        return v

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
