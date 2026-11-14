import { useCallback, useEffect, useState } from "react";
import { Branch, Comparison, Farm, Simulation, TimelineEvent, apiClient } from "../services/apiClient";
import { LivingFieldScene } from "./living-field/LivingFieldScene";
import { branchScenario, scenePath, today, useFarmPlots, useFieldState } from "./living-field/fieldState";
import type { FieldSide } from "./living-field/LivingFieldScene";
import { EmptyState, ErrorState, LoadingState, PageContainer, ReusableCard } from "./ui";

const errorMessage = (error: unknown) => error instanceof Error ? error.message : "The request failed.";

type PlotWorkspace = { farmId: string; plotId: string; navigate: (path: string) => void };

export function Observatory({ farmId, plotId, navigate }: PlotWorkspace) {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [branchId, setBranchId] = useState("");
  const [date, setDate] = useState(() => new window.URLSearchParams(window.location.search).get("date") || today());
  const [reduced, setReduced] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const plots = useFarmPlots(farmId, plotId);

  useEffect(() => {
    let current = true;
    apiClient.listBranches(farmId, plotId).then(({ branches }) => {
      if (!current) return;
      const query = new window.URLSearchParams(window.location.search);
      const requested = query.get("branch") || query.get("branchId");
      const next = branches.find((branch) => branch.branchId === requested)
        ?? branches.find((branch) => !branch.parentBranchId) ?? branches[0];
      setBranches(branches);
      setBranchId(next?.branchId || "");
      if (!query.has("date") && next?.effectiveDate) setDate(next.effectiveDate);
    }).catch(() => { if (current) setUnavailable(true); });
    return () => { current = false; };
  }, [farmId, plotId]);

  const branch = branches.find((item) => item.branchId === branchId);
  const original = branch?.parentBranchId ? branches.find((item) => item.branchId === branch.parentBranchId) : branch;
  const alternative = branch?.parentBranchId ? branch : branches.find((item) => item.parentBranchId === original?.branchId && item.parentBranchId);
  const side = branch?.parentBranchId ? "alternative" : "original";
  const originalState = useFieldState(farmId, plotId, original?.branchId || "", date);
  const alternativeState = useFieldState(farmId, plotId, alternative?.branchId || "", date);
  const state = side === "alternative" ? alternativeState.state : originalState.state;
  const dateQuery = "?date=" + encodeURIComponent(date);

  return <PageContainer>
    <div className="page-intro"><p className="eyebrow">Observatory</p><h2>Living Field</h2>
      <p>Explore the farm, then inspect the stored model state for a plot, branch and date.</p></div>
    <div className="toolbar">
      <label>Branch<select aria-label="Branch" value={branchId} disabled={!branches.length} onChange={(event) => setBranchId(event.target.value)}>
        {!branches.length && <option value="">No saved branches</option>}
        {branches.map((item) => <option key={item.branchId} value={item.branchId}>
          {item.decisionType} · {item.branchId.slice(0, 8)}
        </option>)}
      </select></label>
      <label>Absolute date<input type="date" value={date} onChange={(event) => { if (event.target.value) setDate(event.target.value); }} /></label>
      <label className="checkbox"><input type="checkbox" checked={reduced} onChange={(event) => setReduced(event.target.checked)} /> Reduced quality</label>
    </div>
    {unavailable && <p role="status">Branch feed unavailable. The illustrative field is still available.</p>}
    <LivingFieldScene plots={plots} plotId={plotId} date={date} reduced={reduced} side={side}
      onSelectPlot={(id) => navigate(scenePath(farmId, id, "observatory") + dateQuery)}
      onChangeSide={(next) => setBranchId((next === "original" ? original : alternative)?.branchId || "")}
      original={branchScenario("original", original, originalState)}
      alternative={alternative ? branchScenario("alternative", alternative, alternativeState) : undefined} />
    {state && <ReusableCard><h3>Model provenance</h3>
      <p>{state.provenance.engine} {state.provenance.engineVersion} · {state.provenance.parameterVersion || "parameter version unavailable"}</p>
      <p>Run {state.simulationRunId} · snapshot {state.provenance.environmentalSnapshotId}</p>
    </ReusableCard>}
    <button type="button" className="secondary-button" onClick={() => navigate(scenePath(farmId, plotId, "future-fold") + dateQuery)}>Open Future Fold</button>
  </PageContainer>;
}

