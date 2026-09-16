"""Conectores de tiendas para MarketPulse."""

from marketpulse.stores.base import BaseStoreProvider
from marketpulse.stores.pccomponentes import PcComponentesProvider
from marketpulse.stores.amazon_es import AmazonEsProvider
from marketpulse.stores.mediamarkt import MediaMarktProvider
from marketpulse.stores.aliexpress_es import AliExpressEsProvider

__all__ = [
    "BaseStoreProvider",
    "PcComponentesProvider",
    "AmazonEsProvider",
    "MediaMarktProvider",
    "AliExpressEsProvider",
]
