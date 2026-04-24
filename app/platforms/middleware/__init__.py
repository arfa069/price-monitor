"""Platform adapter middleware."""
from app.platforms.middleware.cookie_injection import CookieInjectionMiddleware

__all__ = ["CookieInjectionMiddleware"]
