from __future__ import annotations

import logging
from typing import Any

import httpx
from app.core.config import get_settings
from app.services.weather.exceptions import (
    WeatherNetworkError,
    WeatherProviderError,
    WeatherResponseMalformedError,
    WeatherTimeoutError,
)

logger = logging.getLogger("terrapulse.weather.client")


class OpenMeteoClient:
    """Async HTTP client for Open-Meteo forecast and ensemble API endpoints."""

    def __init__(
        self,
        forecast_url: str | None = None,
        ensemble_url: str | None = None,
        timeout_seconds: float | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.forecast_url = forecast_url or settings.open_meteo_forecast_url
        self.ensemble_url = ensemble_url or settings.open_meteo_ensemble_url
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.open_meteo_timeout_seconds
        )
        self._external_client = http_client

    async def _request(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute GET request with standardized error handling and response validation."""
        try:
            if self._external_client is not None:
                response = await self._external_client.get(
                    url, params=params, timeout=self.timeout_seconds
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.get(url, params=params)

            response.raise_for_status()

            try:
                data = response.json()
            except Exception as json_err:
                raise WeatherResponseMalformedError(
                    f"Open-Meteo returned invalid JSON: {json_err}"
                ) from json_err

            if not isinstance(data, dict):
                raise WeatherResponseMalformedError(
                    "Open-Meteo returned a non-object JSON response."
                )

            if data.get("error") is True:
                reason = data.get("reason", "Unknown Open-Meteo error")
                raise WeatherProviderError(
                    f"Open-Meteo error: {reason}",
                    status_code=response.status_code,
                    response_body=response.text,
                )

            if "daily" not in data or not isinstance(data["daily"], dict):
                raise WeatherResponseMalformedError(
                    "Open-Meteo response is missing required 'daily' section."
                )

            if "time" not in data["daily"] or not isinstance(data["daily"]["time"], list):
                raise WeatherResponseMalformedError(
                    "Open-Meteo daily section is missing required 'time' array."
                )

            return data

        except httpx.TimeoutException as exc:
            logger.warning("Open-Meteo request timed out after %ss: %s", self.timeout_seconds, exc)
            raise WeatherTimeoutError(
                f"Open-Meteo request timed out after {self.timeout_seconds}s."
            ) from exc

        except (httpx.ConnectError, httpx.NetworkError) as exc:
            logger.error("Open-Meteo network connection error: %s", exc)
            raise WeatherNetworkError(
                f"Failed to connect to Open-Meteo endpoint: {exc}"
            ) from exc

        except httpx.HTTPStatusError as exc:
            logger.error("Open-Meteo HTTP %s error: %s", exc.response.status_code, exc)
            raise WeatherProviderError(
                f"Open-Meteo returned HTTP {exc.response.status_code}: {exc.response.text}",
                status_code=exc.response.status_code,
                response_body=exc.response.text,
            ) from exc

    async def fetch_forecast(self, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch deterministic forecast data from Open-Meteo."""
        return await self._request(self.forecast_url, params)

    async def fetch_ensemble(self, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch probabilistic ensemble forecast data from Open-Meteo."""
        return await self._request(self.ensemble_url, params)
