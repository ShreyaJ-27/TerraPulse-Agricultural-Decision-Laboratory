# Evidence-grounded farm analysis

Issue #21 adds a farm-specific evidence workflow to Assisted. It keeps general crop questions in the bounded crop interaction API and sends plot-specific questions to `POST /api/v1/analysis`.

## Farmer workflow

1. Open **Assisted** (`/assisted` or `/interact`).
2. Use **Quick crop assistance** for crop identity/capability questions, supported general water guidance, ambiguity clarification, pathology escalation, and market-price refusal.
3. Use **Farm evidence analysis** for a question about a registered farm. Select a farm and plot; branch, completed run, and comparison are optional. Choices are loaded from application APIs rather than entered as UUIDs.
4. Submit a typed question or use browser speech recognition to fill the editable question field. The selected English, Kannada, or Hindi locale is sent with either request.
5. Review the localized explanation, verified claims, source fields, freshness, limitations, and escalation notices. **Supporting evidence** reveals selected snapshot/run/branch/comparison references and missing evidence.

The two workflows intentionally remain separate. Disease/pest diagnosis and chemical prescriptions are escalated instead of sent to Gemini. Market pricing is outside the biophysical evidence scope.

## Analysis API

Example request:

```json
{
  "farmId": "registered-farm-uuid",
  "plotId": "registered-plot-uuid",
  "branchId": "optional-branch-uuid",
  "simulationRunId": "optional-completed-run-uuid",
  "comparisonId": "optional-comparison-uuid",
  "question": "Explain the latest scientific result for this plot.",
  "language": "kn",
  "includeWeather": true,
  "includeSoil": true,
  "includeCrop": true,
  "includeSimulation": true,
  "includeComparison": true,
  "forceRefresh": false
}
```

`branchId` selects a branch; `comparisonBranchId` identifies the alternative branch when selecting a pair. `comparisonId` identifies a persisted comparison record and is not interchangeable with a branch ID. If an explicit run is given, its farm, plot, branch, status, snapshot hash, and persisted C3 records are checked. If only a branch is given, the latest completed run for that exact branch is selected. With neither, the latest completed run for the farm and plot is selected deterministically. Missing runs remain missing evidence; the service never substitutes a different branch.

For a selected run, the persisted C1 snapshot referenced by that run is authoritative. The service validates its farm/plot ownership and input hash, validates C1 and each C3 payload against the shared contracts, and preserves weather-member identity. It does not silently fetch newer weather in place of historical simulation inputs. A general analysis without a selected run can use the environmental preparation service; the response labels that evidence as new or cached preparation.

Persisted C5 comparison evidence is included only when the comparison's farm, plot, branch pair, two completed run references, matched-input status, comparison date, C5 payload, and run provenance agree. Non-comparable records provide their recorded reasons but never numerical differences.

Errors use the standard API error envelope with a stable error code and correlation ID. Successful responses include `analysisId`, farm/plot identity, selected evidence references, localized summary/sections, validated claims, evidence and freshness summaries, scientific limitations, escalation notices, guardrail status, generation mode, and creation time.

The evidence summary also identifies the crop's scientific name and engine version, simulation warnings, comparison branch/run pair and date, plus validated C5 assumptions/provenance when a comparable C5 record is available. If a comparison is selected without a run, its recorded baseline run is used for the simulation context so the C3 and C5 evidence cannot silently refer to different runs.

## Claim validation and generation

Each quantitative claim must identify one available source field and match that field's value, unit, source ID, metric, evidence category, staleness, and required qualifications. Missing/unavailable measurements do not become zero. Numeric text in optional Gemini output must be represented by validated structured claims; malformed or unverifiable output is discarded as a whole.

Gemini is optional and configured with `GEMINI_API_KEY` (also supported through the project `.env` settings). Without a key, on provider failure, or after validation rejection, the deterministic explainer remains available. The UI identifies deterministic, Gemini, and deterministic-fallback generation modes.

Environmental weather retrieval age and forecast period, static/modelled soil designation, persisted snapshot age, historical simulation completion, and comparison creation time are reported separately. State dates are not interpreted as observation timestamps.

## Voice and language boundaries

The UI supports English (`en`/`en-IN`), Kannada (`kn`/`kn-IN`), and Hindi (`hi`/`hi-IN`). Speech recognition uses the browser Web Speech API when available and only transcribes into an editable text field. Speech synthesis requires an available matching browser/device voice; an unavailable voice does not block text interaction. No offline speech capability is promised.

## Verification

Run the focused checks from the repository root:

```powershell
python -m pytest tests/services/test_analysis.py tests/services/test_analysis_persistence.py tests/api/test_analysis_router.py tests/api/test_crops_interaction_router.py
ruff check apps/api/app/services/analysis tests/services/test_analysis.py tests/services/test_analysis_persistence.py tests/api/test_analysis_router.py
npm run typecheck:web
npm run lint:web
npm run build:web
```
