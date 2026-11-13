# Integration handoff — Developer A to Developers C and D

Status: **Developer A v0.2 science package**. The new `repository_contracts.py` boundary uses the repository's C1/C3/C8 1.0 JSON shapes. The legacy flat view remains available. Application wiring and persistence remain Developer D work. See the [package README](../README.md) for evidence restoration.

## Issue #11 science execution

Configure `ScientificRunService(crop_binding=binding, c1_model=C1EnvironmentalInput,
c3_model=C3ScientificState)` at application startup. Use the trusted Crop Lens
resolver and canonical lookup to construct `binding` as described below.

Pass the authoritative `EnvironmentalInputResult.c1_input` model only after
checking `is_valid`, authorized farm/plot/branch UUIDs, an allocated simulation
run UUID, and the canonical crop UUID from confirmed server-side identity.
Pass `environmental_warnings=result.warnings`, explicit `turmeric_mapping`,
area, planting date, root depth, depletion fraction, initial depletion, weather
realization ID/kind and the normalized member ID (or `None` for deterministic).
Set `rainfed=True` explicitly or supply the matching C8 JSON and dated schedule.
The science service checks snapshot farm identity and revalidates C1. Crop binding
selects FAO-56 before execution. Missing ET₀ is fatal to FAO-56 even when C's
environmental service returns a valid snapshot with an ET₀ warning.

`execute(...)` returns either a completed result with `states`,
`scienceEnvelope`, `inputProvenance` and combined `warnings`, or
`{"status":"failed","error":{"code":...,"message":...,"stage":...}}`.
Stages are `input`, `engine`, and `output`. Failed results contain no partial
C3 rows. Developer D owns mapping codes to HTTP responses and treating unexpected
programming/infra exceptions as server errors, with correlation IDs in either case.

Developer D should store the C1 payload and `environmentalSnapshotHash` in
`EnvironmentalSnapshot`, its sources in `EnvironmentalProvenance`, and set
`SimulationRun` IDs, engine name/version, status and `input_hash` using the
returned identities, projected engine and `scienceEnvelope.inputHash`.
Persist each C3 row as `ScientificState.payload` with its date, availability,
plot, branch and run UUID. Preserve the full envelope and accompanying
`inputProvenance` and warnings under the same persistent run UUID. Current
`SimulationRun` columns cannot hold the complete envelope. D owns its storage
design and transaction, including crop binding, capability and parameter
version/hash, weather member/realization/hash, source provenance, schedule and
ledger hashes, envelope version and typed failures. C3's engine version alone
cannot reconstruct those values.

The repository pins Python 3.14.3. The science package requires Python 3.12+
and uses no AquaCrop runtime dependency for this FAO-56 boundary. Tests run
against the merged environmental service with offline adapter responses,
the real C1 models and real C3 validation.

## Issue #18 science follow-up

Keep the existing independent scenario comparators. For repository-facing C5,
validate the farm and persistent run/snapshot identities, carry the crop binding,
input hashes, assumptions and provenance for both scenarios, and project only
compatible dated metrics into the authoritative C5 model. Add tests for
rejecting mismatched farm or binding and for provenance through C5. Developer D
supplies the persisted branches, authorized fork/decision history and comparison
API. The existing numerical comparison evidence remains applicable.

## Repository contract 1.0 boundary

### Crop identity and science eligibility (Issue #5)

At application startup, construct `CropBindingService(resolve=CropLensResolver().resolve,
get_crop_by_id=get_crop_by_id)` using the repository's server-side resolver
and catalogue lookup. For farm FAO runs, call `service.run_fao(c1, query=...,
confirmed_crop_id=..., turmeric_mapping="A", **context)`, or `service.prepare_fao` when preparation
and execution are separate. Pass the same query and selected candidate UUID
after confirmation. The service resolves again, requires a matching candidate,
reads the current C7 declaration from the canonical record, then chooses A's
registered profile before invoking the C1 adapter. Do not forward request-body
C7, crop parameters or a caller-supplied registry into this path. The lower-level
FAO and fixture entry points remain for trusted scientific use.

