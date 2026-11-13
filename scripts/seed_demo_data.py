"""Seed official TerraPulse Demo Farm into PostgreSQL database with complete end-to-end data."""
import asyncio
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.db import SessionFactory, engine
from app.models import (
    Base,
    BranchDecision,
    CropIdentity,
    DecisionBranch,
    EnvironmentalSnapshot,
    Farm,
    FarmResource,
    Plot,
    ResourceAllocation,
    ResourceLedger,
    ResourcePlotAuthorization,
    ScientificState,
    SimulationComparison,
    SimulationRun,
    TimelineEvent,
)
from app.services.crop_lens.registry import CROP_REGISTRY
from app.services.farmer_alerts.models import (
    FarmerAlert,
    TelegramDelivery,
    TelegramLink,
    TelegramSubscription,
)

DEMO_FARM_ID = UUID("00000000-0000-0000-0000-000000000001")
PLOT_MAIZE_ID = UUID("00000000-0000-0000-0000-000000000101")
PLOT_TURMERIC_ID = UUID("00000000-0000-0000-0000-000000000102")
PLOT_WHEAT_ID = UUID("00000000-0000-0000-0000-000000000103")

CROP_MAIZE_ID = UUID("00000000-0000-0000-0000-000000000010")
CROP_TURMERIC_ID = UUID("00000000-0000-0000-0000-000000000003")
CROP_WHEAT_ID = UUID("00000000-0000-0000-0000-000000000020")

RESERVOIR_ID = UUID("00000000-0000-0000-0000-000000000201")
BRANCH_BASELINE_ID = UUID("00000000-0000-0000-0000-000000000301")
BRANCH_OPTIMIZED_ID = UUID("00000000-0000-0000-0000-000000000302")
SIM_BASELINE_RUN_ID = UUID("00000000-0000-0000-0000-000000000311")
SIM_OPTIMIZED_RUN_ID = UUID("00000000-0000-0000-0000-000000000312")
COMPARISON_ID = UUID("00000000-0000-0000-0000-000000000401")
ALERT_1_ID = UUID("00000000-0000-0000-0000-000000000501")
ALERT_2_ID = UUID("00000000-0000-0000-0000-000000000502")


