"""Chained price extraction strategy - tries strategies in sequence."""

from app.platforms.strategies.base import PriceExtractionStrategy


class ChainedPriceStrategy(PriceExtractionStrategy):
    """Chains multiple price extraction strategies together.

    Tries each strategy in order, returning the first successful result.
    Useful for combining primary (CSS selectors) with fallback (JS deep scan)
    extraction methods.
    """

    def __init__(self, strategies: list[PriceExtractionStrategy]):
        """Initialize with a list of strategies to try in order.

        Args:
            strategies: List of PriceExtractionStrategy instances.
                       Earlier strategies have higher priority.
        """
        self.strategies = strategies

    async def extract(self, page) -> dict:
        """Try each strategy in order, return first successful result.

        Args:
            page: Playwright page object.

        Returns:
            Dict with success, price, currency, method keys from first
            successful strategy, or failure dict if all strategies fail.
        """
        for strategy in self.strategies:
            result = await strategy.extract(page)
            if result.get("success"):
                return result

        return {"success": False, "error": "All chained strategies failed"}
