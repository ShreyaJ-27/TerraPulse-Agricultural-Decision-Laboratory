import { useCallback, useEffect, useState } from "react";
import { Branch, Comparison, Farm, Simulation, TimelineEvent, apiClient } from "../services/apiClient";
import { LivingFieldScene } from "./living-field/LivingFieldScene";
import { branchScenario, scenePath, today, useFarmPlots, useFieldState } from "./living-field/fieldState";
import type { FieldScenario, FieldSide } from "./living-field/LivingFieldScene";
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
    <div className="workspace-links">
      <button type="button" className="secondary-button" onClick={() => navigate(`/farms/${farmId}/plots/${plotId}/environment`)}>Environmental Evidence</button>
      <button type="button" className="secondary-button" onClick={() => navigate(scenePath(farmId, plotId, "future-fold") + dateQuery)}>Open Future Fold</button>
      <button type="button" className="secondary-button" onClick={() => navigate(`/farms/${farmId}`)}>Farm Workspace</button>
    </div>
  </PageContainer>;
}

export function Timeline({ farmId, plotId, navigate }: PlotWorkspace) {
  const query = new URLSearchParams(window.location.search);
  const [events, setEvents] = useState<TimelineEvent[]>();
  const [branches, setBranches] = useState<Branch[]>([]);
  const [farm, setFarm] = useState<Farm>();
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [snapshotId, setSnapshotId] = useState(query.get("snapshot") || "");
  const [parent, setParent] = useState("");
  const [decision, setDecision] = useState("planting_date");
  const [plantingDate, setPlantingDate] = useState(query.get("date") || "");
  const [busy, setBusy] = useState(false);
  const [ledgerHash, setLedgerHash] = useState("");
  const plotPath = `/farms/${farmId}/plots/${plotId}`;

  const load = useCallback(async () => {
    const [timeline, branchList, runList] = await Promise.allSettled([
      apiClient.getTimeline(farmId, plotId),
      apiClient.listBranches(farmId, plotId),
      apiClient.listSimulations(farmId, plotId),
    ]);
    if (timeline.status === "fulfilled") setEvents(timeline.value.events);
    if (branchList.status === "fulfilled") setBranches(branchList.value.branches);
    if (runList.status === "fulfilled") {
      const completed = runList.value.simulations.find((run) => run.status === "completed" && run.environmentalSnapshotId);
      if (completed?.environmentalSnapshotId) setSnapshotId((current) => current || completed.environmentalSnapshotId || "");
    }
    if (timeline.status === "rejected" || branchList.status === "rejected") setError("Saved decisions could not be fully loaded.");
  }, [farmId, plotId]);

  useEffect(() => {
    let active = true;
    apiClient.getFarm(farmId).then((result) => {
      if (active) setFarm(result);
    }).catch((reason) => { if (active) setError(errorMessage(reason)); });
    void load();
    return () => { active = false; };
  }, [farmId, load]);

  async function create() {
    if (!snapshotId || !plantingDate || busy || (decision === "irrigation" && !ledgerHash.trim())) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await apiClient.createBranch(farmId, plotId, {
        plotId, environmentalSnapshotId: snapshotId, effectiveDate: plantingDate, decisionType: decision,
        parentBranchId: parent || null,
        decisionDiff: decision === "planting_date" ? { plantingDate } : { ledger: { ledgerHash: ledgerHash.trim() } },
      });
      setNotice("Decision saved to this plot’s timeline.");
      await load();
    } catch (reason) { setError(errorMessage(reason)); }
    finally { setBusy(false); }
  }
  const plot = farm?.plots.find((item) => item.plotId === plotId);
  if (!farm) return <PageContainer>{error ? <ErrorState label={error} /> : <LoadingState label="Loading farm timeline…" />}</PageContainer>;
  if (!plot) return <PageContainer><ErrorState label="Plot was not found under this farm." /></PageContainer>;

  return <PageContainer>
    <div className="page-intro"><p className="eyebrow">Saved decisions</p>
      <h2>{plot.management?.plotName || plot.cropCanonicalName} timeline</h2><p>{farm.name}</p>
    </div>
    {error && <ErrorState label={error} />}
    {notice && <p role="status">{notice}</p>}
    <form className="form-panel" onSubmit={(event) => { event.preventDefault(); void create(); }}>
      <h3>Save a decision</h3>
      {snapshotId ? <p>Environmental snapshot · {snapshotId.slice(0, 8)}</p>
        : <p>Prepare environmental evidence to attach a snapshot to the decision.</p>}
      <button type="button" className="secondary-button" onClick={() => navigate(plotPath + "/environment")}>
        {snapshotId ? "Review environmental evidence" : "Prepare environmental evidence"}
      </button>
      <label>Parent branch<select value={parent} onChange={(event) => setParent(event.target.value)}>
        <option value="">Start a new branch</option>{branches.map((branch) => <option key={branch.branchId} value={branch.branchId}>
          {branch.decisionType.replaceAll("_", " ")} · {branch.effectiveDate} · {branch.branchId.slice(0, 6)}
        </option>)}
      </select></label>
      <label>Decision<select value={decision} onChange={(event) => setDecision(event.target.value)}>
        <option value="planting_date">Planting date</option><option value="irrigation">Irrigation ledger</option>
      </select></label>
      {decision === "irrigation" && <label>Saved water ledger hash<input required value={ledgerHash} onChange={(event) => setLedgerHash(event.target.value)} /></label>}
      <label>Effective date<input required type="date" value={plantingDate} onChange={(event) => setPlantingDate(event.target.value)} /></label>
      <button className="primary-button" disabled={busy || !snapshotId || !plantingDate}>{busy ? "Saving…" : "Save decision"}</button>
    </form>
    <section className="timeline">
      {!events && !error && <LoadingState label="Loading timeline events…" />}
      {events?.length === 0 && <EmptyState title="No timeline events" description="Save a decision or submit a simulation to begin history." />}
      {events?.map((event) => <article className="timeline-event" key={event.eventId}>
        <time dateTime={event.eventDate}>{event.eventDate}</time>
        <div><strong>{event.description}</strong><small>{event.eventType.replaceAll("_", " ")}</small>
          {event.branchId && <button className="secondary-button" onClick={() => navigate(scenePath(farmId, plotId, "observatory") + "?"
            + new URLSearchParams({ branch: event.branchId!, date: event.eventDate }))}>View branch in Living Field</button>}
        </div>
      </article>)}
    </section>
  </PageContainer>;
}

