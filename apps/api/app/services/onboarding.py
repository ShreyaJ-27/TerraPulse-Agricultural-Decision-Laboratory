from __future__ import annotations

import logging
import re
import struct
from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

from app.contracts import Availability, Coordinates, DataStatus, Measurement
from app.models import CropIdentity, Farm, FarmResource, Plot, ResourcePlotAuthorization
from app.schemas import FarmCreateRequest, FarmResponse, PlotCreateRequest, PlotResponse
from app.services.crop_lens.registry import CROP_REGISTRY, get_crop_by_id
from app.services.farmer_alerts.models import FarmWorkspaceGrant
from app.services.crop_lens.resolver import CandidateMatch, CropLensResolver, ResolutionStatus
from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger("terrapulse.onboarding")


class AmbiguousCropError(Exception):
    def __init__(self, query: str, candidates: list[CandidateMatch], message: str) -> None:
        self.query = query
        self.candidates = candidates
        self.message = message
        super().__init__(message)


def _parse_point_coordinates(location: Any) -> Coordinates:
    """Extract WGS 84 Coordinates from Coordinates, WKTElement, or PostGIS WKBElement."""
    if isinstance(location, Coordinates):
        return location
    loc_str = str(getattr(location, "data", location))
    match = re.search(r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)", loc_str, re.IGNORECASE)
    if match:
        lon, lat = float(match.group(1)), float(match.group(2))
        return Coordinates(latitude=lat, longitude=lon, crs="EPSG:4326")
    if hasattr(location, "data"):
        try:
            data = bytes(location.data)
            if len(data) >= 21:
                byte_order = data[0]
                endian = "<" if byte_order == 1 else ">"
                geom_type = struct.unpack(f"{endian}I", data[1:5])[0]
                offset = 5
                if geom_type & 0x20000000:
                    offset += 4
                lon, lat = struct.unpack(f"{endian}2d", data[offset : offset + 16])
                return Coordinates(latitude=lat, longitude=lon, crs="EPSG:4326")
        except (ValueError, struct.error, TypeError) as exc:
            logger.debug("Failed to unpack WKB geometry: %s", exc)
    return Coordinates(latitude=0.0, longitude=0.0, crs="EPSG:4326")


def _plot_to_response(db_plot: Plot) -> PlotResponse:
    crop_record = get_crop_by_id(db_plot.crop_id) if db_plot.crop_id else None
    canonical_name = crop_record.canonical_name if crop_record else "Unknown"
    scientific_name = crop_record.scientific_name if crop_record else None
    return PlotResponse(
        plotId=db_plot.id,
        farmId=db_plot.farm_id,
        areaM2=Measurement(
            value=float(db_plot.area_m2),
            unit="m2",
            availability=Availability(status=DataStatus.AVAILABLE),
        ),
        cropId=db_plot.crop_id or uuid4(),
        cropCanonicalName=canonical_name,
        cropScientificName=scientific_name,
        plantingDate=db_plot.planting_date,
        geometry=None,
        management=db_plot.management or {},
        sharedResourceIds=[item.resource_id for item in (db_plot.resource_assignments or [])],
    )


def _farm_to_response(db_farm: Farm) -> FarmResponse:
    coords = _parse_point_coordinates(db_farm.location)
    plots = [_plot_to_response(p) for p in (db_farm.plots or [])]
    return FarmResponse(
        farmId=db_farm.id,
        name=db_farm.name,
        timezone=db_farm.timezone,
        location=coords,
        boundary=None,
        plots=plots,
        createdAt=getattr(db_farm, "created_at", None),
    )


