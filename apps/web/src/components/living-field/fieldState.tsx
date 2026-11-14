import { useEffect, useMemo, useState } from "react";
import type { Branch, Measurement, ScientificState } from "../../services/apiClient";
import { apiClient } from "../../services/apiClient";
import { examplePlots, LivingFieldScene } from "./LivingFieldScene";
import type { FieldPlot, FieldScenario, FieldSide } from "./LivingFieldScene";

export const today = () => new Date().toLocaleDateString("sv-SE");
export const scenePath = (farmId: string, plotId: string, view: "observatory" | "future-fold") =>
  "/farms/" + encodeURIComponent(farmId) + "/plots/" + encodeURIComponent(plotId) + "/" + view;

  const fields = [
  ["waterStress", "Water stress"],
  ["soilWater", "Root-zone storage"],
  ["actualEvapotranspiration", "Actual evapotranspiration"],
  ["cropWaterDemand", "Potential evapotranspiration"],
  ["irrigation", "Irrigation"],
  ["rainfall", "Rainfall"],
] as const;

function measurement(science: ScientificState, key: string) {
  const item = science.state[key] as { value?: unknown; availability?: { status?: string } } | undefined;
  const value = item?.value;
  if (science.availability === "available" && item?.availability?.status === "available" && typeof value === "number" && Number.isFinite(value)) return value;
  return undefined;
}

function scientificMetrics(science: ScientificState) {
  const rows = fields.flatMap(([key, label]) => {
    const item = science.state[key] as Measurement | undefined;
    const value = measurement(science, key);
    if (value == null || !item) return [];
    return [{ label, value: value + " " + item.unit }];
  });
  return rows.length ? rows : [{ label: "Stored state", value: "No numeric outputs for this date" }];
}

export function useFieldState(farmId: string, plotId: string, branchId: string, date: string, runId?: string) {
  const [request, setRequest] = useState<{ key: string; state?: ScientificState }>();
  const key = JSON.stringify([farmId, plotId, branchId, date, runId]);
  useEffect(() => {
    if (!branchId || !date) return;
    let current = true;
    apiClient.getScientificState(farmId, plotId, branchId, date).then((state) => {
      if (!current) return;
      const matches = state.farmId === farmId && state.plotId === plotId && state.branchId === branchId
        && state.date === date && (!runId || state.simulationRunId === runId);
      setRequest({ key, state: matches ? state : undefined });
    }).catch(() => { if (current) setRequest({ key }); });
    return () => { current = false; };
  }, [branchId, date, farmId, key, plotId, runId]);
  return {
    pending: Boolean(branchId && date && request?.key !== key),
    state: request?.key === key ? request.state : undefined,
  };
}

export function useFarmPlots(farmId: string, plotId: string) {
  const [result, setResult] = useState<{ farmId: string; plots: FieldPlot[] }>();
  useEffect(() => {
    let current = true;
    apiClient.getFarm(farmId).then((farm) => {
      if (!current || farm.farmId !== farmId) return;
      setResult({ farmId, plots: farm.plots.map((plot, index) => ({
        id: plot.plotId,
        label: (plot.cropCanonicalName || "Plot") + " · " + (index + 1),
      })) });
    }).catch(() => { if (current) setResult({ farmId, plots: [] }); });
    return () => { current = false; };
  }, [farmId]);
  return useMemo(() => {
    const plots = result?.farmId === farmId ? result.plots : [];
    return plots.some((plot) => plot.id === plotId)
      ? plots : [...plots, { id: plotId, label: "Plot " + plotId.slice(0, 8) }];
  }, [farmId, plotId, result]);
}

export function branchScenario(
  side: FieldSide, branch: Branch | undefined, request: ReturnType<typeof useFieldState>,
): FieldScenario {
  const state = request.state;
  const label = branch ? branch.decisionType.replaceAll("_", " ") + " · " + branch.branchId.slice(0, 8)
    : side === "original" ? "Original decision" : "Alternative decision";
  const fao = Boolean(state?.provenance.engine?.toLowerCase().includes("fao"));
  const description = request.pending ? "Loading the stored result for this date…"
    : state ? (fao ? "FAO-56 model state · " : "Stored model state · ") + [state.provenance.engine, state.provenance.engineVersion].filter(Boolean).join(" ")
    : "No matching model result for this date. The field geometry stays illustrative.";
  const stress = state && fao ? measurement(state, "waterStress") : undefined;
  const soil = state && fao ? measurement(state, "soilWater") : undefined;
  return {
    side, label, description, metrics: state ? scientificMetrics(state) : undefined,
    visual: stress != null || soil != null ? { waterStress: stress, soilWaterMm: soil } : undefined,
  };
}

export function ExampleField() {
  const [date, setDate] = useState("2026-11-13");
  const [plotId, setPlotId] = useState(examplePlots[0].id);
  return <>
    <div className="page-intro">
      <p className="eyebrow">Illustrative example</p>
      <h2>Living Field</h2>
      <p>Explore farm plots, look below the surface and switch between example decisions.</p>
    </div>
    <div className="toolbar"><label>Absolute date<input type="date" value={date}
      onChange={(event) => { if (event.target.value) setDate(event.target.value); }} /></label></div>
    <LivingFieldScene plots={examplePlots} plotId={plotId} onSelectPlot={setPlotId} date={date}
      original={{ side: "original", label: "Original plan", description: "Keep the existing watering plan. Illustrative example." }}
      alternative={{ side: "alternative", label: "Alternative plan", description: "Review watering before the next field visit. Illustrative example." }} />
  </>;
}
