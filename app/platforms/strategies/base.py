"""Base class for price extraction strategies."""
from abc import ABC, abstractmethod
from typing import Any


class PriceExtractionStrategy(ABC):
    """Abstract base class for price extraction strategies.

    A price extraction strategy knows how to extract price data from a
    Playwright page object. Different strategies use different techniques
    (CSS selectors, JavaScript evaluation, etc.).

    All concrete implementations must implement the `extract` method.
    """

    @abstractmethod
    async def extract(self, page) -> dict[str, Any]:
        """Extract price from a Playwright page.

        Args:
            page: A Playwright page object.

        Returns:
            A dict containing:
                - success: bool indicating if extraction succeeded
                - price: float the extracted price value
                - currency: str currency code (e.g., "CNY")
                - method: str name of the extraction method used
        """
        pass