const lowerIsBetter = new Set(["waterstress", "irrigation", "wateruse", "soilwaterdepletion"]);

function metricRows(comparison?: Comparison) {
  const daily = comparison?.payload.result?.daily || [];
  const totals = new Map<string, { name: string; unit: string; a: number; b: number; n: number }>();
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
    const lower = lowerIsBetter.has(row.name.toLowerCase());
    const winner = a === b ? "Same" : (lower ? b < a : b > a) ? "Alternative" : "Baseline";
    return { name: row.name, unit: row.unit, a, b, diff: b - a, percent: a === 0 ? null : ((b - a) / Math.abs(a)) * 100, winner, lower };
  });
}

function readSummary(comparison?: Comparison) {
  const result = comparison?.payload.result as { summary?: Record<string, number> } | undefined;
  return result?.summary && typeof result.summary === "object" ? result.summary : undefined;
}

function interpret(rows: ReturnType<typeof metricRows>, objective: "canopy" | "water" | "balance") {
  const cover = rows.find((row) => row.name === "canopyCover");
  const stress = rows.find((row) => row.name === "waterStress");
  if (!cover && !stress) return "This comparison does not include enough outputs to choose a scenario.";
  const coverLine = cover ? (cover.winner === "Same" ? "Canopy cover is unchanged." : cover.winner + " has the higher average canopy cover.") : "Canopy cover was not returned.";
  const stressLine = stress ? (stress.winner === "Same" ? "Water stress is unchanged." : (stress.winner === "Alternative" ? "Alternative" : "Baseline") + " has the lower average water stress.") : "Water stress was not returned.";
  const yieldNote = " Predicted yield and biomass are not in this stored comparison, so they are not used to pick a winner.";
  if (objective === "canopy") return coverLine + yieldNote;
  if (objective === "water") return stressLine + yieldNote;
  if (cover && stress && cover.winner !== "Same" && stress.winner !== "Same" && cover.winner !== stress.winner) {
    return coverLine + " " + stressLine + " That is a trade-off: one future grows a fuller canopy while the other keeps water stress lower. No single winner is supported." + yieldNote;
  }
  return coverLine + " " + stressLine + yieldNote;
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
  const hasComparison = Boolean(pair.alternative);
  const originalState = useFieldState(farmId, plotId, pair.original?.branchId || "", pair.date, pair.runA);
  const alternativeState = useFieldState(farmId, plotId, pair.alternative?.branchId || "", pair.date, pair.runB);
  return <>
    <LivingFieldScene plots={plots} plotId={plotId} date={pair.date} side={side} onChangeSide={onChangeSide} onSelectPlot={onSelectPlot}
      original={branchScenario("original", pair.original, originalState)}
      alternative={hasComparison ? branchScenario("alternative", pair.alternative, alternativeState) : undefined} />
    <p className="subtitle">{originalState.state || alternativeState.state
      ? `Stored model outputs for ${pair.date}.`
      : "Illustrative field view. Model outputs appear when a stored result is available."}</p>
  </>;
}

