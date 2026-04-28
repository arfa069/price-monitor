"""Platform adapter strategies."""
from app.platforms.strategies.base import PriceExtractionStrategy
from app.platforms.strategies.chained import ChainedPriceStrategy
from app.platforms.strategies.css_selector import CSSSelectorStrategy
from app.platforms.strategies.js_deep_scan import JSDeeScanStrategy

__all__ = [
    "PriceExtractionStrategy",
    "CSSSelectorStrategy",
    "JSDeeScanStrategy",
    "ChainedPriceStrategy",
]
