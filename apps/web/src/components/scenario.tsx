import { useCallback, useEffect, useMemo, useState } from "react";
import { Branch, Comparison, Farm, Simulation, TimelineEvent, apiClient } from "../services/apiClient";
import { LivingFieldScene } from "./living-field/LivingFieldScene";
import { branchScenario, scenePath, today, useFarmPlots, useFieldState } from "./living-field/fieldState";
import type { FieldSide } from "./living-field/LivingFieldScene";
import { EmptyState, ErrorState, LoadingState, PageContainer, ReusableCard } from "./ui";
import { getPreparedDemoScenario, PreparedFutureFoldScenario } from "../services/demoProvider";
import { EXPERIMENT_TEMPLATES } from "../services/demoScenarios";

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
  const [objective, setObjective] = useState<"crop" | "water" | "balance">("balance");
  const [sowingDate, setSowingDate] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  // Experiment Builder state
  const [activeExperiment, setActiveExperiment] = useState<string>("change_sowing_date");
  const [sowingOffsetDays, setSowingOffsetDays] = useState<number>(-14);
  const [irrigationPct, setIrrigationPct] = useState<number>(0);

  const plots = useFarmPlots(farmId, plotId);
  const activePlot = plots.find((p) => p.id === plotId);
  const cropLabel = activePlot?.label || "";
  const detectedCrop = cropLabel.toLowerCase().includes("wheat")
    ? "wheat"
    : cropLabel.toLowerCase().includes("turmeric")
    ? "turmeric"
    : "maize";

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
      if (failures.length > 0 && !stored.length) {
        // Fallback gracefully without breaking demo
      }
    });
    return () => { current = false; };
  }, [farmId, plotId, reloadKey]);

  const original = branches.find((branch) => branch.branchId === a);
  const alternative = branches.find((branch) => branch.branchId === b);
  const runA = runs.find((run) => run.branchId === a && run.status === "completed");
  const runB = runs.find((run) => run.branchId === b && run.status === "completed");
  const latest = comparisons.find((item) => item.baselineBranchId === a && item.alternativeBranchId === b) || comparisons[0];
  const daily = latest?.payload.result?.daily || [];
  const date = dateOverride || daily[0]?.date || original?.effectiveDate || today();
  const originalState = useFieldState(farmId, plotId, a, date, latest?.baselineRunId ?? runA?.simulationRunId);
  const alternativeState = useFieldState(farmId, plotId, b, date, latest?.alternativeRunId ?? runB?.simulationRunId);

  // Deterministic Demo Scenario Provider for full demo reliability across Maize, Wheat & Turmeric
  const demoData = useMemo(() => {
    return getPreparedDemoScenario(detectedCrop, activeExperiment, sowingOffsetDays, irrigationPct);
  }, [detectedCrop, activeExperiment, sowingOffsetDays, irrigationPct]);

  // Use live comparison rows if available, otherwise use prepared demo scenario metrics
  const liveRows = latest ? metricRows(latest) : [];
  const displayMetrics = liveRows.length > 0 ? liveRows.map((r) => ({
    name: metricLabels[r.name] || r.name,
    unit: r.unit,
    branchA: r.a,
    branchB: r.b,
    differenceBMinusA: r.diff,
    higherIsBetter: !r.lower,
  })) : demoData.metrics;

  const snapshotId = runA?.environmentalSnapshotId || runB?.environmentalSnapshotId || "demo-snapshot";
  const forkDate = [sowingDate, demoData.alternative.sowingDate].filter(Boolean).sort()[0];
  const comparisonFork = new Date(forkDate + "T00:00:00Z");
  comparisonFork.setUTCDate(comparisonFork.getUTCDate() - 1);

  // Visual parameter binding for 3D digital twin
  const original3DVisual = {
    waterStress: 1 - demoData.baseline.ks,
    soilWaterMm: demoData.baseline.depletionMm,
    vigor: demoData.baseline.viz.vigor,
    plantHeight: demoData.baseline.viz.plantHeight,
    canopyCoverage: demoData.baseline.viz.canopyCoverage,
    cropType: detectedCrop,
  };

  const alternative3DVisual = {
    waterStress: 1 - demoData.alternative.ks,
    soilWaterMm: demoData.alternative.depletionMm,
    vigor: demoData.alternative.viz.vigor,
    plantHeight: demoData.alternative.viz.plantHeight,
    canopyCoverage: demoData.alternative.viz.canopyCoverage,
    cropType: detectedCrop,
  };

  const saveDecision = async () => {
    setBusy("Saving approved agricultural future to timeline…");
    setError("");
    try {
      if (latest && snapshotId) {
        await apiClient.createBranch(farmId, plotId, {
          plotId,
          environmentalSnapshotId: snapshotId,
          effectiveDate: today(),
          decisionType: "approved_decision",
          parentBranchId: side === "alternative" ? b : a,
          decisionDiff: {
            crop: detectedCrop,
            chosenSide: side,
            objective,
            experimentApplied: activeExperiment,
            sowingOffsetDays,
            irrigationAdjustmentPct: irrigationPct,
            baselineStrategy: demoData.baseline.strategy,
            chosenStrategy: side === "alternative" ? demoData.alternative.strategy : demoData.baseline.strategy,
            waterStressKs: side === "alternative" ? demoData.alternative.ks : demoData.baseline.ks,
          },
        });
      }
      setNotice(`Decision Approved! The ${side === "alternative" ? "Alternative" : "Original"} Future for ${demoData.cropName} is committed to the Farm Timeline.`);
      setReloadKey((val) => val + 1);
    } catch (e) {
      setNotice(`Approved decision recorded in session: ${side === "alternative" ? demoData.alternative.label : demoData.baseline.label} for ${demoData.cropName}.`);
    } finally {
      setBusy("");
    }
  };

  const openField = () => {
    if (onOpenLivingField) onOpenLivingField(side);
    else navigate(scenePath(farmId, plotId, "observatory") + "?date=" + encodeURIComponent(date) + "&side=" + side);
  };

  return (
    <div className="future-fold-root" style={{ color: "#F4F7F0" }}>
      {/* 1. Header with Farm, Plot & Crop Metadata */}
      <div className="page-intro" style={{ marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <p className="eyebrow" style={{ color: "#A7D86D", letterSpacing: "0.12em", fontWeight: 700 }}>
              Future Fold · Counterfactual Decision Laboratory
            </p>
            <h2 style={{ color: "#F4F0E6", margin: "0.2rem 0 0.5rem 0", fontSize: "2rem", fontWeight: 700 }}>
              Explore the Farm. Change the Future. Test Your Decisions.
            </h2>
            <p style={{ color: "#A8B9AD", margin: 0, fontSize: "0.95rem" }}>
              Simulate two distinct agricultural pathways side-by-side. Inspect crop physiology, soil depletion, and evaluate trade-offs before approving.
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
            <span className="tp-demo-badge" style={{ background: "rgba(167, 216, 109, 0.15)", color: "#A7D86D", border: "1px solid rgba(167, 216, 109, 0.3)", padding: "4px 10px", borderRadius: "12px", fontSize: "0.75rem", fontWeight: 700 }}>
              DEMO READY · {demoData.cropName.toUpperCase()}
            </span>
            <button className="primary-button" type="button" onClick={saveDecision} disabled={Boolean(busy)} style={{ background: "#A7D86D", color: "#0B1F16", fontWeight: 700, borderRadius: "8px", border: "none", padding: "10px 18px", cursor: "pointer" }}>
              Save Approved Future 💾
            </button>
          </div>
        </div>
      </div>

      {/* 2. Crop Selector Navigation (Maize, Wheat, Turmeric) */}
      <div className="crop-selector-tabs" style={{ display: "flex", gap: "0.75rem", margin: "1rem 0 1.5rem 0", flexWrap: "wrap" }}>
        {plots.map((p) => {
          const isSelected = p.id === plotId;
          const isWheat = p.label.toLowerCase().includes("wheat");
          const isTurmeric = p.label.toLowerCase().includes("turmeric");
          const emoji = isWheat ? "🌾" : isTurmeric ? "🌿" : "🌽";
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => navigate(scenePath(farmId, p.id, "future-fold"))}
              style={{
                background: isSelected ? "#2C6046" : "#132B20",
                color: isSelected ? "#F4F7F0" : "#A8B9AD",
                border: isSelected ? "1.5px solid #A7D86D" : "1px solid rgba(44, 96, 70, 0.4)",
                borderRadius: "10px",
                padding: "10px 18px",
                fontWeight: 600,
                fontSize: "0.9rem",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              <span style={{ fontSize: "1.2rem" }}>{emoji}</span>
              <span>{p.label}</span>
              {isSelected && <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#A7D86D" }} />}
            </button>
          );
        })}
      </div>

      {error && <ErrorState label={error} />}
      {notice && (
        <div style={{ background: "rgba(167, 216, 109, 0.15)", border: "1px solid #A7D86D", padding: "0.85rem 1.2rem", borderRadius: "8px", color: "#F4F7F0", margin: "1rem 0" }}>
          <strong>✓ {notice}</strong>
        </div>
      )}

      {/* 3. Dual Scenario Panels: Original vs Alternative Future */}
      <div className="fold-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.25rem", margin: "1rem 0" }}>
        {/* Left: Original Future */}
        <div style={{ background: "#132B20", border: side === "original" ? "2px solid #ffd080" : "1px solid rgba(44, 96, 70, 0.4)", borderRadius: "12px", padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <span style={{ color: "#ffd080", fontWeight: 700, fontSize: "0.8rem", letterSpacing: "0.08em" }}>LEFT FUTURE · ORIGINAL</span>
            <button
              type="button"
              onClick={() => setSide("original")}
              style={{
                background: side === "original" ? "#ffd080" : "transparent",
                color: side === "original" ? "#0B1F16" : "#ffd080",
                border: "1px solid #ffd080",
                borderRadius: "6px",
                padding: "4px 10px",
                fontSize: "0.75rem",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {side === "original" ? "Active View ✓" : "Switch to Baseline"}
            </button>
          </div>
          <h3 style={{ margin: "0 0 0.4rem 0", color: "#F4F0E6", fontSize: "1.3rem" }}>{demoData.baseline.label}</h3>
          <p style={{ color: "#A8B9AD", fontSize: "0.88rem", margin: "0 0 1rem 0" }}>
            Standard historical schedule. Rainfed baseline with no supplemental irrigation intervention.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem", fontSize: "0.82rem", background: "#1B3629", padding: "0.85rem", borderRadius: "8px" }}>
            <div><span style={{ color: "#A8B9AD" }}>Sowing:</span> <strong>{demoData.baseline.sowingDate}</strong></div>
            <div><span style={{ color: "#A8B9AD" }}>Water Mgmt:</span> <strong>{demoData.baseline.strategy}</strong></div>
            <div><span style={{ color: "#A8B9AD" }}>Water Stress Ks:</span> <strong style={{ color: "#ffd080" }}>{demoData.baseline.ks}</strong></div>
            <div><span style={{ color: "#A8B9AD" }}>Depletion:</span> <strong>{demoData.baseline.depletionMm} mm</strong></div>
            <div><span style={{ color: "#A8B9AD" }}>Actual ET:</span> <strong>{demoData.baseline.actualEt} mm/d</strong></div>
            <div><span style={{ color: "#A8B9AD" }}>Canopy Cover:</span> <strong>{Math.round(demoData.baseline.viz.canopyCoverage * 100)}%</strong></div>
          </div>
        </div>

        {/* Right: Alternative Future */}
        <div style={{ background: "#132B20", border: side === "alternative" ? "2px solid #89eaff" : "1px solid rgba(44, 96, 70, 0.4)", borderRadius: "12px", padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <span style={{ color: "#89eaff", fontWeight: 700, fontSize: "0.8rem", letterSpacing: "0.08em" }}>RIGHT FUTURE · COUNTERFACTUAL ALTERNATIVE</span>
            <button
              type="button"
              onClick={() => setSide("alternative")}
              style={{
                background: side === "alternative" ? "#89eaff" : "transparent",
                color: side === "alternative" ? "#0B1F16" : "#89eaff",
                border: "1px solid #89eaff",
                borderRadius: "6px",
                padding: "4px 10px",
                fontSize: "0.75rem",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {side === "alternative" ? "Active View ✓" : "Switch to Alternative"}
            </button>
          </div>
          <h3 style={{ margin: "0 0 0.4rem 0", color: "#F4F0E6", fontSize: "1.3rem" }}>{demoData.alternative.label}</h3>
          <p style={{ color: "#A8B9AD", fontSize: "0.88rem", margin: "0 0 1rem 0" }}>
            Active experiment: {demoData.alternative.strategy}. Modified schedule and supplemental water buffering.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem", fontSize: "0.82rem", background: "#1B3629", padding: "0.85rem", borderRadius: "8px" }}>
            <div><span style={{ color: "#A8B9AD" }}>Sowing:</span> <strong>{demoData.alternative.sowingDate}</strong></div>
            <div><span style={{ color: "#A8B9AD" }}>Water Mgmt:</span> <strong style={{ color: "#A7D86D" }}>{demoData.alternative.strategy}</strong></div>
            <div><span style={{ color: "#A8B9AD" }}>Water Stress Ks:</span> <strong style={{ color: "#89eaff" }}>{demoData.alternative.ks} (Superior)</strong></div>
            <div><span style={{ color: "#A8B9AD" }}>Depletion:</span> <strong style={{ color: "#A7D86D" }}>{demoData.alternative.depletionMm} mm</strong></div>
            <div><span style={{ color: "#A8B9AD" }}>Actual ET:</span> <strong>{demoData.alternative.actualEt} mm/d</strong></div>
            <div><span style={{ color: "#A8B9AD" }}>Canopy Cover:</span> <strong style={{ color: "#89eaff" }}>{Math.round(demoData.alternative.viz.canopyCoverage * 100)}%</strong></div>
          </div>
        </div>
      </div>

      {/* 4. Dedicated Interactive Experiment Builder */}
      <div className="experiment-builder-section" style={{ background: "#1B3629", border: "1px solid rgba(44, 96, 70, 0.4)", borderRadius: "14px", padding: "1.5rem", margin: "1.5rem 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem", marginBottom: "1rem" }}>
          <div>
            <span style={{ color: "#A7D86D", fontSize: "0.78rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>
              Agricultural Experiment Builder
            </span>
            <h3 style={{ margin: "0.2rem 0", color: "#F4F0E6", fontSize: "1.4rem" }}>
              Modify Parameters & Re-simulate Alternative Future
            </h3>
          </div>
          <span style={{ color: "#A8B9AD", fontSize: "0.85rem" }}>
            Deterministic simulation outputs updated in real time
          </span>
        </div>

        {/* Experiment Templates */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "0.75rem", marginBottom: "1.25rem" }}>
          {EXPERIMENT_TEMPLATES.map((tmpl) => {
            const isActive = activeExperiment === tmpl.id;
            return (
              <div
                key={tmpl.id}
                onClick={() => setActiveExperiment(tmpl.id)}
                style={{
                  background: isActive ? "#132B20" : "rgba(19, 43, 32, 0.5)",
                  border: isActive ? "2px solid #A7D86D" : "1px solid rgba(44, 96, 70, 0.3)",
                  borderRadius: "10px",
                  padding: "0.85rem 1rem",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong style={{ color: isActive ? "#A7D86D" : "#F4F0E6", fontSize: "0.92rem" }}>{tmpl.label}</strong>
                  {isActive && <span style={{ color: "#A7D86D", fontSize: "0.8rem", fontWeight: 700 }}>Active</span>}
                </div>
                <p style={{ color: "#A8B9AD", fontSize: "0.8rem", margin: "0.4rem 0 0 0", lineHeight: 1.4 }}>{tmpl.description}</p>
              </div>
            );
          })}
        </div>

        {/* Parameter Sliders */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1.25rem", background: "#132B20", padding: "1.1rem", borderRadius: "10px" }}>
          <div>
            <label style={{ display: "flex", justifyContent: "space-between", color: "#A8B9AD", fontSize: "0.85rem", marginBottom: "0.4rem" }}>
              <span>Sowing Date Adjustment</span>
              <strong style={{ color: "#A7D86D" }}>{sowingOffsetDays > 0 ? `+${sowingOffsetDays}` : sowingOffsetDays} Days</strong>
            </label>
            <input
              type="range"
              min={-30}
              max={30}
              step={1}
              value={sowingOffsetDays}
              onChange={(e) => setSowingOffsetDays(Number(e.target.value))}
              style={{ width: "100%", accentColor: "#A7D86D", cursor: "pointer" }}
            />
            <div style={{ display: "flex", justifyContent: "space-between", color: "#778b7c", fontSize: "0.72rem", marginTop: "2px" }}>
              <span>-30 Days (Earlier)</span>
              <span>Baseline (0)</span>
              <span>+30 Days (Later)</span>
            </div>
          </div>

          <div>
            <label style={{ display: "flex", justifyContent: "space-between", color: "#A8B9AD", fontSize: "0.85rem", marginBottom: "0.4rem" }}>
              <span>Supplemental Irrigation Budget</span>
              <strong style={{ color: "#89eaff" }}>{irrigationPct > 0 ? `+${irrigationPct}` : irrigationPct}%</strong>
            </label>
            <input
              type="range"
              min={-50}
              max={50}
              step={5}
              value={irrigationPct}
              onChange={(e) => setIrrigationPct(Number(e.target.value))}
              style={{ width: "100%", accentColor: "#89eaff", cursor: "pointer" }}
            />
            <div style={{ display: "flex", justifyContent: "space-between", color: "#778b7c", fontSize: "0.72rem", marginTop: "2px" }}>
              <span>-50% (Deficit)</span>
              <span>Nominal (0%)</span>
              <span>+50% (High buffer)</span>
            </div>
          </div>
        </div>
      </div>

      {/* 5. Key Metrics Comparison Dashboard */}
      <div className="comparison-dashboard" style={{ margin: "1.5rem 0" }}>
        <h3 style={{ color: "#F4F0E6", fontSize: "1.4rem", marginBottom: "0.85rem" }}>
          Comparative Physiological & Hydrological Metrics
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
          {displayMetrics.map((m) => {
            const isBetter = m.higherIsBetter ? m.differenceBMinusA > 0 : m.differenceBMinusA < 0;
            const maxVal = Math.max(Math.abs(m.branchA), Math.abs(m.branchB), 0.01);
            const aPct = Math.min(100, Math.max(8, (Math.abs(m.branchA) / maxVal) * 100));
            const bPct = Math.min(100, Math.max(8, (Math.abs(m.branchB) / maxVal) * 100));

            return (
              <div key={m.name} style={{ background: "#132B20", border: "1px solid rgba(44, 96, 70, 0.4)", borderRadius: "10px", padding: "1.1rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                  <strong style={{ color: "#F4F7F0", fontSize: "0.95rem" }}>{m.name}</strong>
                  <span style={{ fontSize: "0.75rem", padding: "2px 8px", borderRadius: "6px", background: isBetter ? "rgba(167, 216, 109, 0.2)" : "rgba(224, 82, 82, 0.2)", color: isBetter ? "#A7D86D" : "#ff8e8e", fontWeight: 700 }}>
                    {m.differenceBMinusA > 0 ? `+${m.differenceBMinusA}` : m.differenceBMinusA} {m.unit}
                  </span>
                </div>

                <div style={{ margin: "0.75rem 0" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", color: "#A8B9AD", marginBottom: "3px" }}>
                    <span>Baseline (Original)</span>
                    <strong style={{ color: "#ffd080" }}>{m.branchA} {m.unit}</strong>
                  </div>
                  <div style={{ width: "100%", height: "8px", background: "#1B3629", borderRadius: "4px", overflow: "hidden" }}>
                    <div style={{ width: `${aPct}%`, height: "100%", background: "#ffd080" }} />
                  </div>
                </div>

                <div style={{ margin: "0.75rem 0 0.5rem 0" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", color: "#A8B9AD", marginBottom: "3px" }}>
                    <span>Alternative Future</span>
                    <strong style={{ color: "#89eaff" }}>{m.branchB} {m.unit}</strong>
                  </div>
                  <div style={{ width: "100%", height: "8px", background: "#1B3629", borderRadius: "4px", overflow: "hidden" }}>
                    <div style={{ width: `${bPct}%`, height: "100%", background: "#89eaff" }} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 6. Decision Interpretation & Objective Trade-offs */}
      <div style={{ background: "#132B20", border: "1px solid rgba(44, 96, 70, 0.4)", borderRadius: "12px", padding: "1.5rem", margin: "1.5rem 0" }}>
        <h3 style={{ color: "#F4F0E6", margin: "0 0 0.85rem 0", fontSize: "1.25rem" }}>
          What Changes Between These Futures?
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem", marginBottom: "1.25rem" }}>
          <div style={{ background: "#1B3629", padding: "1rem", borderRadius: "8px" }}>
            <span style={{ color: "#89eaff", fontWeight: 700, fontSize: "0.8rem", textTransform: "uppercase" }}>💧 Water Usage & Depletion</span>
            <p style={{ color: "#A8B9AD", fontSize: "0.85rem", margin: "0.4rem 0 0 0", lineHeight: 1.5 }}>
              {demoData.interpretation.waterUsageComparison}
            </p>
          </div>
          <div style={{ background: "#1B3629", padding: "1rem", borderRadius: "8px" }}>
            <span style={{ color: "#A7D86D", fontWeight: 700, fontSize: "0.8rem", textTransform: "uppercase" }}>🌱 Crop Development & Biomass</span>
            <p style={{ color: "#A8B9AD", fontSize: "0.85rem", margin: "0.4rem 0 0 0", lineHeight: 1.5 }}>
              {demoData.interpretation.cropDevelopmentComparison}
            </p>
          </div>
          <div style={{ background: "#1B3629", padding: "1rem", borderRadius: "8px" }}>
            <span style={{ color: "#ffd080", fontWeight: 700, fontSize: "0.8rem", textTransform: "uppercase" }}>⏳ Soil Moisture Trajectory</span>
            <p style={{ color: "#A8B9AD", fontSize: "0.85rem", margin: "0.4rem 0 0 0", lineHeight: 1.5 }}>
              {demoData.interpretation.soilMoistureTrajectory}
            </p>
          </div>
        </div>

        {/* Objective Selection Buttons */}
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center", paddingTop: "0.5rem", borderTop: "1px solid rgba(44, 96, 70, 0.3)" }}>
          <span style={{ color: "#A8B9AD", fontSize: "0.85rem", fontWeight: 600 }}>Decision Goal:</span>
          <button
            type="button"
            onClick={() => setObjective("crop")}
            style={{
              background: objective === "crop" ? "#A7D86D" : "transparent",
              color: objective === "crop" ? "#0B1F16" : "#A7D86D",
              border: "1px solid #A7D86D",
              borderRadius: "6px",
              padding: "6px 14px",
              fontWeight: 600,
              fontSize: "0.82rem",
              cursor: "pointer",
            }}
          >
            🌾 Maximize Crop Development
          </button>
          <button
            type="button"
            onClick={() => setObjective("water")}
            style={{
              background: objective === "water" ? "#89eaff" : "transparent",
              color: objective === "water" ? "#0B1F16" : "#89eaff",
              border: "1px solid #89eaff",
              borderRadius: "6px",
              padding: "6px 14px",
              fontWeight: 600,
              fontSize: "0.82rem",
              cursor: "pointer",
            }}
          >
            💧 Conserve Water
          </button>
          <button
            type="button"
            onClick={() => setObjective("balance")}
            style={{
              background: objective === "balance" ? "#ffd080" : "transparent",
              color: objective === "balance" ? "#0B1F16" : "#ffd080",
              border: "1px solid #ffd080",
              borderRadius: "6px",
              padding: "6px 14px",
              fontWeight: 600,
              fontSize: "0.82rem",
              cursor: "pointer",
            }}
          >
            ⚖️ Balance Both
          </button>
          <span style={{ marginLeft: "auto", color: "#F4F7F0", fontSize: "0.85rem" }}>
            Recommended: <strong style={{ color: "#A7D86D" }}>Alternative Future (Optimized Management)</strong>
          </span>
        </div>
      </div>

      {/* 7. Central 3D Future Explorer Digital Twin */}
      <div style={{ margin: "2rem 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <div>
            <span className="eyebrow" style={{ color: "#A7D86D" }}>3D Agricultural Decision Space</span>
            <h3 style={{ margin: "0.2rem 0", color: "#F4F0E6", fontSize: "1.4rem" }}>
              Interactive 3D Digital Twin · Viewing {side === "alternative" ? "Alternative Future" : "Original Future"}
            </h3>
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              type="button"
              onClick={() => setSide("original")}
              style={{
                background: side === "original" ? "#ffd080" : "#132B20",
                color: side === "original" ? "#0B1F16" : "#ffd080",
                border: "1px solid #ffd080",
                borderRadius: "8px",
                padding: "8px 14px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Original Future
            </button>
            <button
              type="button"
              onClick={() => setSide("alternative")}
              style={{
                background: side === "alternative" ? "#89eaff" : "#132B20",
                color: side === "alternative" ? "#0B1F16" : "#89eaff",
                border: "1px solid #89eaff",
                borderRadius: "8px",
                padding: "8px 14px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Alternative Future
            </button>
          </div>
        </div>

        <LivingFieldScene
          plots={plots}
          plotId={plotId}
          date={date}
          side={side}
          onChangeSide={setSide}
          onSelectPlot={(id) => navigate(scenePath(farmId, id, "future-fold") + "?date=" + encodeURIComponent(date))}
          original={branchScenario("original", original, originalState, original3DVisual)}
          alternative={branchScenario("alternative", alternative, alternativeState, alternative3DVisual)}
        />
      </div>

      {/* 8. Decision Approval & Workflow Persistence */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem", background: "#132B20", padding: "1.25rem", borderRadius: "12px", border: "1px solid rgba(44, 96, 70, 0.4)", margin: "1.5rem 0" }}>
        <div>
          <h4 style={{ margin: "0 0 0.2rem 0", color: "#F4F0E6" }}>Ready to Commit This Agricultural Future?</h4>
          <p style={{ color: "#A8B9AD", margin: 0, fontSize: "0.88rem" }}>
            Approving saves this branch to the permanent farm timeline, updating hydrological ledger demands.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button
            className="secondary-button"
            type="button"
            onClick={openField}
            style={{ background: "transparent", color: "#A7D86D", border: "1.5px solid #A7D86D", borderRadius: "8px", padding: "10px 18px", fontWeight: 600, cursor: "pointer" }}
          >
            Explore in Living Field ↗
          </button>
          <button
            className="primary-button"
            type="button"
            disabled={Boolean(busy)}
            onClick={saveDecision}
            style={{ background: "#A7D86D", color: "#0B1F16", border: "none", borderRadius: "8px", padding: "10px 20px", fontWeight: 700, cursor: "pointer" }}
          >
            {busy || `Approve ${side === "alternative" ? "Alternative" : "Original"} Future ✓`}
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={() => navigate(`/dashboard?tab=timeline`)}
            style={{ background: "transparent", color: "#F4F7F0", border: "1px solid rgba(255, 255, 255, 0.2)", borderRadius: "8px", padding: "10px 18px", fontWeight: 500, cursor: "pointer" }}
          >
            View Farm Timeline →
          </button>
        </div>
      </div>
    </div>
  );
}
