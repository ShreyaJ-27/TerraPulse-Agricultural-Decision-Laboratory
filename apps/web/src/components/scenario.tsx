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

export function FutureFold({ farmId, plotId, navigate }: PlotWorkspace) {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [runs, setRuns] = useState<Simulation[]>([]);
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [dateOverride, setDate] = useState(() => new window.URLSearchParams(window.location.search).get("date") || "");
  const [side, setSide] = useState<FieldSide>("original");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const plots = useFarmPlots(farmId, plotId);

  useEffect(() => {
    let current = true;
    Promise.allSettled([
      apiClient.listBranches(farmId, plotId), apiClient.listSimulations(farmId, plotId), apiClient.listComparisons(farmId, plotId),
    ]).then(([branchList, simulationList, comparisonList]) => {
      if (!current) return;
      const stored = comparisonList.status === "fulfilled" ? comparisonList.value.comparisons : [];
      const choices = branchList.status === "fulfilled" ? branchList.value.branches : [];
      const params = new window.URLSearchParams(window.location.search);
      const choose = (key: string, fallback?: string) => {
        const requested = params.get(key);
        return choices.find((branch) => branch.branchId === requested)?.branchId || fallback || "";
      };
      setBranches(choices);
      setRuns(simulationList.status === "fulfilled" ? simulationList.value.simulations : []);
      setComparisons(stored);
      setA(choose("baselineBranchId", stored[0]?.baselineBranchId));
      setB(choose("alternativeBranchId", stored[0]?.alternativeBranchId));
      if ([branchList, simulationList, comparisonList].some((result) => result.status === "rejected")) {
        setError("Some stored comparisons or branches could not be loaded.");
      }
    });
    return () => { current = false; };
  }, [farmId, plotId]);

  const original = branches.find((branch) => branch.branchId === a);
  const alternative = branches.find((branch) => branch.branchId === b);
  const runA = runs.find((run) => run.branchId === a && run.status === "completed");
  const runB = runs.find((run) => run.branchId === b && run.status === "completed");
  const latest = comparisons.find((item) => item.baselineBranchId === a && item.alternativeBranchId === b);
  const daily = latest?.payload.result?.daily || [];
  const date = dateOverride || daily[0]?.date || original?.effectiveDate || today();
  const originalState = useFieldState(farmId, plotId, a, date, latest?.baselineRunId ?? runA?.simulationRunId);
  const alternativeState = useFieldState(farmId, plotId, b, date, latest?.alternativeRunId ?? runB?.simulationRunId);
  const day = daily.find((row) => row.date === date);

  const submit = async () => {
    if (!runA || !runB || a === b || busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await apiClient.createComparison(farmId, plotId, {
        baselineBranchId: a, alternativeBranchId: b, baselineRunId: runA.simulationRunId, alternativeRunId: runB.simulationRunId,
      });
      setComparisons((current) => [result, ...current]);
      setDate("");
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  };

  return <PageContainer>
    <div className="page-intro"><p className="eyebrow">Future Fold</p><h2>Compare independent scenarios</h2>
      <p>Compare original and alternative decisions at the same plot and date. Numerical comparisons require two completed runs with matched inputs.</p></div>
    {error && <ErrorState label={error} />}
    <div className="toolbar">
      <label>Baseline branch<select value={a} onChange={(event) => setA(event.target.value)}>
        <option value="">Select branch</option>{branches.map((branch) => <option key={branch.branchId} value={branch.branchId}>{branch.decisionType} · {branch.branchId.slice(0, 8)}</option>)}
      </select></label>
      <label>Alternative branch<select value={b} onChange={(event) => setB(event.target.value)}>
        <option value="">Select branch</option>{branches.map((branch) => <option key={branch.branchId} value={branch.branchId}>{branch.decisionType} · {branch.branchId.slice(0, 8)}</option>)}
      </select></label>
      <label>Absolute date<input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>
      <button className="primary-button" disabled={!runA || !runB || a === b || busy} onClick={submit}>{busy ? "Comparing…" : "Submit comparison"}</button>
    </div>
    <LivingFieldScene plots={plots} plotId={plotId} date={date} side={side} onChangeSide={setSide}
      onSelectPlot={(id) => navigate(scenePath(farmId, id, "future-fold") + "?date=" + encodeURIComponent(date))}
      original={branchScenario("original", original, originalState)} alternative={branchScenario("alternative", alternative, alternativeState)} />
    <div className="form-actions">
      <button className="secondary-button" onClick={() => navigate(scenePath(farmId, plotId, "observatory") + "?date=" + encodeURIComponent(date))}>Open Living Field</button>
      <button className="secondary-button" onClick={() => navigate(`/farms/${farmId}/plots/${plotId}/timeline`)}>Saved decisions</button>
    </div>
    {latest && <ReusableCard><h3>{latest.status === "comparable" ? "Comparable result" : "Not comparable"}</h3>
      {latest.reasons.map((reason) => <p className="warning" key={reason}>{reason}</p>)}
      {day ? <div className="comparison-row"><strong>{day.date}</strong>{day.metrics.map((metric) =>
        <span key={metric.name}>{metric.name}: {metric.branchA} → {metric.branchB} ({metric.differenceBMinusA} {metric.unit})</span>)}</div>
        : latest.status === "comparable" && <p>No comparison values for this date.</p>}
      <p>Baseline run {latest.baselineRunId} · alternative run {latest.alternativeRunId}</p>
    </ReusableCard>}
  </PageContainer>;
}
