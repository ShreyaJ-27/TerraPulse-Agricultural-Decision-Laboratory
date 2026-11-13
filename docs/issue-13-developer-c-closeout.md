# Developer C Closeout: Issue #13 — Farmer Onboarding Interface

This document records the completed backend data, validation, and contract contribution for **GitHub Issue #13 ([P0] Implement farmer farm/plot/crop onboarding interface)** by Developer C (Data and Crop Lens).

The backend implementation was delivered and merged into `main` via **[Pull Request #34](https://github.com/ShreyaJ-27/Vasundara-Agricultural-Decision-Laboratory/pull/34)** (*"Complete onboarding and environmental data services"*). This document serves as the formal architectural closeout and frontend integration specification for Issue #13.

---

## 1. Executive Summary

Developer C was responsible for the backend foundation of farmer onboarding:
- Providing persistent, validated REST APIs for farm and plot onboarding.
- Enforcing strict geographic coordinate bounding and explicit farmer confirmation.
- Integrating multi-lingual crop identity resolution and preventing silent candidate selection on ambiguous queries.
- Ensuring direct export compatibility with the authoritative `C2FarmDefinition` contract.
- Returning structured, field-level error messages suitable for direct UI consumption.

The frontend onboarding wizard UI components remain the responsibility of Developer D (Application Experience).

---

## 2. API Endpoints & Routes

All endpoints are prefixed with `/api/v1` and return standardized responses wrapped in `ApiResponse` with `correlationId`.

### Farm Endpoints (`apps/api/app/routers/farms.py`)
- `POST /api/v1/farms`: Register a new farm. Requires `name`, `timezone`, `location: { latitude, longitude, crs: "EPSG:4326" }`, and `locationConfirmed: true`.
- `GET /api/v1/farms`: List all registered farms.
- `GET /api/v1/farms/{farm_id}`: Retrieve farm details by UUID.

### Plot Endpoints (`apps/api/app/routers/farms.py`)
- `POST /api/v1/farms/{farm_id}/plots`: Register a plot under a confirmed farm. Accepts `areaM2: { value, unit: "m2" }`, and either a confirmed `cropId` or a `cropQuery`. Optional fields include `plantingDate`, `geometry`, `management`, and `sharedResourceIds`.
- `GET /api/v1/farms/{farm_id}/plots`: List all plots under a farm.
- `GET /api/v1/farms/{farm_id}/plots/{plot_id}`: Retrieve a specific plot by UUID with cross-farm access isolation.

### Crop Lens Endpoints (`apps/api/app/routers/crops.py`)
- `GET /api/v1/crops`: List the curated crop catalog with taxonomic references, vernacular aliases, selected engines, and capabilities.
- `GET /api/v1/crops/resolve?q={query}`: Resolve a crop name, alias, or scientific name against the crop lens registry.
- `GET /api/v1/crops/{crop_id}/capability`: Retrieve the authoritative C7 model capability and supported engines (AquaCrop/FAO-56).

---

## 3. Validation & Business Rules

### Geographic Coordinate Validation
- Coordinates are validated against WGS 84 spatial bounds: latitude must be in $[-90.0, 90.0]$, longitude must be in $[-180.0, 180.0]$.
- `FarmCreateRequest.locationConfirmed` must be `true`. If unconfirmed, the backend rejects creation with HTTP 422: *"Farm location coordinates must be explicitly confirmed by the user before onboarding."*
- Arbitrary GPS coordinates are never guessed or automatically confirmed by the backend.

### Plot Area Validation
- Plot area value must be strictly positive (`value > 0`).
- Plot area unit must be `"m2"`.
- Requests with non-positive area or invalid units are rejected with HTTP 422.

### Crop Ambiguity & Identification Protection
- Multi-lingual resolution supports canonical names, vernacular aliases (Hindi, Kannada, Telugu, Tamil), and scientific botanical names.
- When a query matches multiple crops (e.g. `"millet"` matches Pearl Millet, Finger Millet, and Foxtail Millet), `/api/v1/crops/resolve` returns `status: "AMBIGUOUS"` alongside an array of candidate matches (`candidates: [ { cropId, canonicalName, scientificName, matchedAlias } ]`).
- During plot creation (`POST /api/v1/farms/{farm_id}/plots`), supplying an ambiguous `cropQuery` raises `AmbiguousCropError` returning HTTP 422 with `code: "AMBIGUOUS_CROP_IDENTITY"` and candidate names.
- **The system never silently selects a candidate**. Explicit user selection of `cropId` is required.

---

## 4. Structured Error Handling

All validation and domain errors follow the unified `ApiError` schema:

```json
{
  "error": {
    "code": "AMBIGUOUS_CROP_IDENTITY",
    "message": "Crop query 'millet' is ambiguous (3 matches found). Explicit crop confirmation is required.",
    "fields": {
      "cropQuery": [
        "Pearl Millet (Pennisetum glaucum)",
        "Finger Millet (Eleusine coracana)",
        "Foxtail Millet (Setaria italica)"
      ]
    }
  },
  "correlationId": "req-123e4567-e89b-12d3-a456-426614174000"
}
```

Standardized error codes:
- `VALIDATION_ERROR`: Missing or malformed fields, coordinate out-of-bounds, non-positive area.
- `AMBIGUOUS_CROP_IDENTITY`: Query matches multiple crops; confirmation required.
- `NOT_FOUND`: Farm ID, plot ID, or unresolvable crop not found.

---

## 5. Contract Compatibility (C2 Farm Definition)

The onboarding models serialize directly into the project's authoritative `C2FarmDefinition` contract without data loss:
- `FarmResponse.to_c2_definition()` constructs `C2FarmDefinition(contractVersion="1.0", farmId, farmName, location, boundary, timezone, plots)`.
- `PlotResponse.to_contract_plot()` constructs `PlotDefinition(plotId, areaM2, geometry, cropId, plantingDate, management, sharedResourceIds)`.

This guarantees seamless downstream handoff to Issue #8 (Environmental Input Service) and Issue #11 (Scientific Simulation Orchestrator).

---

## 6. Relevant Backend File Paths

- `apps/api/app/routers/farms.py`: Farm and plot onboarding router.
- `apps/api/app/routers/crops.py`: Crop catalog and resolution router.
- `apps/api/app/services/onboarding.py`: Farm and plot persistence service.
- `apps/api/app/services/crop_lens/resolver.py`: Crop lens resolution engine.
- `apps/api/app/services/crop_lens/registry.py`: Curated crop catalog with taxonomic references.
- `apps/api/app/schemas.py`: Request, response, and error schemas.
- `apps/api/app/contracts.py`: Authoritative C2 Farm Definition and C7 Model Capability contracts.
- `tests/api/test_farms_router.py`: Dedicated onboarding API tests (16 tests).
- `tests/api/test_crops_router.py`: Dedicated crop lens API tests (7 tests).

---

## 7. Verification & Actual Test Results

All tests have been verified locally and through CI on `main`:

### Dedicated Onboarding & Crop API Suite (23 passed)
```bash
.venv/bin/pytest tests/api/test_farms_router.py tests/api/test_crops_router.py -v
======================== 23 passed, 4 warnings in 0.92s ========================
```
- `test_create_farm_success`: Farm creation and persistence.
- `test_create_farm_invalid_coordinates`: Coordinate bounds rejection.
- `test_create_farm_unconfirmed_location_rejected`: Unconfirmed location rejection.
- `test_get_farm_by_id`, `test_list_farms`: Farm retrieval.
- `test_create_plot_with_crop_alias_resolution`: Single unambiguous alias resolution during plot creation.
- `test_create_plot_with_direct_crop_id`: Plot creation with direct canonical crop ID.
- `test_create_plot_ambiguous_crop_requires_confirmation`: Rejection of ambiguous crop query with candidate list.
- `test_create_plot_unresolvable_crop_rejected`: 422 rejection on unknown crop query.
- `test_create_plot_invalid_area_value`: Rejection of non-positive area.
- `test_list_and_get_plots_under_farm`: Plot listing under farm.
- `test_farm_with_plots_validates_as_c2_contract`: Direct validation as authoritative C2 contract.
- `test_get_plot_cross_farm_isolation`: Cross-farm plot isolation.
- `test_get_crop_catalog`: Catalog retrieval.
- `test_resolve_crop_exact`, `test_resolve_crop_ambiguous`, `test_resolve_crop_not_found`: Crop resolution states.
- `test_get_crop_capability_by_id`: C7 capability retrieval.

### Full Repository Backend Suite (110 passed)
```bash
.venv/bin/pytest
======================= 110 passed, 4 warnings in 0.94s ========================
```

---

## 8. Integration Handoff for Developer D

Developer D can integrate the onboarding UI wizard with the following sequence:

1. **Check Existing Farm**: Call `GET /api/v1/farms`. If empty, launch onboarding wizard.
2. **Step 1 — Farm Location**: Obtain farmer coordinates, display them for review, and submit `POST /api/v1/farms` with `locationConfirmed: true`. Store the returned `farmId`.
3. **Step 2 — Plot Area**: Enter plot area in square meters. Submit `areaM2: { value: float, unit: "m2" }`.
4. **Step 3 — Crop Selection & Ambiguity**:
   - Query `/api/v1/crops/resolve?q={input}` as the user types or speaks.
   - If `status === "EXACT_MATCH"`, bind `cropId = response.crop.cropId`.
   - If `status === "AMBIGUOUS"`, display the `candidates` array as selection chips. When the user taps a chip, bind the selected candidate's `cropId`.
5. **Step 4 — Plot Creation**: Submit `POST /api/v1/farms/{farmId}/plots` with `cropId`.
6. **Step 5 — Complete**: Persist the resulting `farmId` and `plotId` in client state to activate the farm dashboard.
