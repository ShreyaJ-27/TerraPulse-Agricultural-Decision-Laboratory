from __future__ import annotations

import logging
import math
from datetime import UTC, datetime
from typing import Any

from app.contracts import (
    Availability,
    Coordinates,
    DataStatus,
    Measurement,
    Provenance,
    SoilProperties,
)
from app.services.soil.client import DEFAULT_SOILGRIDS_DEPTHS, SoilGridsClient
from app.services.soil.exceptions import InvalidCoordinatesError, SoilResponseMalformedError
from app.services.soil.models import (
    SoilDepthObservation,
    SoilLayerProperty,
    SoilResult,
)
from app.services.soil.wcs import SoilGridsWcsClient, depth_bounds

logger = logging.getLogger("terrapulse.soil.adapter")

# Authoritative conversion and validation rules for SoilGrids properties
PROPERTY_METADATA: dict[str, dict[str, Any]] = {
    "clay": {
        "divisor": 10.0,
        "target_unit": "%",
        "min": 0.0,
        "max": 100.0,
        "description": "Clay particle fraction (< 2 um)",
    },
    "silt": {
        "divisor": 10.0,
        "target_unit": "%",
        "min": 0.0,
        "max": 100.0,
        "description": "Silt particle fraction (2 - 50 um)",
    },
    "sand": {
        "divisor": 10.0,
        "target_unit": "%",
        "min": 0.0,
        "max": 100.0,
        "description": "Sand particle fraction (50 - 2000 um)",
    },
    "phh2o": {
        "divisor": 10.0,
        "target_unit": "pH",
        "min": 0.0,
        "max": 14.0,
        "description": "Soil pH in H2O",
    },
    "soc": {
        "divisor": 10.0,
        "target_unit": "g/kg",
        "min": 0.0,
        "max": 1000.0,
        "description": "Soil organic carbon content",
    },
    "bdod": {
        "divisor": 100.0,
        "target_unit": "g/cm3",
        "min": 0.05,
        "max": 3.0,
        "description": "Bulk density of fine earth",
    },
    "cfvo": {
        "divisor": 10.0,
        "target_unit": "%",
        "min": 0.0,
        "max": 100.0,
        "description": "Coarse fragments (volumetric)",
    },
    "nitrogen": {
        "divisor": 100.0,
        "target_unit": "g/kg",
        "min": 0.0,
        "max": 100.0,
        "description": "Total nitrogen",
    },
    "wv0033": {
        "divisor": 1000.0,
        "target_unit": "m3/m3",
        "min": 0.0,
        "max": 1.0,
        "description": "Volumetric water content at 33 kPa (Field Capacity)",
    },
    "wv1500": {
        "divisor": 1000.0,
        "target_unit": "m3/m3",
        "min": 0.0,
        "max": 1.0,
        "description": "Volumetric water content at 1500 kPa (Wilting Point)",
    },
}

# Standard NoData sentinels returned by GIS rasters/services
NODATA_SENTINELS: set[float] = {-32768, -9999, -32768.0, -9999.0}


def classify_usda_texture(sand: float, silt: float, clay: float) -> str | None:
    """Classify sand, silt, and clay percentages into the USDA 12 soil texture classes."""
    total = sand + silt + clay
    if total <= 0:
        return None

    # Normalize to 100%
    s = (sand / total) * 100.0
    si = (silt / total) * 100.0
    c = (clay / total) * 100.0

    if s >= 85 and si + 1.5 * c < 15:
        return "sand"
    if s >= 70 and s <= 90 and si + 1.5 * c >= 15 and si + 2 * c < 30:
        return "loamy sand"
    if (c < 20 and s > 52 and si + 2 * c >= 30) or (
        c < 7 and si < 50 and s >= 43 and s <= 52
    ):
        return "sandy loam"
    if c >= 7 and c < 27 and si >= 28 and si < 50 and s <= 52:
        return "loam"
    if (si >= 50 and c >= 12 and c < 27) or (si >= 50 and si < 80 and c < 12):
        return "silt loam"
    if si >= 80 and c < 12:
        return "silt"
    if c >= 20 and c < 35 and si < 28 and s > 45:
        return "sandy clay loam"
    if c >= 27 and c < 40 and s > 20 and s <= 45:
        return "clay loam"
    if c >= 27 and c < 40 and s <= 20:
        return "silty clay loam"
    if c >= 35 and s > 45:
        return "sandy clay"
    if c >= 40 and si >= 40:
        return "silty clay"
    if c >= 40 and s <= 45 and si < 40:
        return "clay"
    return "loam"