export function Timeline({ farmId, plotId, navigate }: PlotWorkspace) {
  const [events, setEvents] = useState<TimelineEvent[]>([]); const [branches, setBranches] = useState<Branch[]>([]); const [farm, setFarm] = useState<Farm>(); const [error, setError] = useState(""); const [snapshotId, setSnapshotId] = useState(() => new window.URLSearchParams(window.location.search).get("snapshot") || ""); const [parent, setParent] = useState(""); const [decision, setDecision] = useState("planting_date"); const [plantingDate, setPlantingDate] = useState(""); const [busy, setBusy] = useState(false); const [ledgerHash, setLedgerHash] = useState("");
  const load = useCallback(() => Promise.all([apiClient.getTimeline(farmId, plotId), apiClient.listBranches(farmId, plotId)]).then(([timeline, branchList]) => { setEvents(timeline.events); setBranches(branchList.branches); }).catch((e) => setError(errorMessage(e))), [farmId, plotId]);
  useEffect(() => { apiClient.getFarm(farmId).then(setFarm).catch((e) => setError(errorMessage(e))); void load(); }, [farmId, load]);
  const create = async () => { if (!snapshotId || !plantingDate) { setError("A persisted environmental snapshot and effective date are required."); return; } setBusy(true); try { await apiClient.createBranch(farmId, plotId, { plotId, environmentalSnapshotId: snapshotId, effectiveDate: plantingDate, decisionType: decision, parentBranchId: parent || null, decisionDiff: decision === "planting_date" ? { plantingDate } : { ledger: { ledgerHash } } }); setError(""); await load(); } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); } };
  if (!farm) return <PageContainer><LoadingState label="Loading farm timeline…" /></PageContainer>;
  return <PageContainer><div className="page-intro"><p className="eyebrow">Decision history</p><h2>{farm.name} timeline</h2><p>Every event is persisted. Reopening a branch never edits its record.</p></div>{error && <ErrorState label={error} />}<section className="form-panel"><h3>Save a decision</h3>{!snapshotId && <button className="secondary-button" onClick={() => navigate(`/farms/${farmId}/plots/${plotId}/environment`)}>Prepare environmental evidence</button>}<label>Environmental snapshot ID<input value={snapshotId} onChange={(e) => setSnapshotId(e.target.value)} placeholder="UUID from prepared evidence" /></label><label>Parent branch<select value={parent} onChange={(e) => setParent(e.target.value)}><option value="">Create baseline</option>{branches.map((branch) => <option key={branch.branchId} value={branch.branchId}>{branch.decisionType} · {branch.branchId.slice(0, 8)}</option>)}</select></label><label>Decision<select value={decision} onChange={(e) => setDecision(e.target.value)}><option value="planting_date">Planting date</option><option value="irrigation">Irrigation ledger</option></select></label>{decision === "irrigation" && <label>Water ledger hash<input value={ledgerHash} onChange={(event) => setLedgerHash(event.target.value)} /></label>}<label>Effective date<input type="date" value={plantingDate} onChange={(e) => setPlantingDate(e.target.value)} /></label><button className="primary-button" disabled={busy} onClick={create}>Save decision</button></section><section className="timeline">{events.length === 0 ? <EmptyState title="No timeline events" description="Create a baseline or submit a simulation to begin history." /> : events.map((event) => <article className="timeline-event" key={event.eventId}><time>{event.eventDate}</time><div><strong>{event.description}</strong><small>{event.eventType} · {event.branchId || "farm"}</small></div></article>)}</section></PageContainer>;
}

const lowerIsBetter = new Set(["rootzonedepletionmm", "waterstress"]);
const higherIsBetter = new Set(["waterstressks"]);
const metricLabels: Record<string, string> = {
  actualEtMm: "Actual evapotranspiration",
  potentialEtMm: "Potential evapotranspiration",
  rootZoneDepletionMm: "Root-zone depletion",
  waterStressKs: "Water stress coefficient",
  seasonalActualEtMm: "Seasonal actual evapotranspiration",
};

