# TerraPulse 2.0 — Fresh Implementation Issue Plan

Repository: `ShreyaJ-27/Vasundara-Agricultural-Decision-Laboratory`  
Target branch: `main`    
Team: four developers  
Issue count: 28

## Team ownership

| Role | Ownership |
|---|---|
| Dev A — Science | FAO-56/AquaCrop adapters, scientific state, simulation validity, branch comparisons, water accounting |
| Dev B — 3D | Living Field, scientific visual-state integration, Future Fold 3D experience and performance |
| Dev C — Agricultural data | Crop identity/capabilities, weather, soil, environmental provenance and validation |
| Dev D — Product/integration | Repository foundation, contracts, database/API integration, farmer UX, AI orchestration, offline, security, CI/deployment |

Names/usernames are intentionally not assigned because the four GitHub usernames have not been provided. Assign these roles to the four team members in GitHub.

## Global implementation rules

- No sensors, Arduino, ESP32, drones or other dedicated hardware are required.
- One authoritative scientific engine per plot and branch. Visuals never invent or alter scientific values.
- Preserve the distinction between available, missing, invalid, unsupported and genuine zero values.
- Every environmental/scientific result must retain units, source/provenance, retrieval or run time, model/parameter version and limitations.
- Offline mode may reopen cached, verified results and queue supported edits; it must never pretend stale data is live or run cloud-only work offline.
- Use focused feature branches and PRs into an agreed integration branch; keep `main` demo-ready.

---

## Sequential issues

### Issue 1 — [P0] Establish the fresh monorepo and local development environment
**Owner:** Dev D  
**Depends on:** None

Create the project foundation on `main`. Set up the React + TypeScript + Vite client, Python FastAPI service, shared development configuration, environment examples, lint/format scripts and a reproducible local startup (Docker Compose may provide PostgreSQL). Define a clear folder structure for app, API, science, data, contracts and tests. Avoid adding unnecessary infrastructure.

**Acceptance criteria**
- [ ] Frontend and API start locally using documented commands.
- [ ] `/health` returns a successful API response.
- [ ] `.env.example` files exist; secrets are not committed.
- [ ] Linting, formatting and type-check commands work.
- [ ] A clean clone can follow the setup instructions.

### Issue 2 — [P0] Define shared C1–C8 contracts and API conventions
**Owner:** Dev D, with review from Dev A/B/C  
**Depends on:** Issue 1

Publish versioned TypeScript and Pydantic contracts for C1 environmental inputs, C2 farm/plot definition, C3 scientific states, C4 branches/decisions, C5 evaluation/comparison, C6 visual state, C7 model capabilities/provenance and C8 shared resources. Define IDs, units, dates, branch identity, missingness semantics, API error envelope and representative fixtures. This is the shared interface all developers build against.

**Acceptance criteria**
- [ ] TypeScript and Python schemas represent the same JSON contracts.
- [ ] Fixtures validate in both stacks.
- [ ] Units, source IDs, timestamps and missing/invalid/unsupported states are explicit.
- [ ] API error shape and versioning rules are documented.
- [ ] Contract changes require fixture updates.

### Issue 3 — [P0] Build database schema, migrations and persistence layer
**Owner:** Dev D  
**Depends on:** Issues 1–2

Set up PostgreSQL (PostGIS for farm geometry) and migrations. Add persistence for farms, plots, crop identities, environmental snapshots, simulation runs, scientific states, branches, comparisons, resource ledgers, users/roles and provenance. Keep database access behind repository/service boundaries. Any seed data must be clearly labelled as demo fixtures.

**Acceptance criteria**
- [ ] Migrations build the schema from an empty database.
- [ ] Core entities have stable IDs and relationships.
- [ ] Spatial farm/plot fields use an explicit coordinate reference system.
- [ ] Tests cover create/read paths for the core entities.
- [ ] Demo records are distinguishable from real farmer records.

### Issue 4 — [P0] Implement farm, plot and crop onboarding APIs
**Owner:** Dev D + Dev C  
**Depends on:** Issues 2–3

