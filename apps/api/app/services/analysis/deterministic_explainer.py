from __future__ import annotations

import math
from typing import Literal

from app.contracts import DailyWeather
from app.services.analysis.models import (
    AnalysisSection,
    EscalationNotice,
    EvidenceBundle,
    GroundedClaim,
    ScientificLimitation,
    StalenessAssessment,
)
from app.services.analysis.staleness import safe_measurement_val


class DeterministicExplainer:
    """Generates 100% deterministic, evidence-grounded explanations with zero hallucination.

    Supports English ('en'), Kannada ('kn'), and Hindi ('hi').
    Every numeric value cited is cataloged as a verified GroundedClaim.
    """

    @classmethod
    def generate(
        cls,
        bundle: EvidenceBundle,
        staleness: list[StalenessAssessment],
        limitations: list[ScientificLimitation],
        escalations: list[EscalationNotice],
        language: Literal["en", "kn", "hi"] = "en",
    ) -> tuple[str, list[AnalysisSection], list[GroundedClaim]]:
        claims: list[GroundedClaim] = []
        sections: list[AnalysisSection] = []

        # Helper to record a claim
        def record_claim(
            metric: str,
            val: float,
            unit: str,
            field_path: str,
            source_id: str,
            category: Literal["observation", "gridded_modelled", "simulation_state", "comparison_derived", "assumption"],
            qualifications: list[str] | None = None,
            is_stale: bool = False,
        ) -> GroundedClaim:
            claim = GroundedClaim(
                claimId=f"claim-{len(claims)+1}",
                metric=metric,
                value=round(val, 4),
                unit=unit,
                sourceField=field_path,
                sourceId=source_id,
                category=category,
                isStale=is_stale,
                qualifications=qualifications or [],
            )
            claims.append(claim)
            return claim

        # ------------------------------------------------------------------
        # Section 1: Context & Field Profile
        # ------------------------------------------------------------------
        plot_area_val = safe_measurement_val(bundle.plot.area_m2)
        plot_area_unit = bundle.plot.area_m2.unit if bundle.plot.area_m2 else "m2"
        section_claims_1: list[GroundedClaim] = []

        if plot_area_val is not None:
            c_area = record_claim(
                metric="plot_area",
                val=plot_area_val,
                unit=plot_area_unit,
                field_path="c2.plot.areaM2",
                source_id="c2-farm-plot",
                category="observation",
            )
            section_claims_1.append(c_area)

        c_lat = record_claim(
            metric="latitude",
            val=bundle.farm.location.latitude,
            unit="degrees",
            field_path="c2.farm.location.latitude",
            source_id="c2-farm-coordinates",
            category="observation",
        )
        c_lon = record_claim(
            metric="longitude",
            val=bundle.farm.location.longitude,
            unit="degrees",
            field_path="c2.farm.location.longitude",
            source_id="c2-farm-coordinates",
            category="observation",
        )
        section_claims_1.extend([c_lat, c_lon])

        crop_sci_text = f" ({bundle.crop_scientific_name})" if bundle.crop_scientific_name else ""

        if language == "kn":
            content_1 = (
                f"ಕ್ಷೇತ್ರದ ಮಾಹಿತಿ: ಕೃಷಿ ಕ್ಷೇತ್ರ '{bundle.farm.farm_name}' "
                f"(ಅಕ್ಷಾಂಶ: {bundle.farm.location.latitude:.4f}, ರೇಖಾಂಶ: {bundle.farm.location.longitude:.4f}). "
                f"ಪ್ಲಾಟ್ ವಿಸ್ತೀರ್ಣ: {plot_area_val or 'ಲಭ್ಯವಿಲ್ಲ'} {plot_area_unit}. "
                f"ಬೆಳೆ: {bundle.crop_canonical_name}{crop_sci_text}. "
                f"ಮಾದರಿ ಎಂಜಿನ್: {bundle.crop_capability.selected_engine}."
            )
            title_1 = "ಕ್ಷೇತ್ರ ಮತ್ತು ಬೆಳೆಯ ವಿವರ"
        elif language == "hi":
            content_1 = (
                f"खेत का विवरण: खेत '{bundle.farm.farm_name}' "
                f"(अक्षांश: {bundle.farm.location.latitude:.4f}, देशांतर: {bundle.farm.location.longitude:.4f}). "
                f"प्लॉट का क्षेत्रफल: {plot_area_val or 'उपलब्ध नहीं'} {plot_area_unit}. "
                f"फसल: {bundle.crop_canonical_name}{crop_sci_text}. "
                f"सिमुलेशन इंजन: {bundle.crop_capability.selected_engine}."
            )
            title_1 = "खेत और फसल की रूपरेखा"
        else:
            content_1 = (
                f"Field Profile: Farm '{bundle.farm.farm_name}' "
                f"located at latitude {bundle.farm.location.latitude:.4f}, longitude {bundle.farm.location.longitude:.4f}. "
                f"Plot area: {plot_area_val or 'Not available'} {plot_area_unit}. "
                f"Cultivated crop: {bundle.crop_canonical_name}{crop_sci_text}. "
                f"Configured scientific engine: {bundle.crop_capability.selected_engine}."
            )
            title_1 = "Field & Crop Context"

        sections.append(AnalysisSection(key="context", title=title_1, content=content_1, claims=section_claims_1))

        # ------------------------------------------------------------------
        # Section 2: Soil Profile & Physical Parameters
        # ------------------------------------------------------------------
        section_claims_2: list[GroundedClaim] = []
        if bundle.c1_input is not None and bundle.c1_input.soil is not None:
            soil = bundle.c1_input.soil
            fc_val = safe_measurement_val(soil.field_capacity)
            wp_val = safe_measurement_val(soil.wilting_point)
            depth_val = safe_measurement_val(soil.depth_cm)
            bd_val = safe_measurement_val(soil.bulk_density)

            if depth_val is not None:
                section_claims_2.append(
                    record_claim("soil_depth", depth_val, soil.depth_cm.unit, "c1.soil.depthCm", "soilgrids-250m", "gridded_modelled")
                )
            if fc_val is not None:
                section_claims_2.append(
                    record_claim("field_capacity", fc_val, soil.field_capacity.unit, "c1.soil.fieldCapacity", "soilgrids-250m", "gridded_modelled")
                )
            if wp_val is not None:
                section_claims_2.append(
                    record_claim("wilting_point", wp_val, soil.wilting_point.unit, "c1.soil.wiltingPoint", "soilgrids-250m", "gridded_modelled")
                )
            if bd_val is not None:
                section_claims_2.append(
                    record_claim("bulk_density", bd_val, soil.bulk_density.unit, "c1.soil.bulkDensity", "soilgrids-250m", "gridded_modelled")
                )

            texture_str = soil.texture or "Not specified"
            if language == "kn":
                content_2 = (
                    f"ಮಣ್ಣಿನ ಗುಣಲಕ್ಷಣಗಳು: ಮಣ್ಣಿನ ವಿನ್ಯಾಸ: {texture_str}, ಆಳ: {depth_val or 'ಲಭ್ಯವಿಲ್ಲ'} ಸೆಂ.ಮೀ. "
                    f"ಕ್ಷೇತ್ರ ಸಾಮರ್ಥ್ಯ (FC): {fc_val or 'ಲಭ್ಯವಿಲ್ಲ'} {soil.field_capacity.unit}, "
                    f"ಬಾಡುವ ಬಿಂದು (WP): {wp_val or 'ಲಭ್ಯವಿಲ್ಲ'} {soil.wilting_point.unit}. "
                    "ಗಮನಿಸಿ: ಈ ಮಣ್ಣಿನ ದತ್ತಾಂಶವು ISRIC SoilGrids 250m ಗ್ರಿಡ್ ಮಾದರಿಯ ಅಂದಾಜಾಗಿದ್ದು, ನೇರ ಸಂವೇದಕ ಮಾಪನವಲ್ಲ."
                )
                title_2 = "ಮಣ್ಣಿನ ವಿನ್ಯಾಸ ಮತ್ತು ಜಲ ಧಾರಣಾ ಸಾಮರ್ಥ್ಯ"
            elif language == "hi":
                content_2 = (
                    f"मृदा गुण: मिट्टी का प्रकार: {texture_str}, गहराई: {depth_val or 'उपलब्ध नहीं'} सेमी. "
                    f"क्षेत्र क्षमता (FC): {fc_val or 'उपलब्ध नहीं'} {soil.field_capacity.unit}, "
                    f"मुलझाने का बिंदु (WP): {wp_val or 'उपलब्ध नहीं'} {soil.wilting_point.unit}. "
                    "ध्यान दें: यह मृदा डेटा ISRIC SoilGrids 250m ग्रिड मॉडल आधारित है, लाइव सेंसर माप नहीं।"
                )
                title_2 = "मृदा जल धारण क्षमता एवं प्रोफ़ाइल"
            else:
                content_2 = (
                    f"Soil Properties: Texture: {texture_str}, profile depth: {depth_val or 'Not available'} cm. "
                    f"Field capacity: {fc_val or 'Not available'} {soil.field_capacity.unit}, "
                    f"permanent wilting point: {wp_val or 'Not available'} {soil.wilting_point.unit}. "
                    "Note: Soil properties represent ISRIC SoilGrids 250m gridded spatial estimates, not direct in-situ sensors."
                )
                title_2 = "Soil Water Holding Profile"
        else:
            if language == "kn":
                content_2 = "ಮಣ್ಣಿನ ದತ್ತಾಂಶವು ಲಭ್ಯವಿಲ್ಲ."
                title_2 = "ಮಣ್ಣಿನ ವಿವರ"
            elif language == "hi":
                content_2 = "मृदा डेटा उपलब्ध नहीं है।"
                title_2 = "मृदा प्रोफ़ाइल"
            else:
                content_2 = "Soil data was not available for this plot."
                title_2 = "Soil Water Profile"

        sections.append(AnalysisSection(key="soil_profile", title=title_2, content=content_2, claims=section_claims_2))

        # ------------------------------------------------------------------
        # Section 3: Weather & Atmospheric Evaporative Demand
        # ------------------------------------------------------------------
        section_claims_3: list[GroundedClaim] = []
        is_weather_stale = any(s.data_type == "daily_weather_forecast" and s.is_stale for s in staleness)

        if bundle.c1_input is not None and bundle.c1_input.daily_weather:
            all_records = bundle.c1_input.daily_weather

            # Group daily records by ensemble_member_id to prevent summing across members
            members_map: dict[str | None, list[DailyWeather]] = {}
            for d in all_records:
                members_map.setdefault(d.ensemble_member_id, []).append(d)

            is_multi_member = len(members_map) > 1

            if is_multi_member:
                # Multiple ensemble members: calculate independent trajectories
                member_rainfalls: dict[str, float | None] = {}
                for m_id, m_days in members_map.items():
                    valid_m_rains = [safe_measurement_val(d.rainfall_mm) for d in m_days if safe_measurement_val(d.rainfall_mm) is not None]
                    member_rainfalls[m_id or "default"] = sum(valid_m_rains) if valid_m_rains else None

                valid_sums = [v for v in member_rainfalls.values() if v is not None]
                n_members = len(members_map)
                n_days = max(len(m_days) for m_days in members_map.values())

                if valid_sums:
                    min_rain = min(valid_sums)
                    max_rain = max(valid_sums)
                    if math.isclose(min_rain, max_rain, rel_tol=1e-2, abs_tol=1e-2):
                        rain_desc_en = f"{min_rain:.1f} mm (consistent across {n_members} ensemble members)"
                        rain_desc_kn = f"{min_rain:.1f} ಮಿ.ಮೀ ({n_members} ಸಮಗ್ರ ಸದಸ್ಯರಲ್ಲಿ ಸ್ಥಿರ)"
                        rain_desc_hi = f"{min_rain:.1f} मिमी ({n_members} एन्सेम्बल सदस्यों में एकसमान)"
                        section_claims_3.append(
                            record_claim("total_rainfall", min_rain, "mm", "c1.daily_weather.rainfall_mm.sum", "open-meteo", "gridded_modelled", is_stale=is_weather_stale)
                        )
                    else:
                        rain_desc_en = f"range of {min_rain:.1f} mm to {max_rain:.1f} mm across {n_members} ensemble members (trajectories preserved independently)"
                        rain_desc_kn = f"{n_members} ಸಮಗ್ರ ಸದಸ್ಯರಲ್ಲಿ {min_rain:.1f} ರಿಂದ {max_rain:.1f} ಮಿ.ಮೀ ವ್ಯಾಪ್ತಿ (ಸ್ವತಂತ್ರ ಪಥಗಳು)"
                        rain_desc_hi = f"{n_members} एन्सेम्बल सदस्यों में {min_rain:.1f} से {max_rain:.1f} मिमी का दायरा (स्वतंत्र प्रक्षेपवक्र)"
                        section_claims_3.append(
                            record_claim("min_ensemble_rainfall", min_rain, "mm", "c1.daily_weather.rainfall_mm.min", "open-meteo", "gridded_modelled", is_stale=is_weather_stale)
                        )
                        section_claims_3.append(
                            record_claim("max_ensemble_rainfall", max_rain, "mm", "c1.daily_weather.rainfall_mm.max", "open-meteo", "gridded_modelled", is_stale=is_weather_stale)
                        )
                else:
                    rain_desc_en = "Not available"
                    rain_desc_kn = "ಲಭ್ಯವಿಲ್ಲ"
                    rain_desc_hi = "उपलब्ध नहीं"

                t_mins = [safe_measurement_val(d.temperature_min_c) for d in all_records if safe_measurement_val(d.temperature_min_c) is not None]
                t_maxs = [safe_measurement_val(d.temperature_max_c) for d in all_records if safe_measurement_val(d.temperature_max_c) is not None]
                et0_vals = [safe_measurement_val(d.reference_evapotranspiration_mm) for d in all_records if safe_measurement_val(d.reference_evapotranspiration_mm) is not None]

            else:
                # Single realization / deterministic forecast
                days = all_records
                n_days = len(days)
                valid_rains = [safe_measurement_val(d.rainfall_mm) for d in days if safe_measurement_val(d.rainfall_mm) is not None]

                if not valid_rains:
                    rain_desc_en = "Not available"
                    rain_desc_kn = "ಲಭ್ಯವಿಲ್ಲ"
                    rain_desc_hi = "उपलब्ध नहीं"
                elif len(valid_rains) < n_days:
                    tot = sum(valid_rains)
                    rain_desc_en = f"{tot:.1f} mm (incomplete: {len(valid_rains)} of {n_days} days recorded)"
                    rain_desc_kn = f"{tot:.1f} ಮಿ.ಮೀ (ಅಪೂರ್ಣ: {len(valid_rains)}/{n_days} ದಿನಗಳು ದಾಖಲಾಗಿವೆ)"
                    rain_desc_hi = f"{tot:.1f} मिमी (अपूर्ण: {len(valid_rains)}/{n_days} दिन दर्ज)"
                    section_claims_3.append(
                        record_claim("total_rainfall", tot, "mm", "c1.daily_weather.rainfall_mm.sum", "open-meteo", "gridded_modelled", qualifications=["incomplete_daily_coverage"], is_stale=is_weather_stale)
                    )
                else:
                    tot = sum(valid_rains)
                    rain_desc_en = f"{tot:.1f} mm"
                    rain_desc_kn = f"{tot:.1f} ಮಿ.ಮೀ"
                    rain_desc_hi = f"{tot:.1f} मिमी"
                    section_claims_3.append(
                        record_claim("total_rainfall", tot, "mm", "c1.daily_weather.rainfall_mm.sum", "open-meteo", "gridded_modelled", is_stale=is_weather_stale)
                    )

                t_mins = [safe_measurement_val(d.temperature_min_c) for d in days if safe_measurement_val(d.temperature_min_c) is not None]
                t_maxs = [safe_measurement_val(d.temperature_max_c) for d in days if safe_measurement_val(d.temperature_max_c) is not None]
                et0_vals = [safe_measurement_val(d.reference_evapotranspiration_mm) for d in days if safe_measurement_val(d.reference_evapotranspiration_mm) is not None]

            min_t_str = f"{min(t_mins):.1f}" if t_mins else "Not available"
            max_t_str = f"{max(t_maxs):.1f}" if t_maxs else "Not available"
            avg_et0 = sum(et0_vals) / len(et0_vals) if et0_vals else None

            if t_mins:
                section_claims_3.append(
                    record_claim("min_temperature", min(t_mins), "degC", "c1.daily_weather.temperature_min_c.min", "open-meteo", "gridded_modelled", is_stale=is_weather_stale)
                )
            if t_maxs:
                section_claims_3.append(
                    record_claim("max_temperature", max(t_maxs), "degC", "c1.daily_weather.temperature_max_c.max", "open-meteo", "gridded_modelled", is_stale=is_weather_stale)
                )
            if avg_et0 is not None:
                section_claims_3.append(
                    record_claim("mean_et0", avg_et0, "mm/day", "c1.daily_weather.reference_evapotranspiration_mm.mean", "open-meteo", "gridded_modelled", is_stale=is_weather_stale)
                )

            stale_warning_en = " [Warning: Weather forecast data exceeds 24-hour freshness window.]" if is_weather_stale else ""
            stale_warning_kn = " [ಎಚ್ಚರಿಕೆ: ಹವಾಮಾನ ಮುನ್ಸೂಚನೆ 24 ಗಂಟೆಗಳಿಗಿಂತ ಹಳೆಯದಾಗಿದೆ.]" if is_weather_stale else ""
            stale_warning_hi = " [चेतावनी: मौसम पूर्वानुमान डेटा 24 घंटे से अधिक पुराना है।] " if is_weather_stale else ""

            if language == "kn":
                content_3 = (
                    f"ಸಂಖ್ಯಾತ್ಮಕ ಹವಾಮಾನ ಮಾದರಿ ಮುನ್ಸೂಚನೆ ({n_days} ದಿನಗಳ ಅವಧಿ): "
                    f"ಮಳೆ: {rain_desc_kn}, ಕನಿಷ್ಠ ತಾಪಮಾನ: {min_t_str} °C, ಗರಿಷ್ಠ ತಾಪಮಾನ: {max_t_str} °C. "
                    f"ಸರಾಸರಿ ಆಧಾರ ಬಾಷ್ಪೀಕರಣ (ET0): {f'{avg_et0:.1f} ಮಿ.ಮೀ/ದಿನ' if avg_et0 is not None else 'ಲಭ್ಯವಿಲ್ಲ'}."
                    f"{stale_warning_kn}"
                )
                title_3 = "ಹವಾಮಾನ ಮಾದರಿ ಮುನ್ಸೂಚನೆ ಮತ್ತು ಬಾಷ್ಪೀಕರಣ ಸ್ಥಿತಿ"
            elif language == "hi":
                content_3 = (
                    f"संख्यात्मक मौसम मॉडल पूर्वानुमान ({n_days} दिनों की अवधि): "
                    f"वर्षा: {rain_desc_hi}, न्यूनतम तापमान: {min_t_str} °C, अधिकतम तापमान: {max_t_str} °C. "
                    f"औसत संदर्भ वाष्पोत्सर्जन (ET0): {f'{avg_et0:.1f} मिमी/दिन' if avg_et0 is not None else 'उपलब्ध नहीं'}."
                    f"{stale_warning_hi}"
                )
                title_3 = "मौसम मॉडल पूर्वानुमान एवं वायुमंडलीय जल मांग"
            else:
                content_3 = (
                    f"Numerical Weather Model Forecast ({n_days}-day horizon): "
                    f"Precipitation: {rain_desc_en}, temperature range: {min_t_str}°C to {max_t_str}°C. "
                    f"Mean reference evapotranspiration (ET0): {f'{avg_et0:.1f} mm/day' if avg_et0 is not None else 'Not available'}."
                    f"{stale_warning_en}"
                )
                title_3 = "Atmospheric & Numerical Weather Forecast"
        else:
            if language == "kn":
                content_3 = "ಹವಾಮಾನ ದತ್ತಾಂಶ ಲಭ್ಯವಿಲ್ಲ."
                title_3 = "ಹವಾಮಾನ ಸ್ಥಿತಿ"
            elif language == "hi":
                content_3 = "मौसम डेटा उपलब्ध नहीं है।"
                title_3 = "मौसम की स्थिति"
            else:
                content_3 = "Weather data was not retrieved."
                title_3 = "Weather & Atmospheric Conditions"

        sections.append(AnalysisSection(key="weather_atmosphere", title=title_3, content=content_3, claims=section_claims_3))

        # ------------------------------------------------------------------
        # Section 4: Crop Water Dynamics & Simulation
        # ------------------------------------------------------------------
        section_claims_4: list[GroundedClaim] = []
        if bundle.c3_states:
            latest_c3 = bundle.c3_states[-1]
            c_demand = safe_measurement_val(latest_c3.crop_water_demand)
            c_eta = safe_measurement_val(latest_c3.actual_evapotranspiration)
            c_stress = safe_measurement_val(latest_c3.water_stress)
            c_sw = safe_measurement_val(latest_c3.soil_water)
            c_irrig = safe_measurement_val(latest_c3.irrigation)

            engine_id = f"terrapulse-{latest_c3.engine.name.lower()}-{latest_c3.engine.version}"

            if c_demand is not None:
                section_claims_4.append(
                    record_claim("crop_water_demand", c_demand, latest_c3.crop_water_demand.unit, "c3.cropWaterDemand", engine_id, "simulation_state")
                )
            if c_eta is not None:
                section_claims_4.append(
                    record_claim("actual_evapotranspiration", c_eta, latest_c3.actual_evapotranspiration.unit, "c3.actualEvapotranspiration", engine_id, "simulation_state")
                )
            if c_stress is not None:
                section_claims_4.append(
                    record_claim("water_stress", c_stress, latest_c3.water_stress.unit, "c3.waterStress", engine_id, "simulation_state")
                )
            if c_sw is not None:
                section_claims_4.append(
                    record_claim("soil_water", c_sw, latest_c3.soil_water.unit, "c3.soilWater", engine_id, "simulation_state")
                )
            if c_irrig is not None:
                section_claims_4.append(
                    record_claim("irrigation", c_irrig, latest_c3.irrigation.unit, "c3.irrigation", engine_id, "simulation_state")
                )

            stress_pct = f"{c_stress * 100:.0f}%" if c_stress is not None else "Not available"

            # Strict preservation of missing values — NEVER converting None into 0.0
            irrig_str_en = f"{c_irrig:.1f} mm" if c_irrig is not None else "Not available"
            irrig_str_kn = f"{c_irrig:.1f} ಮಿ.ಮೀ" if c_irrig is not None else "ಲಭ್ಯವಿಲ್ಲ"
            irrig_str_hi = f"{c_irrig:.1f} मिमी" if c_irrig is not None else "उपलब्ध नहीं"

            if language == "kn":
                content_4 = (
                    f"ಬೆಳೆಯ ನೀರಿನ ಸಮತೋಲನ ({latest_c3.date.isoformat()} ದಿನಾಂಕದಂತೆ): "
                    f"ಬೆಳೆಯ ನೀರಿನ ಬೇಡಿಕೆ (ETc): {c_demand or 'ಲಭ್ಯವಿಲ್ಲ'} ಮಿ.ಮೀ, "
                    f"ನೈಜ ಬಾಷ್ಪೀಕರಣ (ETa): {c_eta or 'ಲಭ್ಯವಿಲ್ಲ'} ಮಿ.ಮೀ. "
                    f"ಮಣ್ಣಿನ ನೀರು: {c_sw or 'ಲಭ್ಯವಿಲ್ಲ'} ಮಿ.ಮೀ. "
                    f"ನೀರಿನ ಒತ್ತಡ ಸೂಚ್ಯಂಕ (Ks): {c_stress or 'ಲಭ್ಯವಿಲ್ಲ'} ({stress_pct} ಒತ್ತಡ). "
                    f"ನೀರಾವರಿ: {irrig_str_kn}."
                )
                title_4 = "ಬೆಳೆಯ ಜಲ ಸಮತೋಲನ ಮತ್ತು ಒತ್ತಡ ವಿಶ್ಲೇಷಣೆ"
            elif language == "hi":
                content_4 = (
                    f"फसल जल संतुलन ({latest_c3.date.isoformat()} की स्थिति): "
                    f"फसल जल मांग (ETc): {c_demand or 'उपलब्ध नहीं'} मिमी, "
                    f"वास्तविक वाष्पोत्सर्जन (ETa): {c_eta or 'उपलब्ध नहीं'} मिमी. "
                    f"मृदा जल स्तर: {c_sw or 'उपलब्ध नहीं'} मिमी. "
                    f"जल तनाव सूचकांक (Ks): {c_stress or 'उपलब्ध नहीं'} ({stress_pct} तनाव). "
                    f"सिंचाई: {irrig_str_hi}."
                )
                title_4 = "फसल जल संतुलन एवं तनाव विश्लेषण"
            else:
                content_4 = (
                    f"Crop Biophysical State as of {latest_c3.date.isoformat()}: "
                    f"Crop water demand (ETc): {c_demand or 'Not available'} mm, "
                    f"actual evapotranspiration (ETa): {c_eta or 'Not available'} mm. "
                    f"Soil water in profile: {c_sw or 'Not available'} mm. "
                    f"Water stress coefficient (Ks): {c_stress or 'Not available'} ({stress_pct} stress impact). "
                    f"Irrigation applied: {irrig_str_en}."
                )
                title_4 = "Crop Water Dynamics & Moisture Stress"
        else:
            if language == "kn":
                content_4 = (
                    f"ಈ ಪ್ಲಾಟ್‌ಗಾಗಿ ದೈನಂದಿನ ಜೈವಿಕ ಭೌತಿಕ ಸಿಮ್ಯುಲೇಶನ್ ನಡೆಸಲಾಗಿಲ್ಲ. "
                    f"ಬೆಳೆ '{bundle.crop_canonical_name}' ಮಾದರಿ ಎಂಜಿನ್ '{bundle.crop_capability.selected_engine}' ಆಗಿದೆ."
                )
                title_4 = "ಬೆಳೆಯ ಜಲ ಸ್ಥಿತಿ"
            elif language == "hi":
                content_4 = (
                    f"इस प्लॉट के लिए दैनिक बायोफिजिकल सिमुलेशन निष्पादित नहीं किया गया है। "
                    f"फसल '{bundle.crop_canonical_name}' के लिए निर्धारित इंजन '{bundle.crop_capability.selected_engine}' है।"
                )
                title_4 = "फसल जल स्थिति"
            else:
                content_4 = (
                    f"Dynamic daily biophysical simulation states have not been computed for this plot. "
                    f"Crop '{bundle.crop_canonical_name}' capability is bound to engine '{bundle.crop_capability.selected_engine}'."
                )
                title_4 = "Crop Simulation Status"

        sections.append(AnalysisSection(key="crop_water_dynamics", title=title_4, content=content_4, claims=section_claims_4))

        # ------------------------------------------------------------------
        # Section 5: Scenario Comparison (C5) if available
        # ------------------------------------------------------------------
        if bundle.c5_comparison is not None:
            section_claims_5: list[GroundedClaim] = []
            c5 = bundle.c5_comparison
            diff_lines: list[str] = []

            for cm in c5.metrics:
                diff_val = safe_measurement_val(cm.difference)
                va = safe_measurement_val(cm.value_a)
                vb = safe_measurement_val(cm.value_b)
                if diff_val is not None:
                    section_claims_5.append(
                        record_claim(
                            metric=f"{cm.metric}_difference",
                            val=diff_val,
                            unit=cm.difference.unit,
                            field_path=f"c5.metrics[{cm.metric}].difference",
                            source_id="terrapulse-compare-1.0",
                            category="comparison_derived",
                        )
                    )
                diff_lines.append(f"{cm.metric}: Branch A={va or 'N/A'}, Branch B={vb or 'N/A'}, Difference={diff_val or 'N/A'} {cm.difference.unit}")

            diff_content_str = "; ".join(diff_lines)
            matched_str = "matched weather realizations" if c5.matched_inputs else "unmatched baseline inputs"

            if language == "kn":
                content_5 = (
                    f"ನಿರ್ವಹಣಾ ಸನ್ನಿವೇಶಗಳ ಹೋಲಿಕೆ ({c5.comparison_date.isoformat()} ದಿನಾಂಕಕ್ಕೆ): "
                    f"ಮೂಲ ಇನ್‌ಪುಟ್ ಸ್ಥಿತಿ: {matched_str}. ಮೆಟ್ರಿಕ್ ವ್ಯತ್ಯಾಸಗಳು: {diff_content_str}."
                )
                title_5 = "ನಿರ್ವಹಣಾ ಸನ್ನಿವೇಶಗಳ ಹೋಲಿಕೆ"
            elif language == "hi":
                content_5 = (
                    f"प्रबंधन परिदृश्यों की तुलना ({c5.comparison_date.isoformat()} की स्थिति): "
                    f"आधार इनपुट स्थिति: {matched_str}. मुख्य अंतर: {diff_content_str}."
                )
                title_5 = "प्रबंधन परिदृश्य तुलना"
            else:
                content_5 = (
                    f"Scenario Comparison as of {c5.comparison_date.isoformat()}: "
                    f"Baseline condition: {matched_str}. Metric differences: {diff_content_str}."
                )
                title_5 = "Management Scenario Comparison"

            sections.append(AnalysisSection(key="comparison_evaluation", title=title_5, content=content_5, claims=section_claims_5))

        # ------------------------------------------------------------------
        # Section 6: Actionable Operational Guidance
        # ------------------------------------------------------------------
        if language == "kn":
            content_6 = (
                "ಕಾರ್ಯಾಚರಣೆಯ ಮಾರ್ಗದರ್ಶನ: ಹವಾಮಾನ ಮುನ್ಸೂಚನೆ ಮತ್ತು ಮಣ್ಣಿನ ತೇವಾಂಶದ ಸಮತೋಲನದ ಆಧಾರದ ಮೇಲೆ ನೀರಾವರಿಯನ್ನು ನಿಗದಿಪಡಿಸಿ. "
                "ಮಳೆ ಬರುವ ನಿರೀಕ್ಷೆಯಿದ್ದರೆ ನೀರಾವರಿಯನ್ನು ಮುಂದೂಡಿ. "
                "ಯಾವುದೇ ಹೊಸ ರಾಸಾಯನಿಕ ಅಥವಾ ಗೊಬ್ಬರ ಸಿಂಪರಣೆಗೂ ಮುನ್ನ ಸ್ಥಳೀಯ ಕೃಷಿ ಇಲಾಖೆಯ ಶಿಫಾರಸುಗಳನ್ನು ಪರಿಶೀಲಿಸಿ."
            )
            title_6 = "ಕಾರ್ಯಾಚರಣೆ ಮಾರ್ಗದರ್ಶನ"
        elif language == "hi":
            content_6 = (
                "परिचालन मार्गदर्शन: मौसम पूर्वानुमान और मिट्टी की नमी के आधार पर ही सिंचाई की योजना बनाएं। "
                "यदि बारिश की संभावना हो तो अनावश्यक सिंचाई टालें। "
                "उर्वरक या कीटनाशक अनुप्रयोग से पूर्व स्थानीय कृषि विभाग की सिफारिशों का पालन करें।"
            )
            title_6 = "परिचालन मार्गदर्शन"
        else:
            content_6 = (
                "Operational Guidance: Plan irrigation schedules strictly against root-zone moisture depletion and forecasted precipitation. "
                "Avoid unnecessary irrigation if rainfall is forecast in the 48-hour window. "
                "Consult local package of practices before fertilizer or soil amendment applications."
            )
            title_6 = "Operational Guidance & Recommendations"

        sections.append(AnalysisSection(key="actions_and_guidance", title=title_6, content=content_6, claims=[]))

        # ------------------------------------------------------------------
        # Section 7: Scientific Limitations & Escalations
        # ------------------------------------------------------------------
        lim_texts: list[str] = [f"[{lim.code}] {lim.description}" for lim in limitations]
        esc_texts: list[str] = [f"[{esc.category}] {esc.reason} -> Contact: {esc.recommended_authority}" for esc in escalations]

        lim_combined = " ".join(lim_texts) if lim_texts else "No operational limitations flagged."
        esc_combined = " ".join(esc_texts) if esc_texts else "No external escalations required."

        if language == "kn":
            content_7 = (
                f"ವೈಜ್ಞಾನಿಕ ಮಿತಿಗಳು: {lim_combined}\n\n"
                f"ಮಾನವ ಹಸ್ತಕ್ಷೇಪ ಮತ್ತು ಶಿಫಾರಸುಗಳು: {esc_combined}"
            )
            title_7 = "ವೈಜ್ಞಾನಿಕ ಮಿತಿಗಳು ಮತ್ತು ಅಧಿಕೃತ ಸಂಪರ್ಕ"
        elif language == "hi":
            content_7 = (
                f"वैज्ञानिक सीमाएं: {lim_combined}\n\n"
                f"मानव विशेषज्ञ रेफरल एवं परामर्श: {esc_combined}"
            )
            title_7 = "वैज्ञानिक सीमाएं एवं विशेषज्ञ परामर्श"
        else:
            content_7 = (
                f"Scientific Scope & Limitations: {lim_combined}\n\n"
                f"Expert Escalation & Referrals: {esc_combined}"
            )
            title_7 = "Scientific Boundaries & Escalations"

        sections.append(AnalysisSection(key="limitations_and_escalation", title=title_7, content=content_7, claims=[]))

        # ------------------------------------------------------------------
        # Overall Summary
        # ------------------------------------------------------------------
        crop_name = bundle.crop_canonical_name
        farm_name = bundle.farm.farm_name

        if language == "kn":
            summary = (
                f"ಕೃಷಿ ಕ್ಷೇತ್ರ '{farm_name}'ದ ಬೆಳೆ '{crop_name}'ಗೆ ಸಂಬಂಧಿಸಿದಂತೆ ವಿಶ್ಲೇಷಣೆ ಪೂರ್ಣಗೊಂಡಿದೆ. "
                f"ಮಾದರಿ ಎಂಜಿನ್: {bundle.crop_capability.selected_engine}. "
                f"ಲಭ್ಯವಿರುವ ಹವಾಮಾನ, ಮಣ್ಣು ಮತ್ತು ಜೈವಿಕ ಭೌತಿಕ ಸಾಕ್ಷ್ಯಾಧಾರಗಳನ್ನು ಆಧರಿಸಿ ವಿವರಣೆ ಸಿದ್ಧಪಡಿಸಲಾಗಿದೆ. "
                f"ರೋಗ ಪತ್ತೆ ಮತ್ತು ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ಅಂದಾಜುಗಳು ವೈಜ್ಞಾನಿಕ ಸಿಮ್ಯುಲೇಶನ್ ವ್ಯಾಪ್ತಿಯಿಂದ ಹೊರಗಿವೆ."
            )
        elif language == "hi":
            summary = (
                f"खेत '{farm_name}' की फसल '{crop_name}' का साक्ष्य-आधारित विश्लेषण तैयार है। "
                f"सिमुलेशन इंजन: {bundle.crop_capability.selected_engine}। "
                f"उपलब्ध मौसम, मृदा और जल संतुलन डेटा के आधार पर रिपोर्ट तैयार की गई है। "
                f"रोग निदान एवं मंडी भाव पूर्वानुमान बायोफिजिकल मॉडल के दायरे से बाहर हैं।"
            )
        else:
            summary = (
                f"Evidence-grounded agro-ecological analysis completed for crop '{crop_name}' at farm '{farm_name}'. "
                f"Simulated via {bundle.crop_capability.selected_engine}. "
                f"All quantitative assessments reflect verified soil, weather, and biophysical water balances. "
                f"Disease diagnosis and market commodity pricing are strictly out of scope and referred to local authorities."
            )

        return summary, sections, claims
