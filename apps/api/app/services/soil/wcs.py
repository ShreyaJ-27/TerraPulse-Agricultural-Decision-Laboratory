from __future__ import annotations

import asyncio
import math
from io import BytesIO
from typing import Any

import httpx
from PIL import Image

from app.core.config import get_settings
from app.services.soil.client import DEFAULT_SOILGRIDS_DEPTHS, DEFAULT_SOILGRIDS_PROPERTIES
from app.services.soil.exceptions import SoilResponseMalformedError, SoilTimeoutError

WGS84 = "http://www.opengis.net/def/crs/EPSG/0/4326"
PROFILE_PROPERTIES = ("wv0033", "wv1500", "clay", "silt", "sand", "bdod")
MAX_RASTER_BYTES = 256 * 1024


def depth_bounds(label: str) -> tuple[int, int]:
    top, bottom = label.removesuffix("cm").split("-")
    return int(top), int(bottom)


def sample_geotiff(content: bytes, latitude: float, longitude: float) -> int | None:
    """Read the cell containing the coordinate from an ISRIC WGS84 raster."""
    try:
        with Image.open(BytesIO(content), formats=["TIFF"]) as raster:
            if raster.mode != "I" or max(raster.size) > 256:
                raise ValueError("expected a small signed integer raster")
            tags = raster.tag_v2
            if (tags.get(258), tags.get(339)) != ((16,), (2,)):
                raise ValueError("expected signed 16-bit samples")
            # GeoKeyDirectory entries are (key, tag location, count, value).
            directory = tags[34735]
            keys = {
                key: value
                for key, location, count, value in zip(
                    directory[4::4], directory[5::4], directory[6::4], directory[7::4]
                )
                if location == 0 and count == 1
            }
            if keys.get(2048) != 4326 or keys.get(1025) != 1 or 34264 in tags:
                raise ValueError("expected north-up WGS84 pixel-area georeferencing")
            scale_x, scale_y, _ = tags[33550]
            i, j, _, x, y, _ = tags[33922]
            if scale_x <= 0 or scale_y <= 0:
                raise ValueError("invalid pixel scale")
            col = math.floor(i + (longitude - x) / scale_x)
            row = math.floor(j + (y - latitude) / scale_y)
            if not (0 <= col < raster.width and 0 <= row < raster.height):
                raise ValueError("coordinate outside raster")
            value = raster.getpixel((col, row))
            nodata = tags.get(42113)
            return None if nodata is not None and value == float(nodata) else value
    except (OSError, ValueError, TypeError, KeyError, OverflowError, SyntaxError, Image.DecompressionBombError) as exc:
        raise SoilResponseMalformedError("Invalid SoilGrids WCS GeoTIFF.") from exc


class SoilGridsWcsClient:
    """Fetch SoilGrids mean predictions from WCS at the requested WGS84 point."""

    source_id = "isric:soilgrids:wcs"
    service_name = "SoilGrids WCS 2.0.1"

    def __init__(
        self,
        api_url: str | None = None,
        timeout_seconds: float | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.api_url = api_url or settings.soilgrids_wcs_url
        self.timeout_seconds = (
            settings.soilgrids_timeout_seconds if timeout_seconds is None else timeout_seconds
        )
        self._external_client = http_client

    async def _sample(
        self, client: httpx.AsyncClient, prop: str, depth: str, lat: float, lon: float
    ) -> dict[str, Any]:
        coverage = f"{prop}_{depth}_mean"
        params = [
            ("map", f"/map/{prop}.map"),
            ("SERVICE", "WCS"),
            ("VERSION", "2.0.1"),
            ("REQUEST", "GetCoverage"),
            ("COVERAGEID", coverage),
            ("FORMAT", "GEOTIFF_INT16"),
            ("SUBSET", f"Lat({max(-90, lat - .004)},{min(90, lat + .004)})"),
            ("SUBSET", f"Long({max(-180, lon - .004)},{min(180, lon + .004)})"),
            ("SUBSETTINGCRS", WGS84),
            ("OUTPUTCRS", WGS84),
        ]
        value = None
        error = None
        try:
            async with client.stream("GET", self.api_url, params=params) as response:
                response.raise_for_status()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(content) + len(chunk) > MAX_RASTER_BYTES:
                        raise SoilResponseMalformedError("SoilGrids WCS raster exceeded size limit.")
                    content.extend(chunk)
            value = sample_geotiff(content, lat, lon)
            if value is None or value in {-32768, -9999}:
                value, error = None, "NoData at the requested coordinate"
            elif value == 0 and prop in {"bdod", "wv0033", "wv1500"}:
                value, error = None, "Zero is invalid for this soil property"
        except httpx.HTTPStatusError as exc:
            error = f"HTTP {exc.response.status_code}"
        except httpx.TimeoutException:
            error = "request timed out"
        except httpx.RequestError:
            error = "network request failed"
        except SoilResponseMalformedError:
            error = "invalid GeoTIFF"

        top, bottom = depth_bounds(depth)
        return {
            "label": depth,
            "range": {"top_depth": top, "bottom_depth": bottom},
            "values": {"mean": value},
            "coverage": coverage,
            "error": error,
        }

    async def query_properties(
        self,
        lat: float,
        lon: float,
        properties: list[str] | None = None,
        depths: list[str] | None = None,
    ) -> dict[str, Any]:
        props = list(dict.fromkeys(properties if properties is not None else PROFILE_PROPERTIES))
        intervals = list(dict.fromkeys(depths if depths is not None else DEFAULT_SOILGRIDS_DEPTHS))
        if set(props) - set(DEFAULT_SOILGRIDS_PROPERTIES) or set(intervals) - set(DEFAULT_SOILGRIDS_DEPTHS):
            raise SoilResponseMalformedError("Unknown SoilGrids property or depth interval.")

        async def fetch(client: httpx.AsyncClient) -> dict[str, Any]:
            # Prioritize hydraulic layers while bounding concurrent upstream requests.
            slots = asyncio.Semaphore(6)

            async def sample(prop: str, depth: str) -> dict[str, Any]:
                async with slots:
                    return await self._sample(client, prop, depth, lat, lon)

            tasks = [(prop, depth) for prop in props for depth in intervals]
            pending = {
                asyncio.create_task(sample(prop, depth)): (prop, depth)
                for prop, depth in tasks
            }
            layers: dict[str, list] = {prop: [] for prop in props}
            if pending:
                try:
                    done, _ = await asyncio.wait(pending, timeout=self.timeout_seconds)
                finally:
                    for task in pending:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)
                for task, (prop, depth) in pending.items():
                    if task in done:
                        layers[prop].append(task.result())
                    else:
                        top, bottom = depth_bounds(depth)
                        layers[prop].append({
                            "label": depth,
                            "range": {"top_depth": top, "bottom_depth": bottom},
                            "values": {"mean": None},
                            "coverage": f"{prop}_{depth}_mean",
                            "error": "profile request timed out",
                        })
                if not done:
                    raise SoilTimeoutError("SoilGrids WCS profile request timed out.")
            return {"properties": {"layers": [
                {"name": prop, "depths": observations} for prop, observations in layers.items()
            ]}}

        if self._external_client is not None:
            return await fetch(self._external_client)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            return await fetch(client)