Create APIs to register a farm, confirm its location, optionally store a boundary, create plots, store plot area/planting date and attach a crop identity. Validate coordinate ranges, units and required fields. Return stable IDs and persist the data. Do not assume that a device GPS fix is the verified farm boundary; require user confirmation.

**Acceptance criteria**
- [ ] Farm and plot create/read endpoints work against the database.
- [ ] Coordinates and area units are validated.
- [ ] A plot references a resolved crop identity.
- [ ] Invalid input returns field-level errors, not silent defaults.
- [ ] API tests cover the successful and invalid paths.

### Issue 5 — [P0] Implement crop identity resolution and model capability registry
**Owner:** Dev C + Dev A  
**Depends on:** Issue 2

Build a versioned crop catalogue with common, local and scientific aliases. Use AGROVOC/GBIF/ECOCROP references where appropriate, preserving source and version. Resolve ambiguous names with a confirmation step. For every supported crop, register the valid engine, parameter provenance, supported output metrics and limitations. Unsupported crops may receive identity/ecology information only, never fabricated simulation values.

**Acceptance criteria**
- [ ] Common/local/scientific aliases resolve to stable crop IDs.
- [ ] Ambiguous matches require user confirmation.
- [ ] Capability registry declares engine and supported outputs.
- [ ] Parameter source/version and limitations are retained.
- [ ] Unsupported crop paths do not return invented yield/growth metrics.

### Issue 6 — [P0] Integrate weather and ensemble data adapter
**Owner:** Dev C  
**Depends on:** Issue 2

Integrate Open-Meteo for supported historical/forecast weather and ensemble information. Normalize units, dates and time zones; preserve source, retrieval timestamp, quality status and ensemble member identity. Add timeouts, retry policy, caching and a typed unavailable response. Provide deterministic fixtures for development and tests.

**Acceptance criteria**
- [ ] Adapter returns normalized, validated weather records.
- [ ] Source, retrieved-at time and ensemble member ID are retained.
- [ ] API failure and incomplete coverage return explicit statuses.
- [ ] Cache entries expose age/freshness.
- [ ] Tests use fixtures and do not depend on a live API.

### Issue 7 — [P0] Integrate soil data adapter and provenance
**Owner:** Dev C  
**Depends on:** Issue 2

Integrate SoilGrids WCS or the selected supported SoilGrids endpoint to retrieve available soil properties by depth for a confirmed location. Normalize units and preserve grid coordinates, data version, source and NoData masks. Label outputs as modelled soil properties, not live field measurements or measured soil moisture.

**Acceptance criteria**
- [ ] Adapter returns depth-indexed soil properties where available.
- [ ] NoData remains missing and is never converted to zero.
- [ ] Source/version, grid location and retrieval metadata are retained.
- [ ] Unsupported properties/depths are explicitly marked.
- [ ] Tests cover valid data, NoData and source failure.

### Issue 8 — [P0] Build environmental input preparation and validation service
**Owner:** Dev C + Dev A  
**Depends on:** Issues 5–7

Combine soil, weather and crop capability information into the C1 input contract. Validate units, time coverage, dates, soil depth availability, missingness and provenance before simulation. Cache valid snapshots and expose clear freshness labels. If inputs are insufficient, block or downgrade the simulation pathway instead of filling gaps with invented values.

**Acceptance criteria**
- [ ] C1 snapshot combines crop, soil and weather references.
- [ ] Invalid units, missing coverage and NoData are handled explicitly.
- [ ] Snapshot includes source and freshness metadata.
- [ ] Supported vs insufficient-input states are clear to callers.
- [ ] Deterministic tests cover valid and invalid combinations.

### Issue 9 — [P0] Implement scientific engine boundary and FAO-56 water-balance pathway
**Owner:** Dev A  
**Depends on:** Issues 2, 5 and 8

Create the common scientific engine interface and implement the initial FAO-56/root-zone water-balance pathway for the selected supported crop workflow. Calculate only outputs supported by the implementation and stated assumptions, such as ET, crop-water demand, root-zone depletion and irrigation/stress indicators. Add unit, conservation and golden-fixture tests.

