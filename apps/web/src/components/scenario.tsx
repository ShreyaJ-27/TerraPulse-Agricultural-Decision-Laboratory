import { useCallback, useEffect, useState } from "react";
import { Branch, Comparison, Farm, ScientificState, Simulation, TimelineEvent, apiClient } from "../services/apiClient";
import { EmptyState, ErrorState, LoadingState, PageContainer, ReusableCard } from "./ui";

const errorMessage = (error: unknown) => error instanceof Error ? error.message : "The request failed.";

function PlotField({ plotId, state, reduced }: { plotId: string; state?: ScientificState; reduced: boolean }) {
  const raw = state?.state || {};
  const metrics = (raw as { metrics?: Record<string, { value?: number; status?: string }> }).metrics || {};
  const stress = metrics.waterStressKs?.status === "available" ? metrics.waterStressKs.value : undefined;
  const color = stress === undefined ? "field-unknown" : stress < 0.5 ? "field-stressed" : "field-healthy";
  return <section className={`living-field ${reduced ? "reduced" : ""}`} aria-label="Living Field visual state">
    <div className="field-grid"><div className={`field-plot ${color}`}><span>Plot {plotId.slice(0, 8)}</span><small>{state ? state.date : "No scientific state"}</small></div></div>
    <p className="field-caption">{state ? "Illustrative visual layer; scientific values remain unchanged." : "Unavailable measurements are not rendered as fabricated indicators."}</p>
  </section>;
}

export function Observatory({ farmId, plotId }: { farmId: string; plotId: string }) {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [branchId, setBranchId] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [state, setState] = useState<ScientificState>();
  const [reduced, setReduced] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { apiClient.listBranches(farmId, plotId).then((value) => { setBranches(value.branches); setBranchId(value.branches[0]?.branchId || ""); }).catch((e) => setError(errorMessage(e))); }, [farmId, plotId]);
  useEffect(() => { if (!branchId) return; setState(undefined); apiClient.getScientificState(farmId, plotId, branchId, date).then(setState).catch((e) => { setState(undefined); setError(errorMessage(e)); }); }, [farmId, plotId, branchId, date]);
  if (error && branches.length === 0) return <PageContainer><ErrorState label={error} /></PageContainer>;
  return <PageContainer><div className="page-intro"><p className="eyebrow">Living Field · Plot {plotId.slice(0, 8)}</p><h2>Scientific state observatory</h2><p>Select an immutable branch and absolute date. The visual layer never writes interpolated values to the API.</p></div>
    <div className="toolbar"><label>Branch<select value={branchId} onChange={(e) => setBranchId(e.target.value)}>{branches.map((branch) => <option key={branch.branchId} value={branch.branchId}>{branch.decisionType} · {branch.branchId.slice(0, 8)}</option>)}</select></label><label>Absolute date<input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label><label className="checkbox"><input type="checkbox" checked={reduced} onChange={(e) => setReduced(e.target.checked)} /> Reduced quality</label></div>
    {error && <ErrorState label={error} />}<PlotField plotId={plotId} state={state} reduced={reduced}/>{state && <ReusableCard><h3>Authoritative provenance</h3><p>{state.provenance.engine} {state.provenance.engineVersion} · {state.provenance.parameterVersion || "parameter version unavailable"}</p><p>Run {state.simulationRunId} · snapshot {state.provenance.environmentalSnapshotId}</p><p>{state.provenance.visualInterpolation.label} Values mutated: {String(state.provenance.visualInterpolation.scientificValuesMutated)}.</p></ReusableCard>}</PageContainer>;
}