def _build_measurement(
    val: float | None,
    unit: str,
    property_name: str,
    min_val: float | None = None,
    max_val: float | None = None,
) -> Measurement:
    """Safely build a C1 Measurement ensuring missing data never becomes zero and units are preserved."""
    if val is None:
        return Measurement(
            value=None,
            unit=unit,
            availability=Availability(
                status=DataStatus.MISSING,
                reason=f"{property_name} missing from provider",
            ),
        )

    try:
        num = float(val)
    except (ValueError, TypeError):
        return Measurement(
            value=None,
            unit=unit,
            availability=Availability(
                status=DataStatus.INVALID,
                reason=f"Unparseable numeric value '{val}' for {property_name}",
            ),
        )

    if (min_val is not None and num < min_val) or (max_val is not None and num > max_val):
        return Measurement(
            value=None,
            unit=unit,
            availability=Availability(
                status=DataStatus.INVALID,
                reason=f"{property_name} value {num} exceeds physical bounds [{min_val}, {max_val}]",
            ),
        )

    return Measurement(
        value=round(num, 4),
        unit=unit,
        availability=Availability(status=DataStatus.AVAILABLE),
    )


class SoilGridsAdapter:
    """Adapter for retrieving, normalizing, and attributing soil data from ISRIC SoilGrids v2.0."""

    def __init__(self, client: SoilGridsClient | SoilGridsWcsClient | None = None) -> None:
        self.client = client or SoilGridsWcsClient()

    def _validate_coordinates(self, latitude: float, longitude: float) -> None:
        """Validate latitude and longitude against geographic WGS 84 bounds."""
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            raise InvalidCoordinatesError(
                f"Coordinates out of bounds: latitude={latitude} must be in [-90, 90], "
                f"longitude={longitude} must be in [-180, 180]."
            )

    def _parse_layers(
        self, layers_payload: list[dict[str, Any]]
    ) -> dict[str, SoilLayerProperty]:
        """Parse raw SoilGrids GeoJSON layers into structured SoilLayerProperty models."""
        parsed_layers: dict[str, SoilLayerProperty] = {}

        for layer_dict in layers_payload:
            prop_name = layer_dict.get("name")
            if not prop_name:
                continue

            unit_measure = layer_dict.get("unit_measure", {})
            mapped_units = unit_measure.get("mapped_units")
            target_units = unit_measure.get("target_units")

            meta = PROPERTY_METADATA.get(prop_name, {})
            divisor = meta.get("divisor", float(unit_measure.get("d_factor", 1.0) or 1.0))
            expected_unit = meta.get("target_unit", target_units or "unknown")

            depths_list: list[SoilDepthObservation] = []
            for depth_dict in layer_dict.get("depths", []):
                label = depth_dict.get("label", "unknown")
                rng = depth_dict.get("range", {})
                top_d = float(rng.get("top_depth", 0))
                bottom_d = float(rng.get("bottom_depth", 0))

                values = depth_dict.get("values", {})
                raw_mean = values.get("mean")
                uncertainty = values.get("uncertainty")

                # Handle raw quantiles
                quantiles: dict[str, float | None] = {}
                for q_key in ("Q0.05", "Q0.5", "Q0.95"):
                    q_raw = values.get(q_key)
                    quantiles[q_key] = (
                        round(float(q_raw) / divisor, 4) if q_raw is not None else None
                    )

                if raw_mean is None or (
                    isinstance(raw_mean, (int, float)) and raw_mean in NODATA_SENTINELS
                ):
                    converted_val = None
                    avail = Availability(
                        status=DataStatus.MISSING,
                        reason=f"No observation reported for {prop_name} at {label}",
                    )
                else:
                    try:
                        raw_num = float(raw_mean)
                        if raw_num in NODATA_SENTINELS:
                            converted_val = None
                            avail = Availability(
                                status=DataStatus.MISSING,
                                reason=f"NoData sentinel ({raw_num}) reported for {prop_name} at {label}",
                            )
                        else:
                            converted_val = round(raw_num / divisor, 4)
                            min_v, max_v = meta.get("min"), meta.get("max")
                            if (min_v is not None and converted_val < min_v) or (
                                max_v is not None and converted_val > max_v
                            ):
                                avail = Availability(
                                    status=DataStatus.INVALID,
                                    reason=f"{prop_name} value {converted_val} exceeds bounds [{min_v}, {max_v}]",
                                )
                            else:
                                avail = Availability(status=DataStatus.AVAILABLE)
                    except (ValueError, TypeError):
                        converted_val = None
                        avail = Availability(
                            status=DataStatus.INVALID,
                            reason=f"Malformed numeric value '{raw_mean}' for {prop_name}",
                        )

                depths_list.append(
                    SoilDepthObservation(
                        depthLabel=label,
                        topDepthCm=top_d,
                        bottomDepthCm=bottom_d,
                        rawMean=raw_mean,
                        convertedValue=converted_val,
                        targetUnit=expected_unit,
                        uncertainty=uncertainty,
                        quantiles=quantiles,
                        availability=avail,
                    )
                )

            parsed_layers[prop_name] = SoilLayerProperty(
                propertyName=prop_name,
                mappedUnits=mapped_units,
                targetUnits=expected_unit,
                conversionFactor=divisor,
                depths=depths_list,
            )

        return parsed_layers

    def _aggregate_property_for_depth(
        self,
        layer: SoilLayerProperty | None,
        target_depth_cm: float = 30.0,
        *,
        require_full_profile: bool = False,
    ) -> float | None:
        """Compute depth-weighted mean for a soil property over interval [0, target_depth_cm]."""
        if layer is None or not layer.depths:
            return None

        weighted_sum = 0.0
        total_thickness = 0.0

        for d in layer.depths:
            if d.availability.status != DataStatus.AVAILABLE or d.converted_value is None:
                continue

            # Calculate interval overlap with [0, target_depth_cm]
            interval_top = max(0.0, d.top_depth_cm)
            interval_bottom = min(target_depth_cm, d.bottom_depth_cm)
            overlap = interval_bottom - interval_top

            if overlap > 0:
                weighted_sum += d.converted_value * overlap
                total_thickness += overlap

        if total_thickness > 0:
            if require_full_profile and not math.isclose(total_thickness, target_depth_cm):
                return None
            return round(weighted_sum / total_thickness, 4)

        return None

    async def fetch_soil(
        self,
        latitude: float,
        longitude: float,
        target_depth_cm: float = 30.0,
        properties: list[str] | None = None,
    ) -> SoilResult:
        """Fetch gridded soil data from SoilGrids, normalize units, and compose C1 SoilProperties.

        Args:
            latitude: Latitude coordinate between -90.0 and 90.0 (WGS 84).
            longitude: Longitude coordinate between -180.0 and 180.0 (WGS 84).
            target_depth_cm: Effective profile / root-zone depth in cm (default 30.0 cm).
            properties: Optional subset of SoilGrids property codes to query.

        Returns:
            SoilResult containing C1 SoilProperties, detailed multi-depth layers, and provenance.
        """
        self._validate_coordinates(latitude, longitude)
        if not math.isfinite(target_depth_cm) or target_depth_cm <= 0:
            raise SoilResponseMalformedError("Soil profile depth must be finite and positive.")
        using_wcs = isinstance(self.client, SoilGridsWcsClient)
        depths = (
            [label for label in DEFAULT_SOILGRIDS_DEPTHS if depth_bounds(label)[0] < target_depth_cm]
            if using_wcs else None
        )

        raw_response = await self.client.query_properties(
            lat=latitude,
            lon=longitude,
            properties=properties,
            depths=depths,
        )

        retrieved_at = datetime.now(UTC)
        layers_payload = raw_response.get("properties", {}).get("layers", [])
        parsed_layers = self._parse_layers(layers_payload)

        # 1. Depth Measurement
        depth_m = Measurement(
            value=float(target_depth_cm),
            unit="cm",
            availability=Availability(status=DataStatus.AVAILABLE),
        )

        # 2. Texture Fractions and Classification
        clay_layer = parsed_layers.get("clay")
        silt_layer = parsed_layers.get("silt")
        sand_layer = parsed_layers.get("sand")

        def aggregate(layer: SoilLayerProperty | None) -> float | None:
            return self._aggregate_property_for_depth(
                layer, target_depth_cm, require_full_profile=using_wcs
            )

        clay_val = aggregate(clay_layer)
        silt_val = aggregate(silt_layer)
        sand_val = aggregate(sand_layer)

        texture_class: str | None = None
        if clay_val is not None and silt_val is not None and sand_val is not None:
            texture_class = classify_usda_texture(sand=sand_val, silt=silt_val, clay=clay_val)

        # 3. Field Capacity (wv0033)
        fc_layer = parsed_layers.get("wv0033")
        fc_val = aggregate(fc_layer)
        fc_m = _build_measurement(
            fc_val,
            unit="m3/m3",
            property_name="fieldCapacity",
            min_val=0.0,
            max_val=1.0,
        )

        # 4. Wilting Point (wv1500)
        wp_layer = parsed_layers.get("wv1500")
        wp_val = aggregate(wp_layer)
        wp_m = _build_measurement(
            wp_val,
            unit="m3/m3",
            property_name="wiltingPoint",
            min_val=0.0,
            max_val=1.0,
        )

        # 5. Bulk Density (bdod)
        bd_layer = parsed_layers.get("bdod")
        bd_val = aggregate(bd_layer)
        bd_m: Measurement | None = None
        if bd_layer is not None:
            bd_m = _build_measurement(
                bd_val,
                unit="g/cm3",
                property_name="bulkDensity",
                min_val=0.05,
                max_val=3.0,
            )

        # Compose authoritative C1 SoilProperties
        c1_soil = SoilProperties(
            depthCm=depth_m,
            texture=texture_class,
            fieldCapacity=fc_m,
            wiltingPoint=wp_m,
            bulkDensity=bd_m,
        )

        # Check overall soil availability based on mandatory C1 fields
        if (
            depth_m.availability.status != DataStatus.AVAILABLE
            or fc_m.availability.status != DataStatus.AVAILABLE
            or wp_m.availability.status != DataStatus.AVAILABLE
        ):
            overall_avail = Availability(
                status=DataStatus.MISSING,
                reason="One or more mandatory soil hydraulic parameters (field capacity, wilting point) are missing.",
            )
        elif fc_val is not None and wp_val is not None and fc_val <= wp_val:
            overall_avail = Availability(
                status=DataStatus.INVALID,
                reason="Field capacity must exceed wilting point.",
            )
        else:
            overall_avail = Availability(status=DataStatus.AVAILABLE)

        # Build Provenance (explicitly identifying data as gridded/modelled, not in-situ field measurement)
        source_id = self.client.source_id if using_wcs else "isric:soilgrids"
        service = self.client.service_name if using_wcs else "SoilGrids REST API v2.0"
        coverages = {
            depth["coverage"]: depth["error"] or (
                "NoData" if depth["values"]["mean"] is None else "sampled"
            )
            for layer in layers_payload for depth in layer["depths"]
        } if using_wcs else {}
        sampled = [name for name, status in coverages.items() if status == "sampled"]
        reference = "https://www.isric.org/explore/soilgrids (modelled gridded soil predictions at 250m resolution)"
        if using_wcs:
            reference = (
                f"{self.client.api_url} (SoilGrids 250m modelled mean predictions, WCS 2.0.1, "
                f"WGS84 pixel containing {latitude}, {longitude}, requested profile 0–{target_depth_cm:g} cm. "
                f"Sampled coverages: {', '.join(sampled) or 'none'}.)"
            )
        provenance = [
            Provenance(
                sourceId=source_id,
                sourceVersion="v2.0",
                retrievedAt=retrieved_at,
                reference=reference,
            )
        ]

        coords = Coordinates(latitude=latitude, longitude=longitude, crs="EPSG:4326")

        return SoilResult(
            location=coords,
            profileDepthCm=target_depth_cm,
            soilProperties=c1_soil,
            layers=parsed_layers,
            dataSourceIds=[source_id],
            provenance=provenance,
            retrievedAt=retrieved_at,
            availability=overall_avail,
            rawMetadata={
                "provider": "ISRIC - World Soil Information",
                "service": service,
                "endpoint": self.client.api_url,
                "model": "SoilGrids 250m",
                "dataType": "modelled_gridded",
                **({"coverages": coverages} if using_wcs else {}),
                "citation": "Poggio et al. (2021) SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. SOIL 7, 217-240",
            },
        )