**Acceptance criteria**
- [ ] Engine accepts validated contracts and returns typed scientific states.
- [ ] Units and assumptions are explicit.
- [ ] Water balance passes documented tolerance checks.
- [ ] Identical complete inputs reproduce the same output within documented numerical tolerance.
- [ ] Unsupported biological growth/yield metrics are omitted or marked unsupported.

### Issue 10 — [P0] Integrate AquaCrop-OSPy for one validated supported crop
**Owner:** Dev A  
**Depends on:** Issues 5 and 9

Integrate AquaCrop-OSPy 3.1.0 behind the common engine interface for at least one crop with defensible parameter data. Pin the dependency, document licensing/redistribution constraints, validate required inputs, filter unexecuted output slots and persist model/parameter versions. Do not claim universal calibration for other crops or regions.

**Acceptance criteria**
- [ ] AquaCrop adapter runs the selected supported fixture reproducibly.
- [ ] Engine and parameter versions are attached to output.
- [ ] Unexecuted/invalid output rows are excluded.
- [ ] Unsupported crop/parameter combinations fail safely.
- [ ] Golden fixtures cover the supported scenario.

### Issue 11 — [P0] Build simulation orchestration and scientific-state APIs
**Owner:** Dev A + Dev D  
**Depends on:** Issues 3, 8–10

Create simulation submission, job-status and result APIs. Select exactly one authoritative engine per plot and branch, execute it, validate output and persist C3 states with input hashes, model version, parameter version, weather identity and provenance. Provide typed failure states and correlation IDs.

**Acceptance criteria**
- [ ] Client can submit a simulation and retrieve its status/result.
- [ ] Exactly one engine is authoritative for each run.
- [ ] C3 results persist with units and provenance.
- [ ] Invalid inputs and engine failures have typed responses.
- [ ] End-to-end API test reaches a valid scientific result.

### Issue 12 — [P0] Build responsive farmer application shell and navigation
**Owner:** Dev D  
**Depends on:** Issue 1

Build the React application shell and reusable components for Connect, Assisted and Observatory modes. Make mobile-first Connect mode the primary entry. Add accessible navigation, language selection, large touch targets, loading/empty/error/offline states and a graceful non-WebGL path. Basic farmer access must remain usable if the 3D scene fails.

**Acceptance criteria**
- [ ] Responsive shell works at mobile and desktop viewports.
- [ ] Connect, Assisted and Observatory routes are navigable.
- [ ] Keyboard and screen-reader basics are supported.
- [ ] Loading, empty, error and offline states are present.
- [ ] WebGL is not required to use Connect mode.

### Issue 13 — [P0] Implement farmer farm/plot/crop onboarding interface
**Owner:** Dev D + Dev C  
**Depends on:** Issues 4, 5 and 12

Build the guided user flow to confirm a field location, create a farm and plot, enter area/planting details and choose a crop by local/common/scientific name. Use touch-first choices and optional voice input where supported, but always provide a text/touch fallback. Connect to the actual APIs and show confirmation before saving.

**Acceptance criteria**
- [ ] Farmer can complete onboarding from the UI and persist records.
- [ ] Crop ambiguity is shown for user confirmation.
- [ ] Location and plot details can be reviewed before save.
- [ ] Validation errors are understandable and actionable.
- [ ] Flow works without voice or 3D.

### Issue 14 — [P0] Build environmental evidence and simulation result screens
**Owner:** Dev D + Dev A + Dev C  
**Depends on:** Issues 8, 11 and 12

Show the selected field's soil/weather input summary, data source and freshness, model capability and simulation status. Render result cards for supported metrics with units, short explanations, uncertainty/limitations and provenance access. Clearly distinguish cached/stale data from live data. Never display missing/unsupported metrics as zero.

