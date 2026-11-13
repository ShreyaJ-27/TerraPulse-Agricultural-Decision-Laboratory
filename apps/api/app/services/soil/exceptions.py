from __future__ import annotations


class SoilAdapterError(Exception):
    """Base exception for all soil adapter errors."""


class InvalidCoordinatesError(ValueError, SoilAdapterError):
    """Raised when latitude or longitude coordinates fail geographic bounds validation."""


class SoilNetworkError(SoilAdapterError):
    """Raised when communication with SoilGrids fails due to network transport issues."""


class SoilTimeoutError(SoilAdapterError):
    """Raised when a request to SoilGrids times out."""


class SoilProviderError(SoilAdapterError):
    """Raised when SoilGrids returns an error response (HTTP 4xx/5xx or provider error)."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class SoilResponseMalformedError(SoilAdapterError):
    """Raised when SoilGrids returns a payload missing mandatory fields or invalid GeoJSON."""
