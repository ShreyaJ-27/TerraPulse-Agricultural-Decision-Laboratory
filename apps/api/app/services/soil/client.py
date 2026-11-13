from __future__ import annotations

import logging
from typing import Any

import httpx
from app.core.config import get_settings
from app.services.soil.exceptions import (
    SoilNetworkError,
    SoilProviderError,
    SoilResponseMalformedError,
    SoilTimeoutError,
)

logger = logging.getLogger("terrapulse.soil.client")

DEFAULT_SOILGRIDS_PROPERTIES = [
    "clay",
    "silt",
    "sand",
    "bdod",
    "phh2o",
    "soc",
    "cfvo",
    "nitrogen",
    "wv0033",
    "wv1500",
]

DEFAULT_SOILGRIDS_DEPTHS = [
    "0-5cm",
    "5-15cm",
    "15-30cm",
    "30-60cm",
    "60-100cm",
    "100-200cm",
]

DEFAULT_SOILGRIDS_VALUES = ["mean", "Q0.05", "Q0.95", "uncertainty"]


class SoilGridsClient:
    """Async HTTP client for ISRIC SoilGrids REST API v2.0."""

    def __init__(
        self,
        api_url: str | None = None,
        timeout_seconds: float | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.api_url = api_url or settings.soilgrids_api_url
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.soilgrids_timeout_seconds
        )
        self._external_client = http_client

    async def query_properties(
        self,
        lat: float,
        lon: float,
        properties: list[str] | None = None,
        depths: list[str] | None = None,
        values: list[str] | None = None,
    ) -> dict[str, Any]:
        """Query SoilGrids properties/query endpoint for a coordinate point."""
        props = properties or DEFAULT_SOILGRIDS_PROPERTIES
        d_list = depths or DEFAULT_SOILGRIDS_DEPTHS
        v_list = values or DEFAULT_SOILGRIDS_VALUES

        # Construct repeated query parameters
        param_tuples: list[tuple[str, str]] = [("lat", str(lat)), ("lon", str(lon))]
        for p in props:
            param_tuples.append(("property", p))
        for d in d_list:
            param_tuples.append(("depth", d))
        for v in v_list:
            param_tuples.append(("value", v))

        try:
            if self._external_client is not None:
                response = await self._external_client.get(
                    self.api_url, params=param_tuples, timeout=self.timeout_seconds
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.get(self.api_url, params=param_tuples)

            response.raise_for_status()

            try:
                data = response.json()
            except Exception as json_err:
                raise SoilResponseMalformedError(
                    f"SoilGrids returned invalid JSON: {json_err}"
                ) from json_err

            if not isinstance(data, dict):
                raise SoilResponseMalformedError(
                    "SoilGrids returned a non-object JSON response."
                )

            if data.get("error") is True:
                reason = data.get("detail", data.get("reason", "Unknown SoilGrids error"))
                raise SoilProviderError(
                    f"SoilGrids error: {reason}",
                    status_code=response.status_code,
                    response_body=response.text,
                )

            # Validate GeoJSON structure
            props_dict = data.get("properties")
            if not isinstance(props_dict, dict) or "layers" not in props_dict:
                raise SoilResponseMalformedError(
                    "SoilGrids response missing required 'properties.layers' structure."
                )

            if not isinstance(props_dict["layers"], list):
                raise SoilResponseMalformedError(
                    "SoilGrids 'properties.layers' must be a list."
                )

            return data

        except httpx.TimeoutException as exc:
            logger.warning("SoilGrids request timed out after %ss: %s", self.timeout_seconds, exc)
            raise SoilTimeoutError(
                f"SoilGrids request timed out after {self.timeout_seconds}s."
            ) from exc

        except (httpx.ConnectError, httpx.NetworkError) as exc:
            logger.error("SoilGrids network connection error: %s", exc)
            raise SoilNetworkError(
                f"Failed to connect to SoilGrids endpoint: {exc}"
            ) from exc

        except httpx.HTTPStatusError as exc:
            logger.error("SoilGrids HTTP %s error: %s", exc.response.status_code, exc)
            raise SoilProviderError(
                f"SoilGrids returned HTTP {exc.response.status_code}: {exc.response.text}",
                status_code=exc.response.status_code,
                response_body=exc.response.text,
            ) from exc