**Acceptance criteria**
- [ ] UI displays supported results from the real API.
- [ ] Units, source and last-updated/run time are visible.
- [ ] Missing/unsupported metrics are not rendered as zero.
- [ ] Model limitations and warnings are visible.
- [ ] Loading, failure and no-result cases are handled.

### Issue 15 — [P0] Build the Living Field 3D scene and plot navigation
**Owner:** Dev B  
**Depends on:** Issues 2 and 12

Create the Three.js/React Three Fiber Observatory with navigable terrain, plot boundaries/identities, crop representations and camera controls. Use real farm/plot identifiers from shared state. Prioritize a coherent performant scene over decorative effects. Include reduced-quality mode and a graceful fallback for devices without WebGL support.

**Acceptance criteria**
- [ ] User can navigate the field and select a plot.
- [ ] Rendered plot IDs match application state.
- [ ] Camera controls work on desktop and touch.
- [ ] Reduced-quality mode is available.
- [ ] Observatory failure does not break Connect mode.

### Issue 16 — [P0] Connect scientific states to Living Field visual states
**Owner:** Dev B + Dev A + Dev D  
**Depends on:** Issues 11 and 15

Map C3/C6 scientific state to the visual field: plot, branch and absolute date must match the selected result. Visual interpolation may improve presentation but cannot change numerical state. Show capability/provenance context and ensure the visual layer gracefully handles unavailable metrics.

**Acceptance criteria**
- [ ] Selecting a plot displays its corresponding scientific state.
- [ ] Branch/date identity matches the API result.
- [ ] Visual interpolation never mutates simulation values.
- [ ] Unsupported values do not appear as fabricated visual indicators.
- [ ] Automated or reproducible integration check validates identity matching.

### Issue 17 — [P0] Implement immutable decision branches and farm timeline
**Owner:** Dev D + Dev A  
**Depends on:** Issues 3 and 11

Implement branch creation for supported management decisions such as planting date and irrigation. Store branch ID, parent ID, effective date, decision diff, base snapshot/input hashes, model version and weather-member identity. Rewind must create a new child branch; prior branches are immutable.

**Acceptance criteria**
- [ ] A change creates a new branch with parent linkage.
- [ ] Parent branch data remains unchanged.
- [ ] Decision, effective date and input/model identity are recorded.
- [ ] Branch history can be listed and reopened.
- [ ] Tests verify immutable lineage and replay identity.

### Issue 18 — [P0] Implement Future Fold independent simulations and comparison API
**Owner:** Dev A + Dev D  
**Depends on:** Issues 11 and 17

Run original and alternative branches independently using matched farm, plot, soil, model, simulation period and weather-member identity for management comparisons. Compare synchronized dates and only common supported metrics. Mark unmatched inputs/capabilities as not comparable; retain assumptions and provenance for every comparison.

**Acceptance criteria**
- [ ] Both branches have independent simulation runs.
- [ ] Controlled comparisons enforce matched required inputs.
- [ ] Comparison returns only supported common metrics.
- [ ] Non-comparable branches are clearly rejected/labelled.
- [ ] Comparison output includes assumptions and provenance.

### Issue 19 — [P0] Build the Future Fold comparison experience
**Owner:** Dev B + Dev D  
**Depends on:** Issues 16 and 18

Build a split-screen or swipe comparison of the original and alternative futures. Synchronize date/timeline and camera where two 3D views are used. Show which decision changed, comparable metrics, uncertainty and limitations. On mobile or low-end hardware, use a clear card comparison rather than forcing dual 3D rendering.

**Acceptance criteria**
- [ ] Farmer can choose a supported what-if decision and view both outcomes.
- [ ] Both sides show the same comparison date and matched weather identity.
- [ ] Changed inputs and supported metric differences are clear.
- [ ] Mobile fallback works without dual 3D rendering.
- [ ] Incomparable results are not presented as a valid comparison.

### Issue 20 — [P1] Implement shared-water resource ledger and accounting
**Owner:** Dev A + Dev D  
**Depends on:** Issues 17–18

