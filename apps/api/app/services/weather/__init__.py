from __future__ import annotations

from app.services.weather.adapter import OpenMeteoWeatherAdapter, normalize_member_id
from app.services.weather.client import OpenMeteoClient
from app.services.weather.exceptions import (
    InvalidCoordinatesError,
    WeatherAdapterError,
    WeatherNetworkError,
    WeatherProviderError,
    WeatherResponseMalformedError,
    WeatherTimeoutError,
)
from app.services.weather.models import SupplementaryDailyWeather, WeatherResult

__all__ = [
    "InvalidCoordinatesError",
    "OpenMeteoClient",
    "OpenMeteoWeatherAdapter",
    "SupplementaryDailyWeather",
    "WeatherAdapterError",
    "WeatherNetworkError",
    "WeatherProviderError",
    "WeatherResponseMalformedError",
    "WeatherResult",
    "WeatherTimeoutError",
    "normalize_member_id",
]
