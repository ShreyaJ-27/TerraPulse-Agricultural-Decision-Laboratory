from __future__ import annotations

from app.services.soil.adapter import (
    PROPERTY_METADATA,
    SoilGridsAdapter,
    classify_usda_texture,
)
from app.services.soil.client import (
    DEFAULT_SOILGRIDS_DEPTHS,
    DEFAULT_SOILGRIDS_PROPERTIES,
    DEFAULT_SOILGRIDS_VALUES,
    SoilGridsClient,
)
from app.services.soil.exceptions import (
    InvalidCoordinatesError,
    SoilAdapterError,
    SoilNetworkError,
    SoilProviderError,
    SoilResponseMalformedError,
    SoilTimeoutError,
)
from app.services.soil.models import (
    SoilDepthObservation,
    SoilLayerProperty,
    SoilResult,
)

__all__ = [
    "DEFAULT_SOILGRIDS_DEPTHS",
    "DEFAULT_SOILGRIDS_PROPERTIES",
    "DEFAULT_SOILGRIDS_VALUES",
    "PROPERTY_METADATA",
    "InvalidCoordinatesError",
    "SoilAdapterError",
    "SoilDepthObservation",
    "SoilGridsAdapter",
    "SoilGridsClient",
    "SoilLayerProperty",
    "SoilNetworkError",
    "SoilProviderError",
    "SoilResponseMalformedError",
    "SoilResult",
    "SoilTimeoutError",
    "classify_usda_texture",
]
