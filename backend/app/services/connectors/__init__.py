from app.services.connectors.base import BaseDataConnector, ConnectorResult
from app.services.connectors.http_connectors import (
    GastatConnector, SamaConnector, OpenDataConnector, MinistryEconomyConnector,
    WorldBankConnector, IMFConnector, OECDConnector,
)

CONNECTORS = {
    "gastat": GastatConnector(),
    "sama": SamaConnector(),
    "data-gov-sa": OpenDataConnector(),
    "mep": MinistryEconomyConnector(),
    "world-bank": WorldBankConnector(),
    "imf": IMFConnector(),
    "oecd": OECDConnector(),
}