function metricRows(comparison?: Comparison) {
  const daily = comparison?.payload.result?.daily || [];
  const totals = new Map<string, { name: string; unit: string; a: number; b: number; n: number }>();
  const seasonal = (comparison?.payload.result?.metrics || []) as { name: string; unit: string; branchA: number; branchB: number }[];
  seasonal.forEach((metric) => {
    const row = totals.get(metric.name) || { name: metric.name, unit: metric.unit, a: 0, b: 0, n: 0 };
    row.a += metric.branchA;
    row.b += metric.branchB;
    row.n += 1;
    totals.set(metric.name, row);
  });
  daily.forEach((day) => day.metrics.forEach((metric) => {
    const row = totals.get(metric.name) || { name: metric.name, unit: metric.unit, a: 0, b: 0, n: 0 };
    row.a += metric.branchA;
    row.b += metric.branchB;
    row.n += 1;
    totals.set(metric.name, row);
  }));
  return [...totals.values()].map((row) => {
    const a = row.a / row.n;
    const b = row.b / row.n;
    const key = row.name.toLowerCase();
    const lower = lowerIsBetter.has(key);
    const directed = lower || higherIsBetter.has(key);
    const winner = !directed || a === b ? "Not assigned" : (lower ? b < a : b > a) ? "Alternative" : "Baseline";
    return { name: row.name, unit: row.unit, a, b, diff: b - a, percent: a === 0 ? null : ((b - a) / Math.abs(a)) * 100, winner, lower, directed };
  });
}

function decisionText(diff?: Record<string, unknown>) {
  const rows = Object.entries(diff || {}).filter(([, value]) => value == null || ["string", "number", "boolean"].includes(typeof value));
  return rows.length ? rows.map(([key, value]) => key + ": " + String(value)).join(" · ") : "Rainfed management. No extra change is recorded on this branch.";
}

function interpret(rows: ReturnType<typeof metricRows>) {
  const stress = rows.find((row) => row.name === "waterStressKs");
  const depletion = rows.find((row) => row.name === "rootZoneDepletionMm");
  const actual = rows.find((row) => row.name === "actualEtMm" || row.name === "seasonalActualEtMm");
  if (!stress && !depletion && !actual) return "This comparison does not include enough FAO-56 outputs to describe a trade-off. Yield, biomass and canopy cover are not produced by this engine.";
  const stressLine = stress
    ? (stress.a === stress.b ? "The water-stress coefficient is unchanged." : (stress.b > stress.a ? "The alternative" : "The original") + " has the higher water-stress coefficient, which means less simulated stress.")
    : "Water stress was not returned.";
  const waterLine = depletion
    ? (depletion.a === depletion.b ? " Root-zone depletion is unchanged." : (depletion.b < depletion.a ? " The alternative" : " The original") + " keeps less root-zone depletion.")
    : "";
  const etLine = actual ? " Actual evapotranspiration is shown as a difference, not as a recommendation." : "";
  return stressLine + waterLine + etLine + " Review the water requirement before approving a change. Yield and biomass are not outputs of FAO-56.";
}

