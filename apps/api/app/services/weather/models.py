from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.contracts import Coordinates, DailyWeather, Measurement, Provenance
from pydantic import BaseModel, ConfigDict, Field


class SupplementaryDailyWeather(BaseModel):
    """Supplementary agricultural weather parameters beyond core DailyWeather."""

    date: date
    ensemble_member_id: str | None = Field(default=None, alias="ensembleMemberId")
    relative_humidity_mean: Measurement | None = Field(
        default=None, alias="relativeHumidityMean"
    )
    wind_speed_max: Measurement | None = Field(default=None, alias="windSpeedMax")
    wind_direction_dominant: Measurement | None = Field(
        default=None, alias="windDirectionDominant"
    )
    shortwave_radiation_sum: Measurement | None = Field(
        default=None, alias="shortwaveRadiationSum"
    )
    model_config = ConfigDict(populate_by_name=True)


class WeatherResult(BaseModel):
    """Normalized output of the Open-Meteo weather and ensemble data adapter."""

    location: Coordinates
    timezone: str
    elevation_m: float | None = Field(default=None, alias="elevationM")
    retrieved_at: datetime = Field(alias="retrievedAt")

    # Deterministic forecast data
    deterministic_daily: list[DailyWeather] = Field(
        default_factory=list, alias="deterministicDaily"
    )
    deterministic_supplementary: list[SupplementaryDailyWeather] = Field(
        default_factory=list, alias="deterministicSupplementary"
    )
    deterministic_available: bool = Field(default=True, alias="deterministicAvailable")
    deterministic_error: str | None = Field(default=None, alias="deterministicError")

    # Ensemble forecast data (member_id -> list of DailyWeather)
    ensemble_members: dict[str, list[DailyWeather]] = Field(
        default_factory=dict, alias="ensembleMembers"
    )
    ensemble_supplementary: dict[str, list[SupplementaryDailyWeather]] = Field(
        default_factory=dict, alias="ensembleSupplementary"
    )
    ensemble_available: bool = Field(default=True, alias="ensembleAvailable")
    ensemble_error: str | None = Field(default=None, alias="ensembleError")

    # Attribution and Provenance
    data_source_ids: list[str] = Field(default_factory=list, alias="dataSourceIds")
    provenance: list[Provenance] = Field(default_factory=list)
    raw_metadata: dict[str, Any] = Field(default_factory=dict, alias="rawMetadata")

    model_config = ConfigDict(populate_by_name=True)

    def get_daily_weather_for_member(
        self, member_id: str | None = None
    ) -> list[DailyWeather]:
        """Retrieve DailyWeather list for a specific ensemble member, or deterministic if member_id is None."""
        if member_id is None:
            return self.deterministic_daily
        return self.ensemble_members.get(member_id, [])

    def all_daily_weather(self) -> list[DailyWeather]:
        """Return consolidated list of all daily weather records (deterministic + all ensemble members)."""
        records = list(self.deterministic_daily)
        for member_records in self.ensemble_members.values():
            records.extend(member_records)
        return records
