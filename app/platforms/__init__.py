"""Platform adapters package."""
from app.platforms.base import BasePlatformAdapter
from app.platforms.taobao import TaobaoAdapter
from app.platforms.jd import JDAdapter
from app.platforms.amazon import AmazonAdapter

__all__ = ["BasePlatformAdapter", "TaobaoAdapter", "JDAdapter", "AmazonAdapter"]