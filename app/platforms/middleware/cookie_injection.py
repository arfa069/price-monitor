"""Cookie injection middleware for platform adapters."""


class CookieInjectionMiddleware:
    """Middleware that handles cookie injection for platform adapters.

    Can be mixed into any adapter that needs to inject cookies into
    the browser context. Provides parsing and injection methods.

    Usage:
        class MyAdapter(BasePlatformAdapter, CookieInjectionMiddleware):
            pass
    """

    @staticmethod
    def parse_cookie_string(cookie_str: str, domain: str = None) -> list[dict[str, str]]:
        """Parse cookie string into Playwright cookie format.

        Args:
            cookie_str: Cookie string in format 'key1=val1; key2=val2'
            domain: Cookie domain (default: None, use generic domain)

        Returns:
            List of cookie dicts with name, value, domain, path keys.
        """
        cookies = []
        for pair in cookie_str.split(";"):
            pair = pair.strip()
            if "=" not in pair:
                continue
            name, value = pair.split("=", 1)
            name = name.strip()
            value = value.strip()
            if name:
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": domain if domain else ".generic.com",
                    "path": "/",
                })
        return cookies

    async def inject_cookies(self, context, cookie_str: str, domain: str = ".jd.com"):
        """Parse and inject cookies into browser context.

        Args:
            context: Playwright BrowserContext
            cookie_str: Cookie string to parse and inject
            domain: Cookie domain (default: .jd.com)
        """
        cookies = self.parse_cookie_string(cookie_str)
        # Override domain with provided domain
        for cookie in cookies:
            cookie["domain"] = domain
        if cookies:
            await context.add_cookies(cookies)
