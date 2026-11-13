/** TerraPulse Developer A local C1/C3/C5/C7/C8 science envelope.
 * Developer D v0.1 is not modified. Units are explicit. Missing != 0.
 */
export type ISODate = string; // YYYY-MM-DD
export type ScienceEngine = "fao56" | "aquacrop";
export type MetricAvailability = "available" | "inactive" | "unsupported" | "unavailable";
export type ScienceStatus = "active" | "inactive";
export type WeatherKind = "observation" | "model-estimate" | "forecast" | "assumption";

export type ScienceMetric = {
  unit: "mm" | "mm/day" | "m" | "m3/m3" | "fraction" | "tonnes/ha";
  definition: string;
} & (
  | { status: "available"; value: number }
  | { status: Exclude<MetricAvailability, "available">; value: null }
);

/** Exact fields from Developer D v0.1 ScientificState (flat compatibility view). */
export interface ScientificStateV01 {
  plotId: string; branchId: string; date: ISODate;
  engine: ScienceEngine; modelVersion: string; growthStage: string | null;
  rootZoneDepletionMm: number | null;
  actualEtMm: number | null; rainfallMm: number | null;
  effectiveIrrigationMm: number | null; drainageMm: number | null;
  waterStressIndex: number | null; // FAO56: severity = 1 - Ks
  biomassTonnesPerHa: number | null;
  yieldTonnesPerHa: number | null;
}

export interface ScienceStateV02 {
  plotId: string; branchId: string; date: ISODate;
  runId?: string; status: ScienceStatus;
  cropActive?: boolean; elapsedDay?: number | null;
  seasonCounter?: number; dap?: number;
  weatherMemberId?: string | null; provenanceId?: string;
  v01C3: ScientificStateV01 | null;
  metrics: Record<string, ScienceMetric>;
}

interface ScienceRunBaseV02 {
  contractVersion: "science-0.2";
  scientificOutputVersion: "dev-a-science-output-0.2.0";
  adapterVersion: "dev-a-adapters-0.2.0";
  registryVersion: "dev-a-0.2.0";
  runId: string;
  capability: { capabilityId: string; [key: string]: unknown };
  plotId: string; branchId: string;
  inputSnapshotId: string; weatherRealizationId: string;
  startDate: ISODate; endDate: ISODate;
  warnings: string[];
  states: ScienceStateV02[];
}

export interface FaoScienceRunV02 extends ScienceRunBaseV02 {
  engine: "fao56"; modelVersion: "fao56-single-kc-1.0"; status: "completed";
  evidenceKind: "executed-fao56";
  inputHash: string;
  /** SHA-256 of the canonical dated weather records. */
  weatherHash: string;
  weatherMemberId: string | null;
}

export interface AquaCropScienceRunV02 extends ScienceRunBaseV02 {
  engine: "aquacrop"; modelVersion: "aquacrop-ospy-3.1.0"; status: "completed-output-parse";
  evidenceKind: "historical-fixture" | "executed-aquacrop" | "provided-unverified-output";
  /** SHA-256 of the source weather file when known. A caller-supplied hash alone does not verify execution. */
  weatherHash: string | null;
  parameterVersion: string; parameterSource: string;
  tableHashes: {
    cropGrowth: string; waterFlux: string; seasonalResults: string;
    waterStorage: string | null;
  };
}

export type ScienceRunV02 = FaoScienceRunV02 | AquaCropScienceRunV02;

export interface ScienceProblem {
  status: "failed";
  code: string; // e.g., WEATHER_COVERAGE, LEDGER_DEPTH_MISMATCH
  error: string;
}

/** Do not silently replace Developer D's original C1/C3/C5/C7/C8 schema.
 * Register conversion behavior at the service boundary and test end to end.
 */