Implement branch-scoped shared water resources, plot allocations, requested/withdrawn/effective irrigation, losses and closing reserve. Enforce conservation and prevent double allocation. Counterfactual branch ledgers must remain isolated from the original branch.

**Acceptance criteria**
- [ ] Water allocations and withdrawals reconcile within documented tolerance.
- [ ] No negative or double-counted allocation is accepted.
- [ ] Each branch has an independent ledger.
- [ ] Ledger outputs expose units and assumptions.
- [ ] Conservation and conflict tests pass.

### Issue 21 — [P0] Implement evidence-grounded AI Analysis service
**Owner:** Dev D + Dev A + Dev C  
**Depends on:** Issues 5, 11 and 18

Build an analysis endpoint that retrieves farm, plot, branch, scientific state, comparison, crop capability and provenance before generating an explanation. AI may summarize supported results, uncertainty and assumptions, but may not invent yield, prices, disease diagnoses or live forecasts. Validate every quantitative statement against retrieved evidence and provide deterministic templates/escalation when evidence is insufficient.

**Acceptance criteria**
- [ ] AI receives a structured evidence bundle from trusted services.
- [ ] Numerical claims map to source fields/IDs.
- [ ] Unsupported questions return a limitation or human-escalation response.
- [ ] Stale inputs are labelled as stale.
- [ ] Deterministic fallback works when the AI provider is unavailable.

### Issue 22 — [P1] Add local-language text and voice interaction
**Owner:** Dev D + Dev C  
**Depends on:** Issues 12 and 21

Add language selection and a bounded farmer interaction flow. Support speech-to-text/text-to-speech when available, with text/touch fallback. Deliver at least one demonstrable local-language path. Clearly report unsupported device/network capabilities; do not make voice mandatory or imply that offline speech works unless a local language pack is installed.

**Acceptance criteria**
- [ ] Farmer can select a supported language.
- [ ] Text/touch journey remains complete without microphone access.
- [ ] Voice capability is detected and failure handled gracefully.
- [ ] Responses preserve scientific limitations and meaning.
- [ ] At least one bounded local-language intent is demonstrated.

### Issue 23 — [P0] Implement offline PWA, cached farm records and result reopen
**Owner:** Dev D  
**Depends on:** Issues 12 and 14

Configure the web app as an installable PWA with Service Worker caching and IndexedDB persistence. Cache farm profiles, crop catalogue, verified environmental snapshots and scientific results. Reopen the last verified result offline with source, last-sync and stale indicators. Cloud-only simulations and live API retrieval must be reported unavailable offline.

**Acceptance criteria**
- [ ] App shell and permitted records are available after initial sync.
- [ ] A verified result reopens with network disabled.
- [ ] Freshness/source labels remain visible offline.
- [ ] Live weather/soil refresh is not falsely claimed offline.
- [ ] Browser storage failure is handled without data corruption.

### Issue 24 — [P1] Implement offline operation queue and safe synchronization
**Owner:** Dev D  
**Depends on:** Issues 17 and 23

Queue supported profile edits and user decisions with stable IDs, base snapshot versions and idempotency keys. Sync when connectivity returns. Merge safe profile changes and explicitly block/reconcile conflicting scientific states or resource ledgers. Show sync status and actionable conflict messages.

**Acceptance criteria**
- [ ] Offline changes are queued and survive app restart.
- [ ] Replayed operations are idempotent.
- [ ] Safe profile changes sync successfully.
- [ ] Scientific/resource conflicts never silently overwrite state.
- [ ] User sees sync and conflict status.

### Issue 25 — [P0] Add authentication, roles, consent and farm-data controls
**Owner:** Dev D  
**Depends on:** Issues 3, 4 and 12

Implement a practical authentication/session approach and role-aware access for farmer, field agent/FPO and administrator. Capture consent for farm location, voice and institutional sharing. Enforce data minimization, authorization, secure transport, export/deletion pathways and audit logs. Avoid exposing precise farm coordinates to roles that do not need them.

