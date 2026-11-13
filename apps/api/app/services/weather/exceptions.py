from __future__ import annotations


class WeatherAdapterError(Exception):
    """Base exception for all weather adapter errors."""


class InvalidCoordinatesError(ValueError, WeatherAdapterError):
    """Raised when latitude or longitude coordinates fail geographic bounds validation."""


class WeatherNetworkError(WeatherAdapterError):
    """Raised when communication with Open-Meteo fails due to network transport issues."""


class WeatherTimeoutError(WeatherAdapterError):
    """Raised when a request to Open-Meteo times out."""


class WeatherProviderError(WeatherAdapterError):
    """Raised when Open-Meteo returns an error response (HTTP 4xx or 5xx or payload error)."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class WeatherResponseMalformedError(WeatherAdapterError):
    """Raised when Open-Meteo returns a payload missing mandatory fields or invalid JSON."""