function SowingExample({ onOpenField }: { onOpenField: (side: FieldSide) => void }) {
  const [delay, setDelay] = useState("7");
  const [objective, setObjective] = useState("field");
  const [side, setSide] = useState<FieldSide>("original");
  const base = "2026-07-01";
  const alternative = new Date(Date.parse(base) + Number(delay) * 86_400_000).toISOString().slice(0, 10);
  return <section className="form-panel sowing-example">
    <p className="eyebrow">Illustrative scenario</p>
    <h3>Compare sowing schedules</h3>
    <p>Assume the field is available on July 1 and that waiting gives the operator more preparation time. This example compares dates only.</p>
    <div className="form-actions">
      <label>Delay sowing<select value={delay} onChange={(event) => setDelay(event.target.value)}>
        <option value="3">3 days</option><option value="7">7 days</option><option value="14">14 days</option>
      </select></label>
      <label>Priority<select value={objective} onChange={(event) => setObjective(event.target.value)}>
        <option value="field">Sow earlier</option><option value="prep">Allow more preparation time</option>
      </select></label>
    </div>
    <div className="toolbar" role="group" aria-label="Example schedule">
      <button type="button" aria-pressed={side === "original"} onClick={() => setSide("original")}>Baseline · {base}</button>
      <button type="button" aria-pressed={side === "alternative"} onClick={() => setSide("alternative")}>Alternative · {alternative}</button>
    </div>
    <p role="status">{objective === "field" ? "The baseline starts first." : `The alternative allows ${delay} more days of preparation.`}</p>
    <button className="secondary-button" onClick={() => onOpenField(side)}>View selected layout</button>
  </section>;
}