**Acceptance criteria**
- [ ] Protected APIs enforce the user's role and farm access.
- [ ] Consent is captured before optional data collection/sharing.
- [ ] Precise location is not exposed unnecessarily.
- [ ] Export/deletion requests have a documented supported path.
- [ ] Secrets and sensitive data are not written to client logs.

### Issue 26 — [P0] Add CI, full-stack deployment and operational checks
**Owner:** Dev D, with all developers fixing their failing tests  
**Depends on:** Issues 1–2; complete before final release

Set up CI for frontend lint/build, backend tests, contract checks, scientific golden fixtures and browser smoke tests. Deploy the frontend, API and database-backed service as a full-stack application. Add health/readiness endpoints, environment documentation, migrations, structured logs and a reproducible demo configuration.

**Acceptance criteria**
- [ ] CI runs relevant tests on every PR.
- [ ] Deployed frontend can call the deployed API and database-backed services.
- [ ] Health/readiness checks report dependency failures.
- [ ] Migrations run in the documented deployment process.
- [ ] Deployment commit and model/schema versions are identifiable.

### Issue 27 — [P0] Prepare reproducible demo data, setup guide and operator walkthrough
**Owner:** Dev D + all developers  
**Depends on:** Issues 4, 11, 14, 18 and 21

Create a clearly labelled demo farm, plot, supported crop and environmental fixture so the full journey can be demonstrated without relying on live third-party APIs. Add a reset/seed command, setup guide, API/architecture overview, known limitations and a short operator walkthrough. Demo data must never be represented as a real farmer's measured field data.

**Acceptance criteria**
- [ ] One command seeds the labelled demo scenario.
- [ ] Demo can run when external APIs are unavailable.
- [ ] Seed/reset process is documented and repeatable.
- [ ] Known limitations and prototype capabilities are documented.
- [ ] A new team member can launch and run the demo from the guide.

### Issue 28 — [P0] Complete end-to-end acceptance, performance and release verification
**Owner:** All four developers  
**Depends on:** Issues 11, 16, 18–19, 21, 23, 25–27

Verify the complete journey: register/confirm field, choose a supported crop, retrieve labelled soil/weather inputs, run a supported simulation, explore the Living Field, change a planting/irrigation decision, compare matched Future Fold branches, receive an evidence-grounded AI explanation and reopen cached results offline. Test desktop/mobile, WebGL fallback, API failures, stale data, accessibility basics, performance and privacy controls. Fix all P0 blockers before marking the project complete.

**Acceptance criteria**
- [ ] Complete farmer journey passes on the deployed build.
- [ ] Scientific outputs and Future Fold comparisons pass golden/contract checks.
- [ ] Offline reopen works with network disabled and stale state labelled.
- [ ] Core Connect flow works on a mobile viewport without WebGL.
- [ ] Critical API, AI grounding, consent and authorization tests pass.
- [ ] No P0 bugs remain; demo labels fixtures/prototypes honestly.

---

## Recommended execution waves

The issue numbers provide a dependency order, not a rule that only one person can work at a time.

| Wave | Issues | Parallel work |
|---|---|---|
| 1. Shared foundation | 1–3 | Dev D establishes app, contracts and persistence. Dev A/B/C review contracts and prepare their modules. |
| 2. Data and core UI | 4–8, 12 | Dev C handles crop/weather/soil; Dev D handles APIs and app shell; Dev A reviews model inputs. |
| 3. Scientific and 3D core | 9–11, 13–16 | Dev A builds engines; Dev B builds Living Field; Dev C finalizes data; Dev D integrates onboarding/results. |
| 4. Decision loop | 17–21 | Dev A/D implement branches and comparisons; Dev B builds Future Fold presentation; Dev C supports evidence; Dev D implements grounded AI. |
| 5. Offline and release | 22–28 | Dev D leads voice/offline/security/deploy; all developers verify their modules and close acceptance gaps. |

## Definition of done for every issue

A focused PR is merged into the agreed integration branch; the feature is wired into the shared application; relevant automated tests or reproducible verification are included; no unsupported agricultural claim is introduced; and setup/configuration/docs are updated where needed.
