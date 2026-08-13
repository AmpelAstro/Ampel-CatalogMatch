import warnings

from ampel.catalogmatch.base.CatalogMatchFilter import CatalogMatchFilter

__all__ = [
    "CatalogMatchFilter",
]

warnings.warn(
    "CatalogMatchFilter has moved; import from ampel.catalogmatch.base.CatalogMatchFilter instead",
    DeprecationWarning,
    stacklevel=2,
)
