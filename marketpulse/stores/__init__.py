"""Conectores de tiendas para MarketPulse."""

from marketpulse.stores.base import BaseStoreProvider
from marketpulse.stores.pccomponentes import PcComponentesProvider
from marketpulse.stores.amazon_es import AmazonEsProvider
from marketpulse.stores.mediamarkt import MediaMarktProvider
from marketpulse.stores.aliexpress_es import AliExpressEsProvider
from marketpulse.stores.wallapop import WallapopProvider
from marketpulse.stores.cex_es import CexProvider
from marketpulse.stores.backmarket_es import BackMarketProvider

__all__ = [
    "BaseStoreProvider",
    "PcComponentesProvider",
    "AmazonEsProvider",
    "MediaMarktProvider",
    "AliExpressEsProvider",
    "WallapopProvider",
    "CexProvider",
    "BackMarketProvider",
]