| Developer C declaration | Developer A binding and required alignment |
| --- | --- |
| Turmeric `…0003`, `Curcuma longa`, FAO-56 `1.0`, `demo-1`, placeholder coefficient and empty parameter sources | Requires explicit selection of A's sourced provisional A/B/C profiles. Align the catalogue versions, sources, supported outputs and limitations with A before exposing them as application science. |
| Wheat `…0020`, `Triticum aestivum`, FAO-56 `1.0`, `fao56-wheat-standard` | Reports an engine mismatch. A verifies `Tunis-Wheat-example-3.1.0` only. Keep the example separate from farm eligibility, or register and verify a distinct FAO wheat pathway before enabling it. |
| Maize `…0010`, `Zea mays`, AquaCrop `3.1.0`, `aquacrop-maize-v1` | No verified A profile or adapter. Suppress numerical eligibility and yield/growth offers until a maize pathway is verified. |
| Pearl millet `…0031`, finger millet `…0032`, chickpea `…0041`, declared FAO-56 profiles | No verified A binding. Catalogue declarations alone cannot enable simulation. |
| Foxtail millet `…0033`, black gram `…0042`, upland cotton `…0050`, and off-catalogue identities | Identity/ecology only. No scientific run or simulated outputs. |

Developer D should map `CROP_CONFIRMATION_REQUIRED` to a selection step using
C's resolver candidates, prompt for a stage mapping on `CROP_MAPPING_REQUIRED`, and present mismatched or unsupported capabilities
without offering a run. Persist the returned `cropBinding` alongside the full
science envelope and C3 states. The binding does not change the shared C7
schema or Developer C's catalogue.

- **C1:** Pass the authoritative Pydantic model's `model_dump(mode="json", by_alias=True)` to `fao_input_from_c1_v1`. The adapter requires available depth in cm, field capacity and wilting point in m³/m³, daily rain and ET0 in mm and temperatures in °C. It verifies the selected member covers the entire simulation period, retains source records and hashes the full snapshot. Supply plot and branch UUIDs, plot area, planting date, a registered crop profile, fixed root depth, depletion fraction, initial depletion, weather realization ID and source kind. Declare rainfed operation explicitly, or supply C8 and its schedule. No independent runoff estimate is supplied by C1.
- **C3:** Pass a completed science envelope to `c3_states_from_run` with the farm UUID, persistent simulation run UUID and source records. FAO storage is end-of-day theta multiplied by fixed root depth. FAO stress is severity (1 − Ks). Crop demand is potential daily ET. AquaCrop storage uses Wr where exported. The projector marks unexported fluxes missing and leaves ambiguous `rootZone` and daily yield unsupported. Keep the full science envelope for explicit depletion, capability versions, seasonal yield and audit evidence. The authoritative Pydantic C3 model validates the projected rows in tests.
- **C8:** The repository ledger is an aggregate. Provide Developer D's dated schedule alongside its exact JSON: `{ledgerHash, resourceId, plotId, days: [{date, effectiveLitres}]}`. `ledgerHash` is the science package's `stable_hash` of the same C8 JSON. Provide one entry per delivery date within the run window, with effective litres summed across deliveries for that plot and resource. The adapter validates farm/branch/plot/resource identity, litre units, availability, unique allocations and dates, opening minus withdrawals equals closing, losses equal withdrawals minus effective litres, and dated totals equal the plot allocation. It converts effective litres divided by plot area to mm. Missing schedule data never becomes an invented delivery. Developer D owns the schedule's dates, snapshot and fork history. The shared C8 shape fixture's closing volume is 8,900 L for 10,000 L opening and 1,000 L withdrawn. The science boundary rejects that balance and the positive test uses 9,000 L without altering the shared fixture.