class OnboardingService:
    """Service managing farm and plot registration, location validation, and crop identity linking.

    When initialized with an active AsyncSession, reads and writes against PostgreSQL.
    When initialized without a session (session=None), operates in deterministic in-memory mode for unit tests.
    """

    _in_memory_farms: ClassVar[dict[UUID, FarmResponse]] = {}
    _in_memory_plots: ClassVar[dict[UUID, PlotResponse]] = {}

    def __init__(
        self,
        session: AsyncSession | None = None,
        crop_resolver: CropLensResolver | None = None,
    ) -> None:
        self.session = session
        self.crop_resolver = crop_resolver or CropLensResolver(CROP_REGISTRY)

    async def create_farm(self, request: FarmCreateRequest, *, workspace_key_hash: str | None = None) -> FarmResponse:
        farm_id = uuid4()
        now = datetime.now(UTC)

        farm_resp = FarmResponse(
            farmId=farm_id,
            name=request.name.strip(),
            timezone=request.timezone.strip(),
            location=request.location,
            boundary=request.boundary,
            plots=[],
            createdAt=now,
        )

        if self.session is not None:
            loc_wkt = WKTElement(
                f"POINT({request.location.longitude} {request.location.latitude})", srid=4326
            )
            db_farm = Farm(
                id=farm_id,
                name=farm_resp.name,
                timezone=farm_resp.timezone,
                location=loc_wkt,
                boundary=None,
                workspace_key_hash=workspace_key_hash,
            )
            self.session.add(db_farm)
            await self.session.commit()
            return farm_resp

        self._in_memory_farms[farm_id] = farm_resp
        return farm_resp

    async def get_farm(self, farm_id: UUID) -> FarmResponse | None:
        if self.session is not None:
            stmt = select(Farm).where(Farm.id == farm_id).options(
                selectinload(Farm.plots).selectinload(Plot.resource_assignments)
            )
            result = await self.session.execute(stmt)
            db_farm = result.scalar_one_or_none()
            if db_farm is None:
                return None
            return _farm_to_response(db_farm)

        return self._in_memory_farms.get(farm_id)

    async def list_farms(self, *, workspace_key_hash: str | None = None) -> list[FarmResponse]:
        if self.session is not None:
            stmt = select(Farm).options(
                selectinload(Farm.plots).selectinload(Plot.resource_assignments)
            )
            if workspace_key_hash is not None:
                stmt = stmt.where(
                    (Farm.workspace_key_hash == workspace_key_hash)
                    | (Farm.id.in_(select(FarmWorkspaceGrant.farm_id).where(
                        FarmWorkspaceGrant.token_hash == workspace_key_hash,
                    )))
                )
            result = await self.session.execute(stmt)
            return [_farm_to_response(f) for f in result.scalars().all()]

        return list(self._in_memory_farms.values())

    async def create_plot(self, farm_id: UUID, request: PlotCreateRequest) -> PlotResponse:
        farm = await self.get_farm(farm_id)
        if farm is None:
            raise KeyError(f"Farm with ID {farm_id} not found.")

        # Resolve crop identity using Issue #5 CropLens
        resolved_aliases: list[str] = []
        if request.crop_id is not None:
            crop = get_crop_by_id(request.crop_id)
            if crop is None:
                raise ValueError(f"Crop ID '{request.crop_id}' not found in registry.")
            resolved_crop_id = crop.crop_id
            resolved_canonical = crop.canonical_name
            resolved_scientific = crop.scientific_name
            resolved_aliases = list(crop.aliases)
        elif request.crop_query:
            result = self.crop_resolver.resolve(request.crop_query)
            if result.status == ResolutionStatus.EXACT_MATCH and result.crop is not None:
                resolved_crop_id = result.crop.crop_id
                resolved_canonical = result.crop.canonical_name
                resolved_scientific = result.crop.scientific_name
                resolved_aliases = list(result.crop.aliases)
            elif result.status == ResolutionStatus.AMBIGUOUS:
                raise AmbiguousCropError(
                    query=request.crop_query,
                    candidates=result.candidates,
                    message=result.message,
                )
            else:
                raise ValueError(
                    f"Crop identity could not be resolved for query '{request.crop_query}'."
                )
        else:
            raise ValueError("A plot must reference a crop identity.")

        plot_id = uuid4()
        area_measurement = Measurement(
            value=request.area_m2.value,
            unit=request.area_m2.unit,
            availability=Availability(status=DataStatus.AVAILABLE),
        )

        plot_resp = PlotResponse(
            plotId=plot_id,
            farmId=farm_id,
            areaM2=area_measurement,
            cropId=resolved_crop_id,
            cropCanonicalName=resolved_canonical,
            cropScientificName=resolved_scientific,
            plantingDate=request.planting_date,
            geometry=request.geometry,
            management=request.management,
            sharedResourceIds=request.shared_resource_ids,
        )

        if self.session is not None:
            crop_identity = await self.session.get(CropIdentity, resolved_crop_id)
            if crop_identity is None:
                self.session.add(
                    CropIdentity(
                        id=resolved_crop_id,
                        canonical_name=resolved_canonical,
                        scientific_name=resolved_scientific,
                        aliases=resolved_aliases,
                    )
                )
                await self.session.flush()
            resources = await self.session.execute(
                select(FarmResource).where(
                    FarmResource.farm_id == farm_id,
                    FarmResource.id.in_(request.shared_resource_ids),
                )
            )
            if len(resources.scalars().all()) != len(set(request.shared_resource_ids)):
                raise ValueError("RESOURCE_FARM_MISMATCH")
            db_plot = Plot(
                id=plot_id,
                farm_id=farm_id,
                area_m2=request.area_m2.value,
                crop_id=resolved_crop_id,
                planting_date=request.planting_date,
                management=request.management or {},
            )
            self.session.add(db_plot)
            self.session.add_all(
                [
                    ResourcePlotAuthorization(
                        id=uuid4(), resource_id=resource_id, plot_id=plot_id
                    )
                    for resource_id in request.shared_resource_ids
                ]
            )
            await self.session.commit()
            return plot_resp

        self._in_memory_plots[plot_id] = plot_resp
        farm.plots.append(plot_resp)
        return plot_resp

    async def get_plot(self, farm_id: UUID, plot_id: UUID) -> PlotResponse | None:
        if self.session is not None:
            stmt = select(Plot).where(Plot.id == plot_id, Plot.farm_id == farm_id).options(
                selectinload(Plot.resource_assignments)
            )
            result = await self.session.execute(stmt)
            db_plot = result.scalar_one_or_none()
            if db_plot is None:
                return None
            return _plot_to_response(db_plot)

        plot = self._in_memory_plots.get(plot_id)
        if plot is not None and plot.farm_id == farm_id:
            return plot
        return None

    async def list_plots(self, farm_id: UUID) -> list[PlotResponse]:
        farm = await self.get_farm(farm_id)
        if farm is None:
            raise KeyError(f"Farm with ID {farm_id} not found.")

        if self.session is not None:
            stmt = select(Plot).where(Plot.farm_id == farm_id).options(
                selectinload(Plot.resource_assignments)
            )
            result = await self.session.execute(stmt)
            return [_plot_to_response(p) for p in result.scalars().all()]

        return [p for p in self._in_memory_plots.values() if p.farm_id == farm_id]
