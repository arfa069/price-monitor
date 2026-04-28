"""Platform adapters package."""
from app.platforms.amazon import AmazonAdapter
from app.platforms.base import BasePlatformAdapter
from app.platforms.boss import BossZhipinAdapter
from app.platforms.jd import JDAdapter
from app.platforms.taobao import TaobaoAdapter

__all__ = ["BasePlatformAdapter", "TaobaoAdapter", "JDAdapter", "AmazonAdapter", "BossZhipinAdapter"]