## C1 → model input (C's responsibility + A's validator)

The package's legacy C1 adapter expects the earlier prototype shape:

```ts
{ weather: [{date, ensembleMemberId, rainfallMm, referenceEtMm,
  minTemperatureC, maxTemperatureC, provenance}],
  soilLayers: [{fromCm, toCm, fieldCapacityM3M3, wiltingPointM3M3, provenance}] }
```

Use `from_c1_with_root_depth(...)` in `src/terrapulse_science/c1_c8.py`. This function **requires** an explicit root depth and a sourced depletion fraction, as well as one selected weather ensemble member and input snapshot identity. The root depth is *not* silently inferred from a district-center coordinate.

**Blocked cases:** missing ET0 or rain, missing date(s), mixed members, negative values, `NoData`, gaps in soil depth, heterogeneity across the modelled root zone, FC≤WP, unbounded/invalid coordinates in upstream farm validation, or missing provenance. An explicit single-zone FAO model cannot be passed a richer multilayer soil as if it had simulated each layer. Additional real hydrology must be separately implemented and tested.

No forecast ensemble member is averaged into a fictitious daily observation. A result is for **exactly one selected weather realization and member**; alternative forecast members require separate runs and correctly labelled comparisons.

## C8 → effective field irrigation

Developer D's `IrrigationEntry.effectiveIrrigationDepthMm` is net water infiltrated (mm). It equals `effectiveLiters / plotAreaM2`, because `1 L/m² = 1 mm`.

The adapter verifies entry conservation `withdrawn = effective + loss`, the sum `initial - withdrawals = remaining`, branch IDs, unique allocation IDs, and per-plot depth conversion. It does not decide how much water should be withdrawn. It deliberately **does not infer irrigation efficiency**. D must still ensure requested/withdrawn volumes and authorized plots are correct before writing its ledger.

The initial soil-water state and fixed zone depth are **separate** from D's shared reservoir. The same reservoir volume must not be counted as available to both sibling branches simultaneously *within a branch*. A branching scenario gets its own virtual ledger with inherited historical transactions through the authorized fork, as D's existing design provides.

## Advisory signals and stress display

**Developer D.** Pass the persisted `scienceEnvelope`, the decision date, and
the simulation's persisted identity and input provenance to the package:

```python
from terrapulse_science import evaluate_advisory_signals, compare_advisory_signals

advisory = evaluate_advisory_signals(
    simulation["scienceEnvelope"],
    date="2026-06-07",
    simulation_run_id=simulation["simulationRunId"],
    input_provenance=simulation.get("inputProvenance"),
)
comparison = compare_advisory_signals(
    baseline["scienceEnvelope"], alternative["scienceEnvelope"],
    date="2026-06-07", fork_date="2026-06-07",
    baseline_simulation_run_id=baseline["simulationRunId"],
    alternative_simulation_run_id=alternative["simulationRunId"],
    baseline_input_provenance=baseline.get("inputProvenance"),
    alternative_input_provenance=alternative.get("inputProvenance"),
)
```

Both return JSON-compatible dictionaries. Each signal supplies the decision
category, metric, unit, date, trigger, supporting values, model and parameter
provenance, and confidence limitations. Use the per-metric status in `metrics`.
`available` can include zero. `inactive` marks a date outside the crop season.
`unavailable` means evidence is missing for this run or date. `unsupported`
means the engine has no comparable output. An inactive FAO-56 day retains
modeled soil depletion and emits no crop signal. AquaCrop can supply potential
ET from the registered historical example. Its storage metric supplies no
FAO-56 depletion or Ks.