export function DashboardLivingField({ farmId, plotId, side, onChangeSide, onSelectPlot }: {
  farmId: string; plotId: string; side: FieldSide; onChangeSide: (side: FieldSide) => void; onSelectPlot: (id: string) => void;
}) {
  const plots = useFarmPlots(farmId, plotId);
  const [pair, setPair] = useState<{ original?: Branch; alternative?: Branch; date: string; runA?: string; runB?: string }>({ date: today() });
  useEffect(() => {
    let current = true;
    Promise.all([apiClient.listBranches(farmId, plotId), apiClient.listComparisons(farmId, plotId)]).then(([branchList, comparisonList]) => {
      if (!current) return;
      const choices = branchList.branches;
      const baseline = choices.find((branch) => branch.decisionType === "baseline" || !branch.parentBranchId) || choices[0];
      const paired = comparisonList.comparisons.find((item) => item.baselineBranchId === baseline?.branchId) || comparisonList.comparisons[0];
      const alternative = choices.find((branch) => branch.branchId === paired?.alternativeBranchId)
        || choices.find((branch) => branch.parentBranchId && branch.branchId !== baseline?.branchId);
      const daily = paired?.payload.result?.daily || [];
      setPair({
        original: baseline, alternative, date: daily[0]?.date || baseline?.effectiveDate || today(),
        runA: paired?.baselineRunId, runB: paired?.alternativeRunId,
      });
    }).catch(() => { if (current) setPair({ date: today() }); });
    return () => { current = false; };
  }, [farmId, plotId]);
  const originalState = useFieldState(farmId, plotId, pair.original?.branchId || "", pair.date, pair.runA);
  const alternativeState = useFieldState(farmId, plotId, pair.alternative?.branchId || "", pair.date, pair.runB);
  return <>
    <LivingFieldScene plots={plots} plotId={plotId} date={pair.date} side={side} onChangeSide={onChangeSide} onSelectPlot={onSelectPlot}
      original={branchScenario("original", pair.original, originalState)}
      alternative={pair.alternative ? branchScenario("alternative", pair.alternative, alternativeState) : undefined} />
    <p className="subtitle">The side panel shows stored model outputs for {pair.date}. Predicted yield and biomass are not in this comparison, so they are not shown here.</p>
  </>;
}

