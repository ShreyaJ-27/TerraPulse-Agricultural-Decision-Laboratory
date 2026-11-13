# Integration handoff — Developer A to Developers C and D

Status: **Developer A v0.2 standalone science package**. Its legacy flat view targets Developer D's earlier prototype. The repository's current C1–C8 1.0 schemas in `packages/contracts` and `apps/api/app/contracts.py` use measurement envelopes and different shapes. Adapting those schemas to the engine and emitting repository-native C3 states remain integration work. See the [package README](../README.md) for evidence restoration.

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
2. Wire C1 soil/weather snapshot and D's C8 virtual ledger into `from_c1_with_root_depth` after C7 crop capability resolution.
3. Add a run service that calls `run_fao`, persists `runId` and dated states, and surfaces typed `ScienceError.code` to callers.
4. Use returned `v01C3` for backwards-compatible display; surface the scientific envelope and warnings in detailed results.
5. Implement branch-specific reruns and compare with explicit fork date. Do not use C5 comparison to hide two different input realizations.
6. Connect B's Living Field to plot/branch/date identity, with layered visualization labelled **illustrative** until independently backed by model layers.
7. Add integration tests against real Developer C inputs, state persistence, HTTP APIs and a browser journey. None are represented by this local science package.

## Acceptance handoff to full product

- Issues #5, #8, #9, #10, #11, #16, #18, #28 require work across C/D/B, documented under the TerraPulse GitHub repository.
- Institutional/organizer timing rules and selected field data remain external. No contest code was pushed by this task.