const sowingExampleSide: FieldScenario = {
  side: "alternative", label: "Example sowing alternative",
  description: "Illustrative field layout for a later sowing decision.",
};

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
  const [objective, setObjective] = useState<"canopy" | "water" | "balance">("balance");
  const [sowingDate, setSowingDate] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [loading, setLoading] = useState(true);
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
      setA((selected) => choices.some((branch) => branch.branchId === selected) ? selected : baseline?.branchId || "");
      setB((selected) => choices.some((branch) => branch.branchId === selected) ? selected : alternative?.branchId || "");
      setError(failures.join(" "));
      setLoading(false);
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

  const rows = metricRows(latest);
  const summary = readSummary(latest);
  const reading = interpret(rows, objective);
  const snapshotId = runA?.environmentalSnapshotId || "";
  const chooseExampleSide = (nextSide: FieldSide) => {
    setSide(nextSide);
    document.getElementById("future-field")?.scrollIntoView({ block: "start" });
  };

  const submit = async () => {
    if (!runA || !runB || a === b || busy) return;
    setBusy("Comparing the two completed runs…");
    setError("");
    setNotice("");
    try {
      const result = await apiClient.createComparison(farmId, plotId, {
        baselineBranchId: a, alternativeBranchId: b, baselineRunId: runA.simulationRunId, alternativeRunId: runB.simulationRunId,
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
    if (!latest || !latest.matchedInputs || !rows.length || !snapshotId || busy) return;
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
    else {
      const params = new URLSearchParams({ date });
      const branch = side === "alternative" ? b : a;
      if (branch) params.set("branch", branch);
      navigate(scenePath(farmId, plotId, "observatory") + "?" + params);
    }
  };
  const diffText = (value: { diff: number; percent: number | null; unit: string }) =>
    (value.diff > 0 ? "+" : "") + value.diff.toLocaleString(undefined, { maximumFractionDigits: 2 }) + " " + value.unit
    + (value.percent == null ? "" : " (" + (value.percent > 0 ? "+" : "") + value.percent.toFixed(1) + "%)");

  return <PageContainer>
    <div className="page-intro"><p className="eyebrow">Future Fold</p><h2>Compare two futures for this plot</h2>
      <p>Compare completed model runs or explore the example sowing schedules while farm results are pending.</p></div>
    {error && <ErrorState label={error} />}
    {notice && <p role="status">{notice}</p>}
    {busy && <LoadingState label={busy} />}
    {loading && <LoadingState label="Loading farm scenarios…" />}
    {!loading && !latest && <SowingExample onOpenField={chooseExampleSide} />}
    {!loading && !branches.length && !error && <EmptyState title="No decision branches yet"
      description="Prepare environmental evidence and complete a baseline run to compare model outputs."
      action={<button className="secondary-button" onClick={() => navigate(scenePath(farmId, plotId, "observatory").replace(/observatory$/, "environment"))}>Prepare evidence</button>} />}
    <div className="fold-grid">
      <ReusableCard><h3>Baseline</h3>
        <label>Branch<select aria-label="Baseline branch" value={a} onChange={(event) => setA(event.target.value)}>
          <option value="">Select baseline</option>{branches.map((branch) => <option key={branch.branchId} value={branch.branchId}>{branch.decisionType.replaceAll("_", " ")} · {branch.effectiveDate}</option>)}
        </select></label>
        <p>{original ? original.decisionType.replaceAll("_", " ") + " · " + original.effectiveDate : "No baseline selected."}</p>
        <p>{runA ? "Completed run " + runA.simulationRunId.slice(0, 8) + " · " + (runA.engine || "engine") : "No completed baseline run."}</p>
        {original && Object.keys(original.decisionDiff || {}).length > 0 && <details>
          <summary>Decision inputs</summary><pre className="fold-diff">{JSON.stringify(original.decisionDiff, null, 2)}</pre>
        </details>}
      </ReusableCard>
      <ReusableCard><h3>Alternative</h3>
        <label>Branch<select aria-label="Alternative branch" value={b} onChange={(event) => setB(event.target.value)}>
          <option value="">Select alternative</option>{branches.filter((branch) => branch.branchId !== a).map((branch) => <option key={branch.branchId} value={branch.branchId}>{branch.decisionType.replaceAll("_", " ")} · {branch.effectiveDate}</option>)}
        </select></label>
        <p>{alternative ? alternative.decisionType.replaceAll("_", " ") + " · " + alternative.effectiveDate : "No alternative selected."}</p>
        <p>{runB ? "Completed run " + runB.simulationRunId.slice(0, 8) + " · " + (runB.engine || "engine") : "No completed alternative run."}</p>
        {alternative && Object.keys(alternative.decisionDiff || {}).length > 0 && <details>
          <summary>Decision inputs</summary><pre className="fold-diff">{JSON.stringify(alternative.decisionDiff, null, 2)}</pre>
        </details>}
        <label>New sowing date<input type="date" value={sowingDate} onChange={(event) => setSowingDate(event.target.value)} /></label>
        <button className="secondary-button" type="button" disabled={!a || !snapshotId || !sowingDate || Boolean(busy)} onClick={runSowingAlternative}>Simulate this sowing date</button>
        <p>The engine applies a sowing-date change on the same weather snapshot. An irrigation ledger is required before a new irrigation depth can be simulated.</p>
      </ReusableCard>
    </div>
    <div className="toolbar">
      <label>Absolute date<input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>
      <button className="primary-button" type="button" disabled={!runA || !runB || a === b || Boolean(busy)} onClick={submit}>{busy ? "Working…" : "Run comparison"}</button>
    </div>
    {latest ? <section className="fold-results">
      <h3>Stored comparison · {latest.status}</h3>
      {latest.reasons.map((reason) => <p key={reason}>{reason}</p>)}
      {!rows.length && <p>The comparison record has no daily metrics to chart.</p>}
      <div className="fold-grid">
        {rows.map((row) => {
          const scale = Math.max(Math.abs(row.a), Math.abs(row.b), 0.001);
          return <ReusableCard key={row.name}><h3>{row.name}</h3>
            <p>Baseline {row.a.toLocaleString(undefined, { maximumFractionDigits: 2 })} {row.unit}</p>
            <p>Alternative {row.b.toLocaleString(undefined, { maximumFractionDigits: 2 })} {row.unit}</p>
            <div className="fold-bars" aria-hidden="true">
              <i className="a" style={{ width: Math.max(4, Math.abs(row.a) / scale * 100) + "%" }} />
              <i className="b" style={{ width: Math.max(4, Math.abs(row.b) / scale * 100) + "%" }} />
            </div>
            <p>Difference {diffText(row)}. {row.lower ? "Lower is the advantage." : "Higher is the advantage."} {row.winner}.</p>
          </ReusableCard>;
        })}
      </div>
      {summary && <ReusableCard><h3>Stored summary fields</h3>
        <p>These values are on the comparison record. They are not a second baseline-versus-alternative split.</p>
        {Object.entries(summary).map(([key, value]) => <p key={key}>{key}: {typeof value === "number" ? value.toLocaleString() : String(value)}</p>)}
      </ReusableCard>}
      <div className="toolbar" role="group" aria-label="Decision objective">
        <button type="button" aria-pressed={objective === "canopy"} onClick={() => setObjective("canopy")}>Maximize canopy</button>
        <button type="button" aria-pressed={objective === "water"} onClick={() => setObjective("water")}>Conserve water</button>
        <button type="button" aria-pressed={objective === "balance"} onClick={() => setObjective("balance")}>Balance both</button>
      </div>
      <ReusableCard><h3>What this means</h3><p>{reading}</p>
        <p>Viewing the {side === "alternative" ? "alternative" : "baseline"} future. Switch it in the field below, then save that choice.</p>
      </ReusableCard>
    </section> : runA && runB ? <p>Both runs are complete. Run comparison to store the difference.</p> : null}
    <div id="future-field">
      <LivingFieldScene plots={plots} plotId={plotId} date={date} side={side} onChangeSide={setSide}
        onSelectPlot={(id) => navigate(scenePath(farmId, id, "future-fold") + "?date=" + encodeURIComponent(date))}
        original={branchScenario("original", original, originalState)}
        alternative={alternative ? branchScenario("alternative", alternative, alternativeState) : !latest ? sowingExampleSide : undefined} />
    </div>
    <div className="form-actions">
      <button className="primary-button" type="button" onClick={openField}>View this future in Living Field</button>
      <button className="secondary-button" type="button" disabled={!latest?.matchedInputs || !rows.length || !snapshotId || Boolean(busy)} onClick={saveDecision}>Save approved decision</button>
      <button className="secondary-button" type="button" onClick={() => navigate(`/dashboard?${new URLSearchParams({ tab: "timeline", farmId, plotId })}`)}>Saved decisions</button>
    </div>
  </PageContainer>;
}