export function Timeline({ farmId, plotId }: { farmId: string; plotId: string }) {
  const [events, setEvents] = useState<TimelineEvent[]>([]); const [branches, setBranches] = useState<Branch[]>([]); const [farm, setFarm] = useState<Farm>(); const [error, setError] = useState(""); const [snapshotId, setSnapshotId] = useState(""); const [parent, setParent] = useState(""); const [decision, setDecision] = useState("planting_date"); const [plantingDate, setPlantingDate] = useState("");
  const load = useCallback(() => Promise.all([apiClient.getTimeline(farmId, plotId), apiClient.listBranches(farmId, plotId)]).then(([timeline, branchList]) => { setEvents(timeline.events); setBranches(branchList.branches); }).catch((e) => setError(errorMessage(e))), [farmId, plotId]);
  useEffect(() => { apiClient.getFarm(farmId).then(setFarm).catch((e) => setError(errorMessage(e))); void load(); }, [farmId, load]);
  const create = async () => { if (!snapshotId || !plantingDate) { setError("A persisted environmental snapshot and effective date are required."); return; } try { await apiClient.createBranch(farmId, plotId, { plotId, environmentalSnapshotId: snapshotId, effectiveDate: plantingDate, decisionType: decision, parentBranchId: parent || null, decisionDiff: decision === "planting_date" ? { plantingDate } : { ledger: { ledgerHash: snapshotId } } }); setError(""); await load(); } catch (e) { setError(errorMessage(e)); } };
  if (!farm) return <PageContainer><LoadingState label="Loading farm timeline…" /></PageContainer>;
  return <PageContainer><div className="page-intro"><p className="eyebrow">Decision history</p><h2>{farm.name} timeline</h2><p>Every event is persisted. Reopening a branch never edits its record.</p></div>{error && <ErrorState label={error} />}<section className="form-panel"><h3>Create immutable child branch</h3><label>Environmental snapshot ID<input value={snapshotId} onChange={(e) => setSnapshotId(e.target.value)} placeholder="UUID from prepared evidence" /></label><label>Parent branch<select value={parent} onChange={(e) => setParent(e.target.value)}><option value="">Create baseline</option>{branches.map((branch) => <option key={branch.branchId} value={branch.branchId}>{branch.decisionType} · {branch.branchId.slice(0, 8)}</option>)}</select></label><label>Decision<select value={decision} onChange={(e) => setDecision(e.target.value)}><option value="planting_date">Planting date</option><option value="irrigation">Irrigation ledger</option></select></label><label>Effective date<input type="date" value={plantingDate} onChange={(e) => setPlantingDate(e.target.value)} /></label><button className="primary-button" onClick={create}>Create child branch</button></section><section className="timeline">{events.length === 0 ? <EmptyState title="No timeline events" description="Create a baseline or submit a simulation to begin history." /> : events.map((event) => <article className="timeline-event" key={event.eventId}><time>{event.eventDate}</time><div><strong>{event.description}</strong><small>{event.eventType} · {event.branchId || "farm"}</small></div></article>)}</section></PageContainer>;
}

export function FutureFold({ farmId, plotId }: { farmId: string; plotId: string }) {
  const [branches, setBranches] = useState<Branch[]>([]); const [runs, setRuns] = useState<Simulation[]>([]); const [comparisons, setComparisons] = useState<Comparison[]>([]); const [a, setA] = useState(""); const [b, setB] = useState(""); const [error, setError] = useState("");
  useEffect(() => { Promise.all([apiClient.listBranches(farmId, plotId), apiClient.listSimulations(farmId, plotId), apiClient.listComparisons(farmId, plotId)]).then(([branchList, simulationList, comparisonList]) => { setBranches(branchList.branches); setRuns(simulationList.simulations); setComparisons(comparisonList.comparisons); }).catch((e) => setError(errorMessage(e))); }, [farmId, plotId]);
  const runFor = (branchId: string) => runs.find((run) => run.branchId === branchId);
  const submit = async () => { const runA = runFor(a); const runB = runFor(b); if (!runA || !runB) { setError("Both branches need independently completed simulation runs."); return; } try { const result = await apiClient.createComparison(farmId, plotId, { baselineBranchId: a, alternativeBranchId: b, baselineRunId: runA.simulationRunId, alternativeRunId: runB.simulationRunId }); setComparisons([result, ...comparisons]); setError(""); } catch (e) { setError(errorMessage(e)); } };
  const latest = comparisons[0]; const daily = latest?.payload.result?.daily || [];
  return <PageContainer><div className="page-intro"><p className="eyebrow">Future Fold</p><h2>Compare independent scenarios</h2><p>Only completed runs with matched scientific inputs are eligible. Unsupported metrics remain unavailable.</p></div>{error && <ErrorState label={error} />}<div className="toolbar"><label>Baseline branch<select value={a} onChange={(e) => setA(e.target.value)}><option value="">Select branch</option>{branches.map((branch) => <option key={branch.branchId} value={branch.branchId}>{branch.decisionType} · {branch.branchId.slice(0, 8)}</option>)}</select></label><label>Alternative branch<select value={b} onChange={(e) => setB(e.target.value)}><option value="">Select branch</option>{branches.map((branch) => <option key={branch.branchId} value={branch.branchId}>{branch.decisionType} · {branch.branchId.slice(0, 8)}</option>)}</select></label><button className="primary-button" onClick={submit}>Submit comparison</button></div>{latest && <ReusableCard><h3>{latest.status === "comparable" ? "Comparable result" : "Not comparable"}</h3>{latest.reasons.map((reason) => <p className="warning" key={reason}>{reason}</p>)}{daily.map((day) => <div className="comparison-row" key={day.date}><strong>{day.date}</strong>{day.metrics.map((metric) => <span key={metric.name}>{metric.name}: {metric.branchA} → {metric.branchB} ({metric.differenceBMinusA} {metric.unit})</span>)}</div>)}<p>Provenance is retained for baseline and alternative runs.</p></ReusableCard>}</PageContainer>;
}
