import warnings

from ampel.catalogmatch.base.CatalogMatchUnit import (
    CatalogItem,
    CatalogMatchContextUnit,
    CatalogMatchUnit,
    ConeSearchRequest,
    retry_transient_errors,
)

__all__ = [
    "CatalogItem",
    "CatalogMatchContextUnit",
    "CatalogMatchUnit",
    "ConeSearchRequest",
    "retry_transient_errors",
]

warnings.warn(
    "CatalogMatchUnit has moved; import from ampel.catalogmatch.base.CatalogMatchUnit instead",
    DeprecationWarning,
    stacklevel=2,
)
