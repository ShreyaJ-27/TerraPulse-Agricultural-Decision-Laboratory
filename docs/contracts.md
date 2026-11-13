# Shared contracts and API conventions

The authoritative JSON contracts live in [`packages/contracts/src/index.ts`](../packages/contracts/src/index.ts) and their Pydantic validation counterparts live in [`apps/api/app/contracts.py`](../apps/api/app/contracts.py). Fixtures in `packages/contracts/fixtures` are the cross-language compatibility examples for C1–C8.

All measurements carry a unit and an availability status. `available` requires a numeric value; `missing`, `invalid`, and `unsupported` must not be represented as zero. Dates use ISO `YYYY-MM-DD`; timestamps use ISO 8601 UTC strings. Coordinates are WGS 84 (`EPSG:4326`) and are range validated.

API endpoints are versioned under `/api/v1`. Successful responses use `{ "data": ..., "correlationId": "...", "contractVersion": "1.0" }`. Validation errors use `{ "error": { "code": "VALIDATION_ERROR", "message": "...", "fields": { "...": ["..."] } }, "correlationId": "...", "contractVersion": "1.0" }`. The `X-Correlation-ID` request header is echoed or generated.

Contract changes require updating both implementations and all affected fixtures before merging.