export function FutureFold({ farmId, plotId, navigate, onOpenLivingField }: PlotWorkspace & {
  onOpenLivingField?: (side: FieldSide) => void;
}) {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [runs, setRuns] = useState<Simulation[]>([]);
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [dateOverride, setDate] = useState(() => new window.URLSearchParams(window.location.search).get("date") || "");
  const [side, setSide] = useState<FieldSide>("original");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  const [objective, setObjective] = useState<"water" | "balance">("balance");
  const [sowingDate, setSowingDate] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const plots = useFarmPlots(farmId, plotId);

  useEffect(() => {
    let current = true;
    Promise.allSettled([
      apiClient.listBranches(farmId, plotId), apiClient.listSimulations(farmId, plotId), apiClient.listComparisons(farmId, plotId),
    ]).then(([branchList, simulationList, comparisonList]) => {
      if (!current) return;
      const stored = comparisonList.status === "fulfilled" ? comparisonList.value.comparisons : [];
      const choices = branchList.status === "fulfilled" ? branchList.value.branches : [];
      const failures = [branchList, simulationList, comparisonList].flatMap((result) =>
        result.status === "rejected" ? [errorMessage(result.reason)] : []);
      const baseline = choices.find((branch) => branch.decisionType === "baseline" || !branch.parentBranchId) || choices[0];
      const paired = stored.find((item) => item.baselineBranchId === baseline?.branchId) || stored[0];
      const alternative = choices.find((branch) => branch.branchId === paired?.alternativeBranchId)
        || choices.find((branch) => branch.parentBranchId && branch.branchId !== baseline?.branchId);
      setBranches(choices);
      setRuns(simulationList.status === "fulfilled" ? simulationList.value.simulations : []);
      setComparisons(stored);
      setA(baseline?.branchId || "");
      setB(alternative?.branchId || "");
      setError(failures.join(" "));
    });
    return () => { current = false; };
  }, [farmId, plotId, reloadKey]);

  const original = branches.find((branch) => branch.branchId === a);
  const alternative = branches.find((branch) => branch.branchId === b);
  const runA = runs.find((run) => run.branchId === a && run.status === "completed");
  const runB = runs.find((run) => run.branchId === b && run.status === "completed");
  const latest = comparisons.find((item) => item.baselineBranchId === a && item.alternativeBranchId === b);
  const daily = latest?.payload.result?.daily || [];
  const date = dateOverride || daily[0]?.date || original?.effectiveDate || today();
  const originalState = useFieldState(farmId, plotId, a, date, latest?.baselineRunId ?? runA?.simulationRunId);
  const alternativeState = useFieldState(farmId, plotId, b, date, latest?.alternativeRunId ?? runB?.simulationRunId);

  const cropLabel = plots.find((plot) => plot.id === plotId)?.label || "";
  const live = /turmeric/i.test(cropLabel);
  const blocked = /maize|wheat|corn/i.test(cropLabel);
  const rows = live ? metricRows(latest) : [];
  const reading = interpret(rows);
  const snapshotId = runA?.environmentalSnapshotId || runB?.environmentalSnapshotId || "";
  const forkDate = [sowingDate, "2026-05-20"].filter(Boolean).sort()[0];
  const comparisonFork = new Date(forkDate + "T00:00:00Z");
  comparisonFork.setUTCDate(comparisonFork.getUTCDate() - 1);

  const runBaseline = async () => {
    if (!live || busy) return;
    setBusy("Retrieving weather and soil, then running the FAO-56 baseline…");
    setError("");
    setNotice("");
    try {
      const end = new Date();
      const start = new Date();
      start.setUTCDate(start.getUTCDate() - 20);
      const iso = (value: Date) => value.toISOString().slice(0, 10);
      const prepared = await apiClient.prepareEnvironment({
        farmId, plotId, includeEnsemble: false, requireQuantitativeSimulation: true,
        simulationPeriod: { startDate: iso(start), endDate: iso(end) },
      }) as { environmentalSnapshotId?: string; isValid?: boolean; errors?: string[] };
      if (!prepared.environmentalSnapshotId || prepared.isValid === false) {
        setError((prepared.errors || []).join(" ") || "Environmental evidence was not valid. No simulation was submitted.");
        return;
      }
      const queued = await apiClient.submitSimulation({
        farmId, plotId, environmentalSnapshotId: prepared.environmentalSnapshotId,
        irrigationMode: "rainfed", turmericMapping: "B",
      });
      let run = queued as Simulation;
      for (let attempt = 0; attempt < 24 && run.status !== "completed" && run.status !== "failed"; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        run = await apiClient.getSimulation(queued.simulationRunId);
      }
      if (run.status !== "completed") {
        setError(run.errorMessage || "The FAO-56 baseline did not complete.");
        return;
      }
      setNotice("FAO-56 baseline completed on the retrieved weather. Choose a sowing date to run the alternative.");
      setReloadKey((value) => value + 1);
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(""); }
  };

  const submit = async () => {
    if (!live || !runA || !runB || a === b || busy) return;
    setBusy("Comparing the two completed FAO-56 runs…");
    setError("");
    setNotice("");
    try {
      const result = await apiClient.createComparison(farmId, plotId, {
        baselineBranchId: a, alternativeBranchId: b, baselineRunId: runA.simulationRunId, alternativeRunId: runB.simulationRunId,
        forkDate: comparisonFork.toISOString().slice(0, 10),
      });
      setComparisons((current) => [result, ...current.filter((item) => item.comparisonId !== result.comparisonId)]);
      setNotice("Comparison stored from the two completed simulation runs.");
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(""); }
  };

  const runSowingAlternative = async () => {
    if (!a || !snapshotId || !sowingDate || busy) return;
    setBusy("Creating the sowing-date branch and submitting it to the simulation engine…");
    setError("");
    setNotice("");
    try {
      const crop = plots.find((plot) => plot.id === plotId)?.label || "";
      const branch = await apiClient.createBranch(farmId, plotId, {
        plotId, environmentalSnapshotId: snapshotId, effectiveDate: sowingDate,
        decisionType: "planting_date", decisionDiff: { plantingDate: sowingDate }, parentBranchId: a,
      });
      const queued = await apiClient.submitSimulation({
        farmId, plotId, environmentalSnapshotId: snapshotId, branchId: branch.branchId,
        irrigationMode: "rainfed", turmericMapping: crop.toLowerCase().includes("turmeric") ? "B" : undefined,
      });
      let run = queued as Simulation;
      for (let attempt = 0; attempt < 12 && run.status !== "completed" && run.status !== "failed"; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        run = await apiClient.getSimulation(queued.simulationRunId);
      }
      if (run.status !== "completed") {
        setError(run.errorMessage || "The alternative simulation did not complete. The stored comparison is unchanged.");
        setReloadKey((value) => value + 1);
        return;
      }
      if (runA) {
        const result = await apiClient.createComparison(farmId, plotId, {
          baselineBranchId: a, alternativeBranchId: branch.branchId,
          baselineRunId: runA.simulationRunId, alternativeRunId: run.simulationRunId,
          forkDate: comparisonFork.toISOString().slice(0, 10),
        });
        setNotice("Alternative sowing date was simulated and compared against the baseline.");
        setB(branch.branchId);
        setComparisons((current) => [result, ...current]);
      }
      setReloadKey((value) => value + 1);
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(""); }
  };

  const saveDecision = async () => {
    if (!latest || !snapshotId || busy) return;
    setBusy("Saving the approved decision…");
    setError("");
    try {
      await apiClient.createBranch(farmId, plotId, {
        plotId, environmentalSnapshotId: snapshotId, effectiveDate: today(),
        decisionType: "approved_decision", parentBranchId: side === "alternative" ? b : a,
        decisionDiff: {
          comparisonId: latest.comparisonId, objective, chosenSide: side,
          baselineBranchId: latest.baselineBranchId, alternativeBranchId: latest.alternativeBranchId,
          baselineRunId: latest.baselineRunId, alternativeRunId: latest.alternativeRunId,
        },
      });
      setNotice("Approved decision saved to the farm timeline.");
      setReloadKey((value) => value + 1);
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(""); }
  };

  const openField = () => {
    if (onOpenLivingField) onOpenLivingField(side);
    else navigate(scenePath(farmId, plotId, "observatory") + "?date=" + encodeURIComponent(date) + "&side=" + side);
  };
  const diffText = (value: { diff: number; percent: number | null; unit: string }) =>
    (value.diff > 0 ? "+" : "") + value.diff.toLocaleString(undefined, { maximumFractionDigits: 2 }) + " " + value.unit
    + (value.percent == null ? "" : " (" + (value.percent > 0 ? "+" : "") + value.percent.toFixed(1) + "%)");

  return <PageContainer>
    <div className="page-intro"><p className="eyebrow">Future Fold</p><h2>Compare two futures for this plot</h2>
      <p>{live ? "Turmeric uses the FAO-56 engine. Both futures share one retrieved weather snapshot. Only the sowing date changes." : "This crop cannot run a farm-scale simulation in the current science library."}</p></div>
    {blocked && <ErrorState label="Farm-scale simulation is not available. Maize has no verified farm profile, and wheat is limited to the published Tunis example. Stored demonstration records are not shown as live results." />}
    {live && <button className="primary-button" type="button" disabled={Boolean(busy)} onClick={runBaseline}>Prepare evidence and run FAO-56 baseline</button>}
    {error && <ErrorState label={error} />}
    {notice && <p role="status">{notice}</p>}
    {busy && <LoadingState label={busy} />}
    {!branches.length && !error && <EmptyState title="No decision branches yet" description="This plot has no stored baseline. Prepare environmental evidence and run a simulation before comparing futures." />}
    <div className="fold-grid">
      <ReusableCard><h3>Baseline</h3>
        <label>Branch<select aria-label="Baseline branch" value={a} onChange={(event) => setA(event.target.value)}>
          <option value="">Select baseline</option>{branches.map((branch) => <option key={branch.branchId} value={branch.branchId}>{branch.decisionType.replaceAll("_", " ")} · {branch.effectiveDate}</option>)}
        </select></label>
        <p>{original ? original.decisionType.replaceAll("_", " ") + " · " + original.effectiveDate : "No baseline selected."}</p>
        <p>{runA ? "Completed run " + runA.simulationRunId.slice(0, 8) + " · " + (runA.engine || "engine") : "No completed baseline run."}</p>
        <p>{decisionText(original?.decisionDiff)}</p>
      </ReusableCard>
      <ReusableCard><h3>Alternative</h3>
        <label>Branch<select aria-label="Alternative branch" value={b} onChange={(event) => setB(event.target.value)}>
          <option value="">Select alternative</option>{branches.filter((branch) => branch.branchId !== a).map((branch) => <option key={branch.branchId} value={branch.branchId}>{branch.decisionType.replaceAll("_", " ")} · {branch.effectiveDate}</option>)}
        </select></label>
        <p>{alternative ? alternative.decisionType.replaceAll("_", " ") + " · " + alternative.effectiveDate : "No alternative selected."}</p>
        <p>{runB ? "Completed run " + runB.simulationRunId.slice(0, 8) + " · " + (runB.engine || "engine") : "No completed alternative run."}</p>
        <p>{decisionText(alternative?.decisionDiff)}</p>
        <label>New sowing date<input type="date" value={sowingDate} onChange={(event) => setSowingDate(event.target.value)} /></label>
        <button className="secondary-button" type="button" disabled={!a || !snapshotId || !sowingDate || Boolean(busy)} onClick={runSowingAlternative}>Simulate this sowing date</button>
        <p>The engine applies a sowing-date change on the same weather snapshot. An irrigation ledger is required before a new irrigation depth can be simulated.</p>
      </ReusableCard>
    </div>
    <div className="toolbar">
      <label>Absolute date<input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>
      <button className="primary-button" type="button" disabled={!live || !runA || !runB || a === b || Boolean(busy)} onClick={submit}>{busy ? "Working…" : "Run comparison"}</button>
    </div>
    {live && latest ? <section className="fold-results">
      <h3>Stored comparison · {latest.status}</h3>
      {latest.reasons.map((reason) => <p key={reason}>{reason}</p>)}
      {!rows.length && <p>The comparison record has no daily metrics to chart.</p>}
      <div className="fold-grid">
        {rows.map((row) => {
          const scale = Math.max(Math.abs(row.a), Math.abs(row.b), 0.001);
          return <ReusableCard key={row.name}><h3>{metricLabels[row.name] || row.name}</h3>
            <p>Baseline {row.a.toLocaleString(undefined, { maximumFractionDigits: 2 })} {row.unit}</p>
            <p>Alternative {row.b.toLocaleString(undefined, { maximumFractionDigits: 2 })} {row.unit}</p>
            <div className="fold-bars" aria-hidden="true">
              <i className="a" style={{ width: Math.max(4, Math.abs(row.a) / scale * 100) + "%" }} />
              <i className="b" style={{ width: Math.max(4, Math.abs(row.b) / scale * 100) + "%" }} />
            </div>
            <p>Difference {diffText(row)}. {row.directed ? (row.lower ? "Lower is the advantage. " : "Higher is the advantage. ") + row.winner + "." : "No advantage is assigned for this metric."}</p>
          </ReusableCard>;
        })}
      </div>
      <div className="toolbar" role="group" aria-label="Decision objective">
        <button type="button" aria-pressed={objective === "water"} onClick={() => setObjective("water")}>Conserve water</button>
        <button type="button" aria-pressed={objective === "balance"} onClick={() => setObjective("balance")}>Review both</button>
      </div>
      <ReusableCard><h3>What this means</h3><p>{reading}</p>
        <p>Viewing the {side === "alternative" ? "alternative" : "baseline"} future. Switch it in the field below, then save that choice.</p>
      </ReusableCard>
    </section> : runA && runB ? <p>Both runs are complete. Run comparison to store the difference.</p> : null}
    <LivingFieldScene plots={plots} plotId={plotId} date={date} side={side} onChangeSide={setSide}
      onSelectPlot={(id) => navigate(scenePath(farmId, id, "future-fold") + "?date=" + encodeURIComponent(date))}
      original={branchScenario("original", original, originalState)} alternative={branchScenario("alternative", alternative, alternativeState)} />
    <div className="form-actions">
      <button className="primary-button" type="button" onClick={openField}>View this future in Living Field</button>
      <button className="secondary-button" type="button" disabled={!latest || !snapshotId || Boolean(busy)} onClick={saveDecision}>Save approved decision</button>
      <button className="secondary-button" type="button" onClick={() => navigate(`/dashboard?tab=timeline`)}>Saved decisions</button>
    </div>
  </PageContainer>;
}