async def seed():
    print("Starting database seeding...")
    async with SessionFactory() as session:
        # 1. Seed all crops from CROP_REGISTRY
        print("Seeding crops...")
        for crop in CROP_REGISTRY:
            stmt = pg_insert(CropIdentity).values(
                id=crop.crop_id,
                canonical_name=crop.canonical_name,
                scientific_name=crop.scientific_name,
                aliases=crop.aliases,
                provenance=[{"source": ref.source_name, "id": ref.identifier} for ref in crop.external_references],
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[CropIdentity.id],
                set_={
                    "canonical_name": crop.canonical_name,
                    "scientific_name": crop.scientific_name,
                    "aliases": crop.aliases,
                },
            )
            await session.execute(stmt)
        await session.commit()

        # 2. Seed Demo Farm
        print("Seeding Demo Farm...")
        farm_stmt = pg_insert(Farm).values(
            id=DEMO_FARM_ID,
            name="TerraPulse Demo Farm (Agricultural Decision Lab)",
            timezone="Asia/Kolkata",
            location=WKTElement("POINT(75.8573 30.9010)", srid=4326),
        ).on_conflict_do_update(
            index_elements=[Farm.id],
            set_={"name": "TerraPulse Demo Farm (Agricultural Decision Lab)", "timezone": "Asia/Kolkata"},
        )
        await session.execute(farm_stmt)
        await session.commit()

        # 3. Seed Plots
        print("Seeding Plots...")
        plots_data = [
            (PLOT_MAIZE_ID, 12000.0, CROP_MAIZE_ID, date(2026, 6, 15), {"season": "kharif", "irrigationMethod": "furrow", "regionId": "IN-PB", "plantingDateCertainty": "confirmed", "title": "North Plot - Maize"}),
            (PLOT_TURMERIC_ID, 8000.0, CROP_TURMERIC_ID, date(2026, 5, 20), {"season": "kharif", "stageMapping": "B", "irrigationMethod": "drip", "regionId": "IN-PB", "plantingDateCertainty": "confirmed", "title": "East Plot - Turmeric"}),
            (PLOT_WHEAT_ID, 15000.0, CROP_WHEAT_ID, date(2026, 11, 5), {"season": "rabi", "irrigationMethod": "flood", "regionId": "IN-PB", "plantingDateCertainty": "confirmed", "title": "South Plot - Wheat"}),
        ]
        for pid, area, cid, pdate, mgmt in plots_data:
            p_stmt = pg_insert(Plot).values(
                id=pid,
                farm_id=DEMO_FARM_ID,
                area_m2=area,
                crop_id=cid,
                planting_date=pdate,
                management=mgmt,
            ).on_conflict_do_update(
                index_elements=[Plot.id],
                set_={"area_m2": area, "crop_id": cid, "planting_date": pdate, "management": mgmt},
            )
            await session.execute(p_stmt)
        await session.commit()

        # 4. Seed Farm Resource (Reservoir)
        print("Seeding Farm Resource (Reservoir)...")
        r_stmt = pg_insert(FarmResource).values(
            id=RESERVOIR_ID,
            farm_id=DEMO_FARM_ID,
            name="Central Farm Irrigation Reservoir",
            resource_type="water_reservoir",
            unit="litres",
            opening_volume=750000.0,
            metadata_json={"capacityLitres": 750000.0, "source": "Rainwater harvesting pond + Borewell"},
        ).on_conflict_do_update(
            index_elements=[FarmResource.id],
            set_={"name": "Central Farm Irrigation Reservoir", "opening_volume": 750000.0},
        )
        await session.execute(r_stmt)
        await session.commit()

        for pid in [PLOT_MAIZE_ID, PLOT_TURMERIC_ID, PLOT_WHEAT_ID]:
            auth_stmt = pg_insert(ResourcePlotAuthorization).values(
                id=uuid4(),
                plot_id=pid,
                resource_id=RESERVOIR_ID,
            ).on_conflict_do_nothing()
            await session.execute(auth_stmt)
        await session.commit()

        # 5. Seed Environmental Snapshots
        print("Seeding Environmental Snapshots...")
        snap_id = uuid4()
        now_utc = datetime.now(timezone.utc)
        env_stmt = pg_insert(EnvironmentalSnapshot).values(
            id=snap_id,
            farm_id=DEMO_FARM_ID,
            plot_id=PLOT_MAIZE_ID,
            availability="available",
            input_hash="hash_demo_snap_maize_01",
            payload={
                "environmentalSnapshotId": str(snap_id),
                "farmId": str(DEMO_FARM_ID),
                "plotId": str(PLOT_MAIZE_ID),
                "retrievedAt": now_utc.isoformat(),
                "dataSourceIds": ["open-meteo-ensemble", "soilgrids-wcs"],
                "isValid": True,
                "c1Input": {
                    "soil": {
                        "depthCm": {"value": 120.0, "unit": "cm", "availability": {"status": "available"}},
                        "texture": "Sandy Loam",
                        "fieldCapacity": {"value": 0.28, "unit": "m3/m3", "availability": {"status": "available"}},
                        "wiltingPoint": {"value": 0.12, "unit": "m3/m3", "availability": {"status": "available"}},
                        "bulkDensity": {"value": 1.42, "unit": "g/cm3", "availability": {"status": "available"}},
                    },
                    "dailyWeather": [
                        {"date": (date.today() - timedelta(days=2)).isoformat(), "temperatureMinC": {"value": 22.5, "unit": "C", "availability": {"status": "available"}}, "temperatureMaxC": {"value": 34.2, "unit": "C", "availability": {"status": "available"}}, "rainfallMm": {"value": 0.0, "unit": "mm", "availability": {"status": "available"}}, "ensembleMemberId": "deterministic"},
                        {"date": (date.today() - timedelta(days=1)).isoformat(), "temperatureMinC": {"value": 23.0, "unit": "C", "availability": {"status": "available"}}, "temperatureMaxC": {"value": 33.8, "unit": "C", "availability": {"status": "available"}}, "rainfallMm": {"value": 4.2, "unit": "mm", "availability": {"status": "available"}}, "ensembleMemberId": "deterministic"},
                        {"date": date.today().isoformat(), "temperatureMinC": {"value": 21.8, "unit": "C", "availability": {"status": "available"}}, "temperatureMaxC": {"value": 32.5, "unit": "C", "availability": {"status": "available"}}, "rainfallMm": {"value": 0.0, "unit": "mm", "availability": {"status": "available"}}, "ensembleMemberId": "deterministic"},
                        {"date": (date.today() + timedelta(days=1)).isoformat(), "temperatureMinC": {"value": 20.5, "unit": "C", "availability": {"status": "available"}}, "temperatureMaxC": {"value": 30.1, "unit": "C", "availability": {"status": "available"}}, "rainfallMm": {"value": 28.4, "unit": "mm", "availability": {"status": "available"}}, "ensembleMemberId": "deterministic"},
                        {"date": (date.today() + timedelta(days=2)).isoformat(), "temperatureMinC": {"value": 19.8, "unit": "C", "availability": {"status": "available"}}, "temperatureMaxC": {"value": 29.0, "unit": "C", "availability": {"status": "available"}}, "rainfallMm": {"value": 12.0, "unit": "mm", "availability": {"status": "available"}}, "ensembleMemberId": "deterministic"},
                    ],
                },
                "capability": {
                    "selectedEngine": "AquaCrop",
                    "engineVersion": "3.1.0",
                    "supportedOutputs": ["waterStress", "cropTranspiration", "soilWaterContent", "canopyCover", "biomass"],
                    "knownLimitations": ["AquaCrop zero-slot daily outputs filtered", "Soil volumetric content derived from ISRIC SoilGrids"],
                },
            },
        ).on_conflict_do_nothing()
        await session.execute(env_stmt)
        await session.commit()

        # 6. Seed Decision Branches and Simulations
        print("Seeding Decision Branches...")
        b1_stmt = pg_insert(DecisionBranch).values(
            id=BRANCH_BASELINE_ID,
            farm_id=DEMO_FARM_ID,
            plot_id=PLOT_MAIZE_ID,
            effective_date=date(2026, 6, 15),
            decision_type="baseline",
            decision_diff={"mode": "rainfed", "irrigationScheduled": False},
            model_version="AquaCrop-3.1.0",
            base_snapshot_hash="hash_baseline_v1",
            input_hashes=["hash_baseline_v1"],
        ).on_conflict_do_nothing()
        await session.execute(b1_stmt)

        b2_stmt = pg_insert(DecisionBranch).values(
            id=BRANCH_OPTIMIZED_ID,
            farm_id=DEMO_FARM_ID,
            plot_id=PLOT_MAIZE_ID,
            parent_branch_id=BRANCH_BASELINE_ID,
            effective_date=date(2026, 7, 20),
            decision_type="supplemental_irrigation",
            decision_diff={"mode": "supplemental_drip", "irrigationMm": 25.0, "targetWaterStress": 0.15},
            model_version="AquaCrop-3.1.0",
            base_snapshot_hash="hash_optimized_v1",
            input_hashes=["hash_optimized_v1"],
        ).on_conflict_do_nothing()
        await session.execute(b2_stmt)
        await session.commit()

        # 7. Seed Simulations and Scientific States
        print("Seeding Simulations & Scientific States...")
        sim1 = pg_insert(SimulationRun).values(
            id=SIM_BASELINE_RUN_ID,
            farm_id=DEMO_FARM_ID,
            plot_id=PLOT_MAIZE_ID,
            branch_id=BRANCH_BASELINE_ID,
            environmental_snapshot_id=snap_id,
            engine_name="AquaCrop",
            engine_version="3.1.0",
            status="completed",
            input_hash="hash_baseline_run",
            requested_at=now_utc - timedelta(hours=2),
            completed_at=now_utc - timedelta(hours=2),
        ).on_conflict_do_nothing()
        await session.execute(sim1)

        sim2 = pg_insert(SimulationRun).values(
            id=SIM_OPTIMIZED_RUN_ID,
            farm_id=DEMO_FARM_ID,
            plot_id=PLOT_MAIZE_ID,
            branch_id=BRANCH_OPTIMIZED_ID,
            environmental_snapshot_id=snap_id,
            engine_name="AquaCrop",
            engine_version="3.1.0",
            status="completed",
            input_hash="hash_optimized_run",
            requested_at=now_utc - timedelta(hours=1),
            completed_at=now_utc - timedelta(hours=1),
        ).on_conflict_do_nothing()
        await session.execute(sim2)
        await session.commit()

        # Seed Daily Scientific States
        today = date.today()
        for i in range(-5, 6):
            curr_date = today + timedelta(days=i)
            # Baseline state (higher water stress)
            st1 = pg_insert(ScientificState).values(
                id=uuid4(),
                plot_id=PLOT_MAIZE_ID,
                branch_id=BRANCH_BASELINE_ID,
                simulation_run_id=SIM_BASELINE_RUN_ID,
                state_date=curr_date,
                availability="available",
                payload={
                    "date": curr_date.isoformat(),
                    "farmId": str(DEMO_FARM_ID),
                    "plotId": str(PLOT_MAIZE_ID),
                    "simulationRunId": str(SIM_BASELINE_RUN_ID),
                    "waterStress": {"value": 0.42 + (0.02 * i), "unit": "fraction", "availability": {"status": "available"}},
                    "soilWaterContent": {"value": 0.18, "unit": "m3/m3", "availability": {"status": "available"}},
                    "rootZoneDepth": {"value": 0.85, "unit": "m", "availability": {"status": "available"}},
                    "canopyCover": {"value": 68.5, "unit": "%", "availability": {"status": "available"}},
                    "engine": {"name": "AquaCrop", "version": "3.1.0"},
                    "provenance": ["PAU-Ludhiana-Weather-Run", "AquaCrop-OSPy-3.1.0"],
                },
            ).on_conflict_do_nothing()
            await session.execute(st1)

            # Optimized state (lower stress, preserved canopy)
            st2 = pg_insert(ScientificState).values(
                id=uuid4(),
                plot_id=PLOT_MAIZE_ID,
                branch_id=BRANCH_OPTIMIZED_ID,
                simulation_run_id=SIM_OPTIMIZED_RUN_ID,
                state_date=curr_date,
                availability="available",
                payload={
                    "date": curr_date.isoformat(),
                    "farmId": str(DEMO_FARM_ID),
                    "plotId": str(PLOT_MAIZE_ID),
                    "simulationRunId": str(SIM_OPTIMIZED_RUN_ID),
                    "waterStress": {"value": 0.12 + (0.01 * (i % 2)), "unit": "fraction", "availability": {"status": "available"}},
                    "soilWaterContent": {"value": 0.25, "unit": "m3/m3", "availability": {"status": "available"}},
                    "rootZoneDepth": {"value": 0.95, "unit": "m", "availability": {"status": "available"}},
                    "canopyCover": {"value": 84.0, "unit": "%", "availability": {"status": "available"}},
                    "engine": {"name": "AquaCrop", "version": "3.1.0"},
                    "provenance": ["PAU-Ludhiana-Weather-Run", "AquaCrop-OSPy-3.1.0"],
                },
            ).on_conflict_do_nothing()
            await session.execute(st2)
        await session.commit()

        # 8. Seed Comparison
        print("Seeding Comparison...")
        cmp_stmt = pg_insert(SimulationComparison).values(
            id=COMPARISON_ID,
            farm_id=DEMO_FARM_ID,
            plot_id=PLOT_MAIZE_ID,
            branch_a_id=BRANCH_BASELINE_ID,
            branch_b_id=BRANCH_OPTIMIZED_ID,
            run_a_id=SIM_BASELINE_RUN_ID,
            run_b_id=SIM_OPTIMIZED_RUN_ID,
            comparison_date=today,
            status="completed",
            matched_inputs=True,
            non_comparable_reasons=["Identical weather trajectory and soil profile maintained."],
            payload={
                "result": {
                    "summary": {
                        "cropProtectionScore": 88.5,
                        "waterEfficiencyScore": 84.0,
                        "reserveSafetyScore": 86.0,
                        "overallWaterDecisionScore": 86.7,
                        "waterStressReductionPercent": 42.5,
                        "totalIrrigationWithdrawnL": 180000.0,
                        "remainingReserveL": 410000.0,
                    },
                    "daily": [
                        {"date": (today + timedelta(days=d)).isoformat(), "metrics": [
                            {"name": "waterStress", "unit": "fraction", "branchA": 0.45, "branchB": 0.14, "differenceBMinusA": -0.31},
                            {"name": "canopyCover", "unit": "%", "branchA": 65.0, "branchB": 82.0, "differenceBMinusA": 17.0},
                        ]}
                        for d in range(-3, 4)
                    ],
                },
                "provenance": {"engine": "AquaCrop-3.1.0", "evaluatedBy": "TerraPulse C5 Comparison Engine"},
            },
        ).on_conflict_do_nothing()
        await session.execute(cmp_stmt)
        await session.commit()

        # 9. Seed Telegram Subscription & Live/Delivered Alerts
        print("Seeding Telegram subscription and alerts...")
        sub_stmt = pg_insert(TelegramSubscription).values(
            id=uuid4(),
            farm_id=DEMO_FARM_ID,
            chat_id=987654321,
            user_id=12345678,
            active=True,
            locale="en",
            categories={"calendar": True, "weather": True, "science": True},
            timezone="Asia/Kolkata",
            quiet_start_hour=22,
            quiet_end_hour=7,
        ).on_conflict_do_nothing()
        await session.execute(sub_stmt)

        # Demo link token
        link_stmt = pg_insert(TelegramLink).values(
            id=uuid4(),
            farm_id=DEMO_FARM_ID,
            token_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            expires_at=now_utc + timedelta(days=30),
        ).on_conflict_do_nothing()
        await session.execute(link_stmt)

        # Seed realistic alerts
        alert1 = pg_insert(FarmerAlert).values(
            id=ALERT_1_ID,
            dedupe_key="demo_alert_rain_01",
            farm_id=DEMO_FARM_ID,
            plot_id=PLOT_MAIZE_ID,
            category="weather",
            kind="forecast-rain-review",
            event_date=today + timedelta(days=1),
            evidence_hash="sha_demo_rain_01",
            payload={
                "farmId": str(DEMO_FARM_ID),
                "plotId": str(PLOT_MAIZE_ID),
                "cropName": "Maize",
                "category": "weather",
                "kind": "forecast-rain-review",
                "eventDate": (today + timedelta(days=1)).isoformat(),
                "title": "Review forecast rain for Maize tomorrow (28.4 mm)",
                "evidence": "Open-Meteo ensemble projects 28.4 mm of precipitation (deterministic run; retrieved today).",
                "suggestedAction": "Recheck field drainage and postpone scheduled furrow irrigation by 48 hours to conserve reservoir water.",
                "sourceId": "open-meteo-ensemble",
                "sourceVersion": "weather-c1-v1",
                "uncertainty": "Forecast, not an observation or guaranteed rainfall.",
            },
        ).on_conflict_do_nothing()
        await session.execute(alert1)

        alert2 = pg_insert(FarmerAlert).values(
            id=ALERT_2_ID,
            dedupe_key="demo_alert_science_02",
            farm_id=DEMO_FARM_ID,
            plot_id=PLOT_MAIZE_ID,
            category="science",
            kind="modelled-water-stress",
            event_date=today,
            evidence_hash="sha_demo_science_02",
            payload={
                "farmId": str(DEMO_FARM_ID),
                "plotId": str(PLOT_MAIZE_ID),
                "cropName": "Maize",
                "category": "science",
                "kind": "modelled-water-stress",
                "eventDate": today.isoformat(),
                "title": "AquaCrop modeled water stress alert for Maize (1-Ks = 0.42)",
                "evidence": "AquaCrop 3.1.0 estimates water-stress severity at 0.42 in baseline rainfed branch (run 00000000-0000-0000-0000-000000000311).",
                "suggestedAction": "Verify root-zone moisture in field. Applying 25 mm supplemental irrigation reduces stress by 42.5%.",
                "sourceId": "AquaCrop-3.1.0",
                "sourceVersion": "3.1.0",
                "uncertainty": "Simulation under model inputs; check field conditions before irrigating.",
            },
        ).on_conflict_do_nothing()
        await session.execute(alert2)

        alert_1_rec = await session.scalar(select(FarmerAlert).where(FarmerAlert.dedupe_key == "demo_alert_rain_01"))
        alert_1_id = alert_1_rec.id if alert_1_rec else ALERT_1_ID
        alert_2_rec = await session.scalar(select(FarmerAlert).where(FarmerAlert.dedupe_key == "demo_alert_science_02"))
        alert_2_id = alert_2_rec.id if alert_2_rec else ALERT_2_ID

        # Record deliveries as DELIVERED
        sub_record = await session.scalar(select(TelegramSubscription).where(TelegramSubscription.farm_id == DEMO_FARM_ID))
        if sub_record:
            deliv1 = pg_insert(TelegramDelivery).values(
                id=uuid4(),
                alert_id=alert_1_id,
                subscription_id=sub_record.id,
                status="delivered",
                attempts=1,
                telegram_message_id=450123,
                updated_at=now_utc - timedelta(minutes=15),
            ).on_conflict_do_nothing()
            await session.execute(deliv1)

            deliv2 = pg_insert(TelegramDelivery).values(
                id=uuid4(),
                alert_id=alert_2_id,
                subscription_id=sub_record.id,
                status="delivered",
                attempts=1,
                telegram_message_id=450124,
                updated_at=now_utc - timedelta(minutes=5),
            ).on_conflict_do_nothing()
            await session.execute(deliv2)

        # Seed Timeline Events
        te1 = pg_insert(TimelineEvent).values(
            id=uuid4(),
            farm_id=DEMO_FARM_ID,
            plot_id=PLOT_MAIZE_ID,
            branch_id=BRANCH_BASELINE_ID,
            event_type="planting_date",
            event_date=date(2026, 6, 15),
            description="Maize (Hybrid Pioneer 3396) sown in North Plot under standard Kharif cycle.",
            payload={"sowingRateKgHa": 20.0, "spacingCm": "60x20", "depthCm": 5.0},
        ).on_conflict_do_nothing()
        await session.execute(te1)

        te2 = pg_insert(TimelineEvent).values(
            id=uuid4(),
            farm_id=DEMO_FARM_ID,
            plot_id=PLOT_MAIZE_ID,
            branch_id=BRANCH_BASELINE_ID,
            event_type="soil_inspection",
            event_date=date(2026, 7, 5),
            description="Field soil inspection: Topsoil moisture 0.28 m3/m3, root depth reaching 45 cm.",
            payload={"topsoilMoisture": 0.28, "subsoilMoisture": 0.32},
        ).on_conflict_do_nothing()
        await session.execute(te2)

        te3 = pg_insert(TimelineEvent).values(
            id=uuid4(),
            farm_id=DEMO_FARM_ID,
            plot_id=PLOT_MAIZE_ID,
            branch_id=BRANCH_OPTIMIZED_ID,
            event_type="branch_fork",
            event_date=date(2026, 7, 20),
            description="Forked optimized drip branch: scheduled 25 mm pulse upon reaching 50% RAW deficit.",
            payload={"decisionType": "supplemental_irrigation", "irrigationMm": 25.0},
        ).on_conflict_do_nothing()
        await session.execute(te3)

        te4 = pg_insert(TimelineEvent).values(
            id=uuid4(),
            farm_id=DEMO_FARM_ID,
            plot_id=PLOT_MAIZE_ID,
            branch_id=BRANCH_OPTIMIZED_ID,
            event_type="irrigation",
            event_date=date(2026, 8, 2),
            description="Precision drip application: 48,000 L delivered from central farm reservoir.",
            payload={"litres": 48000, "source": "Central Reservoir", "efficiency": 0.95},
        ).on_conflict_do_nothing()
        await session.execute(te4)

        await session.commit()
    print("Database seeding completed successfully!")


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed())