The FAO-56 `monitor-depletion` condition compares end-of-day headroom to today's
potential crop ET. This one-day screening heuristic assumes today's demand rate
and leaves future rainfall and irrigation unevaluated. `irrigation-review`
fires when same-day Ks is below 1 after wetting, or when end-of-day depletion
exceeds modeled readily available water (RAW). The two tests use different
points in the day's water balance. `crop-water-demand` reports modeled
potential ET in mm/day. Comparison alerts require matched runs, an explicit
fork date, and two available active crop values on the selected date. The
comparison reports when the choices fall on opposite sides of RAW or the Ks
stress boundary. These are review inputs. Delivery amounts and field
verification remain separate decisions. [FAO-56 Chapter 8](https://www.fao.org/4/x0490e/x0490e0e.htm)

**Developers B and D.** The observatory response wraps persisted C3 in
`data.state`. Read `state.waterStress.value` only when
`state.waterStress.availability.status === "available"`. C3
`waterStress` is `1 - Ks` in ratio units, so 0 means no modeled stress and 1
means maximum modeled stress. If retaining the existing illustrative
`raw Ks < 0.5` color cutoff, its C3 equivalent is `waterStress.value > 0.5`.
The raw science envelope uses `states[i].metrics.waterStressKs.value` and
`metrics.waterStressKs.status`, with 1 meaning no modeled stress. C3
`soilWater` is storage, and C3 `cropWaterDemand` is the potential ET depth
for that date in mm. For depletion and explicit inactive status use the
science envelope. C3 1.0 represents inactivity as `missing` with a crop-inactive
reason, missing evidence as `missing`, and unsupported metrics as `unsupported`.
The frontend change belongs in the Living Field component.

### Demo evidence and shared water

The replay uses provisional turmeric mapping A, a fixed 0.30 m homogeneous
root zone, C1 fixture FC/WP of 0.28/0.12 m³/m³, fixed p of 0.4, and 10 mm
initial depletion. The single dry C1 fixture day (4.2 mm ET₀, zero rain) is
repeated for seven days as a scenario assumption. These are sensitivity results
with no established farm forecast validity.

On June 7 the baseline has 21.71 mm end-of-day depletion and Ks 0.9694.
The alternative receives the C8 fixture's 900 effective litres that day over
100 m² (9 mm), ends at 12.76 mm, and has Ks 1. Both use RAW of 19.20 mm.
The alternative opens with 10,000 L, withdraws 1,000 L including 100 L loss,
and closes with 9,000 L. The baseline independently closes with its full
10,000 L. C8 stock reconciliation uses opening = closing + withdrawals,
and each withdrawal comprises effective delivery plus loss. The adapter
rejects duplicate plot aggregates and duplicate dated rows, binds each schedule
to the exact branch ledger hash, and converts only reconciled net litres to
depth. The litres reconciliation tolerance is 0.000001 L.

## C3 output compatibility

Both engines return `contractVersion: science-0.2`, `scientificOutputVersion: dev-a-science-output-0.2.0`, `adapterVersion: dev-a-adapters-0.2.0`, and `registryVersion: dev-a-0.2.0`. The envelope includes `runId`, `modelVersion`, `capability`, `inputSnapshotId`, `weatherRealizationId`, `evidenceKind`, `warnings`, and dated `states`.

FAO-56 returns `inputHash`, `weatherMemberId` (possibly null), and a `weatherHash` of canonical dated weather records. AquaCrop returns `parameterVersion`, `parameterSource`, canonical `tableHashes`, and a source-file `weatherHash` (null when unknown). Its `evidenceKind` distinguishes executed runs, historical fixtures, and unverified supplied tables.

FAO-56 and active AquaCrop states include the flat `v01C3` compatibility view. AquaCrop preplant states have `v01C3: null`, and unexecuted slots are omitted. Extended metrics use `available` with a number, or `inactive`, `unsupported`, or `unavailable` with null. Groundwater depth in the registered AquaCrop example is `unavailable`. State status and run status are separate fields.

Persist branch, plot, date, run ID, engine and parameter metadata, and the engine-specific hashes and provenance. Developer D owns persistence, error mapping and access control.

## C4/C5 Future Fold

`compare_runs(run_a, run_b, fork_date=...)` requires distinct complete runs and matching soil, input snapshot, model version, crop parameters and complete absolute-weather series. Allowed changes: planting date and/or C8 irrigation allocation, provided their independent simulation runs actually reflect those decisions.

**Changed planting date:** the fork must precede the earlier planting date. All branches must share a common simulation start and initial soil state; the explicit `fallow_kc` is applied before planting. Soil is not reset when a late branch plants. Our fallow rule is an illustrative empirical assumption, *not* validated bare-soil evaporation; a better fallow hydrology pathway is a separate engineering/science workstream. A simulation window must cover both completed seasons before `seasonalActualEtMm` is compared.

**Daily comparison:** pair by `date`, not DAP. Only compare metrics available in both *crop-active* states. Inactive, post-season, missing and unexecuted crop states cannot substitute for zero. Any differences in weather member, crop parameter mapping, C1 snapshot or engine version make the comparison **not comparable**.

**AquaCrop:** `compare_aquacrop_runs` accepts independent 3.1.0 Tunis Wheat/SandyLoam outputs with matching verified weather and evidence kind. Compare two historical fixtures or two live executions. It pairs six completed seasonal dry yields and mutually available crop-active daily states. The reported seasonal harvest date is the interval end, one day after the final daily slot date.

**D's role:** independently check forked decision history, water-ledger inherited transactions, who can alter decisions, and branch persistence before accepting scenario results. A's `fork_date` guard alone is *not* a complete audit of historical decisions.

## C7 capability, outputs and provenance

`registry()` describes these default capabilities:

- Turmeric FAO-56: **conditional numerical pathway**, Kc maps A/B/C provisional. Yield, biomass, measured canopy and layered root hydrology unsupported.
- Tunis wheat AquaCrop: **published-example runtime and fixture**. Fresh AquaCrop-OSPy 3.1.0 runs for October 1 and November 1 passed 12/12 exact golden checks against historical fixtures and paired six harvest seasons. The profile balance covers 1,182 and 1,213 executed days respectively, with explicit field-capacity resets at planting. Changes across skipped intervals are unknown. The authorized release contains the original live execution record at `docs/test_logs/v02-live-golden.json`. See the README for local reproduction.

The registry also describes the opt-in FAO-56 dry-bean numerical reference. FAO-56 requires a registered parameter set and uses a fixed, homogeneous root zone. AquaCrop evidence establishes reproducibility for the registered rainfed Tunis wheat example. Local crop response, field calibration, yield accuracy and predictive uncertainty remain unverified. Additional profiles require applicable parameter sources and independent scientific review.

## Developer D integration sequence

1. Review `docs/science-contract-v0.2.d.ts` alongside the repository's shared schemas. Agree the mapping for units, availability, provenance and persistent IDs before exposing any output through the API.
2. Wire C1 soil/weather and D's C8 ledger plus dated schedule into `fao_input_from_c1_v1` after C7 crop capability resolution.
3. Add a run service that calls `run_fao`, persists `runId` and dated states, and surfaces typed `ScienceError.code` to callers.
4. Use `c3_states_from_run` for repository C3 and retain the science envelope and warnings in detailed results.
5. Implement branch-specific reruns and compare with explicit fork date. Do not use C5 comparison to hide two different input realizations.
6. Connect B's Living Field to plot/branch/date identity, with layered visualization labelled **illustrative** until independently backed by model layers.
7. Add integration tests against real Developer C inputs, state persistence, HTTP APIs and a browser journey. None are represented by this local science package.

## Acceptance handoff to full product

- Issues #5, #8, #9, #10, #11, #16, #18, #28 require work across C/D/B, documented under the TerraPulse GitHub repository.
- Institutional/organizer timing rules and selected field data remain external. No contest code was pushed by this task.
