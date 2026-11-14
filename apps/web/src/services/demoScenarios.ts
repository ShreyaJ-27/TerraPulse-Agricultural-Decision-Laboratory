/**
 * TerraPulse Demo Scenario Dataset
 * Three-crop demo: Maize, Wheat, Turmeric
 *
 * This module provides complete, self-contained demo data for the FutureFold
 * feature. It is consumed by demoProvider.ts when the backend is unavailable
 * or when viewing a "blocked" crop.
 */

// ---------------------------------------------------------------------------
// Core types
// ---------------------------------------------------------------------------

export type DailyState = {
  date: string;
  waterStressKs: number;
  rootZoneDepletionMm: number;
  actualEtMm: number;
  potentialEtMm: number;
  rainfallMm: number;
  irrigationMm: number;
  soilWaterMm: number;
};

export type ComparisonMetric = {
  name: string;
  unit: string;
  branchA: number;
  branchB: number;
  differenceBMinusA: number;
  higherIsBetter: boolean;
};

export type ExperimentTemplate = {
  id: string;
  label: string;
  description: string;
  parameterChanges: Record<string, number | string>;
  /** Relative effects on key metrics */
  effects: {
    ksChange: number;         // absolute change, e.g. +0.08
    depletionChangePct: number; // percentage change, negative = improvement
    waterUsedChangePct?: number;
  };
};

export type Viz3DParams = {
  /** 0–1 plant vigour */
  vigor: number;
  /** Normalised plant height 0–1 (1 = tallest) */
  plantHeight: number;
  /** Fraction of plot covered by canopy 0–1 */
  canopyCoverage: number;
  /** Geometry style for 3-D renderer */
  geometryType: "maize" | "wheat" | "broadleaf";
  /** Dominant leaf colour hex */
  leafColor: string;
  /** Whether the scene shows dryness stress markers */
  showStressMarkers: boolean;
};

export type ScenarioBranch = {
  label: string;
  sowingDate: string;
  irrigationStrategy: string;
  waterStressKs: number;
  rootZoneDepletionMm: number;
  actualEtMmPerDay: number;
  dailyStates: DailyState[];
  viz3D: Viz3DParams;
};

export type DemoCrop = {
  cropId: string;
  canonicalName: string;
  scientificName: string;
  geometryType: Viz3DParams["geometryType"];
  original: ScenarioBranch;
  alternative: ScenarioBranch;
  comparisonMetrics: ComparisonMetric[];
  experimentTemplates: ExperimentTemplate[];
};

export type DemoScenarioDataset = {
  version: string;
  generatedAt: string;
  crops: DemoCrop[];
};

// ---------------------------------------------------------------------------
// Shared experiment templates (crop-agnostic templates, applied to all crops)
// ---------------------------------------------------------------------------

const EXPERIMENT_TEMPLATES: ExperimentTemplate[] = [
  {
    id: "change_sowing_date",
    label: "Earlier sowing date (−14 days)",
    description: "Shift the sowing date 14 days earlier to capture better soil moisture and temperature conditions during establishment.",
    parameterChanges: { sowingDateOffsetDays: -14 },
    effects: { ksChange: +0.08, depletionChangePct: -20 },
  },
  {
    id: "reduce_irrigation",
    label: "Reduce irrigation (−30%)",
    description: "Cut irrigation applications by 30% to test deficit-irrigation tolerance and water saving potential.",
    parameterChanges: { irrigationReductionPct: 30 },
    effects: { ksChange: -0.10, depletionChangePct: +15 },
  },
  {
    id: "increase_irrigation",
    label: "Increase irrigation (+20%)",
    description: "Add 20% more irrigation during critical growth stages to maintain optimal soil water content.",
    parameterChanges: { irrigationIncreasePct: 20 },
    effects: { ksChange: +0.07, depletionChangePct: -12 },
  },
  {
    id: "rainfed_vs_irrigated",
    label: "Rainfed vs. full irrigation",
    description: "Compare a fully rainfed approach against a fully irrigated strategy across the season.",
    parameterChanges: { irrigationStrategy: "rainfed", comparisonStrategy: "full_irrigation" },
    effects: { ksChange: +0.15, depletionChangePct: -35, waterUsedChangePct: -100 },
  },
  {
    id: "optimize_water",
    label: "Drip vs. flood irrigation",
    description: "Compare drip irrigation (high efficiency) with flood irrigation to quantify water saving and yield benefits.",
    parameterChanges: { irrigationType: "drip", comparisonType: "flood" },
    effects: { ksChange: +0.09, depletionChangePct: -20, waterUsedChangePct: -25 },
  },
  {
    id: "compare_strategies",
    label: "Conservative vs. intensive management",
    description: "Side-by-side trade-off analysis: conservative low-input strategy versus intensive management for maximum yield.",
    parameterChanges: { managementIntensity: "conservative", comparisonIntensity: "intensive" },
    effects: { ksChange: +0.12, depletionChangePct: -25 },
  },
];

// ---------------------------------------------------------------------------
// Daily state generators
// ---------------------------------------------------------------------------

/** Generate 7 daily states starting from `startDate` based on scenario params. */
function generateDailyStates(opts: {
  startDate: string;
  baseKs: number;
  baseDepletion: number;
  baseActualEt: number;
  basePotentialEt: number;
  avgRainfall: number;
  avgIrrigation: number;
  fieldCapacityMm: number;
  trend: "stable" | "improving" | "declining";
}): DailyState[] {
  const {
    startDate, baseKs, baseDepletion, baseActualEt, basePotentialEt,
    avgRainfall, avgIrrigation, fieldCapacityMm, trend,
  } = opts;

  const states: DailyState[] = [];
  const start = new Date(startDate);

  for (let i = 0; i < 7; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    const dateStr = d.toISOString().slice(0, 10);

    // Apply deterministic trend
    const trendFactor = trend === "improving" ? (i * 0.01)
      : trend === "declining" ? -(i * 0.01)
      : 0;

    const ks = Math.min(1.0, Math.max(0.1, baseKs + trendFactor + (i % 3 === 0 ? 0.01 : -0.005)));
    const depletion = Math.max(5, baseDepletion - i * (trend === "improving" ? 2 : trend === "declining" ? -1.5 : 0.5));
    const rainfall = i % 3 === 1 ? avgRainfall * 2.5 : avgRainfall * 0.3;
    const irrigation = i % 2 === 0 ? avgIrrigation : 0;
    const soilWater = Math.max(0, fieldCapacityMm - depletion);

    states.push({
      date: dateStr,
      waterStressKs: parseFloat(ks.toFixed(3)),
      rootZoneDepletionMm: parseFloat(depletion.toFixed(1)),
      actualEtMm: parseFloat((baseActualEt * ks + (i % 2 === 0 ? 0.1 : -0.05)).toFixed(2)),
      potentialEtMm: parseFloat(basePotentialEt.toFixed(2)),
      rainfallMm: parseFloat(rainfall.toFixed(1)),
      irrigationMm: parseFloat(irrigation.toFixed(1)),
      soilWaterMm: parseFloat(soilWater.toFixed(1)),
    });
  }
  return states;
}

// ---------------------------------------------------------------------------
// MAIZE
// ---------------------------------------------------------------------------

const MAIZE_FIELD_CAPACITY_MM = 350; // fc=0.35 × 1000mm root zone

const maize: DemoCrop = {
  cropId: "maize",
  canonicalName: "Maize",
  scientificName: "Zea mays",
  geometryType: "maize",
  original: {
    label: "Rainfed (baseline)",
    sowingDate: "2026-05-15",
    irrigationStrategy: "rainfed",
    waterStressKs: 0.72,
    rootZoneDepletionMm: 85,
    actualEtMmPerDay: 4.2,
    dailyStates: generateDailyStates({
      startDate: "2026-11-07",
      baseKs: 0.72,
      baseDepletion: 85,
      baseActualEt: 4.2,
      basePotentialEt: 5.8,
      avgRainfall: 3.5,
      avgIrrigation: 0,
      fieldCapacityMm: MAIZE_FIELD_CAPACITY_MM,
      trend: "stable",
    }),
    viz3D: {
      vigor: 0.60,
      plantHeight: 0.65,
      canopyCoverage: 0.55,
      geometryType: "maize",
      leafColor: "#5d8a3c",
      showStressMarkers: true,
    },
  },
  alternative: {
    label: "Supplemental irrigation",
    sowingDate: "2026-05-01",
    irrigationStrategy: "supplemental_irrigation",
    waterStressKs: 0.89,
    rootZoneDepletionMm: 42,
    actualEtMmPerDay: 5.8,
    dailyStates: generateDailyStates({
      startDate: "2026-11-07",
      baseKs: 0.89,
      baseDepletion: 42,
      baseActualEt: 5.8,
      basePotentialEt: 6.5,
      avgRainfall: 3.5,
      avgIrrigation: 25,
      fieldCapacityMm: MAIZE_FIELD_CAPACITY_MM,
      trend: "improving",
    }),
    viz3D: {
      vigor: 0.90,
      plantHeight: 1.00,
      canopyCoverage: 0.82,
      geometryType: "maize",
      leafColor: "#3a7d20",
      showStressMarkers: false,
    },
  },
  comparisonMetrics: [
    { name: "waterStressKs",         unit: "dimensionless", branchA: 0.72, branchB: 0.89, differenceBMinusA: +0.17, higherIsBetter: true  },
    { name: "rootZoneDepletionMm",   unit: "mm",            branchA: 85,   branchB: 42,   differenceBMinusA: -43,   higherIsBetter: false },
    { name: "actualEtMm",            unit: "mm/day",        branchA: 4.2,  branchB: 5.8,  differenceBMinusA: +1.6,  higherIsBetter: true  },
    { name: "canopyCoverage",        unit: "fraction",      branchA: 0.55, branchB: 0.82, differenceBMinusA: +0.27, higherIsBetter: true  },
    { name: "vigor",                 unit: "index",         branchA: 0.60, branchB: 0.90, differenceBMinusA: +0.30, higherIsBetter: true  },
  ],
  experimentTemplates: EXPERIMENT_TEMPLATES,
};

// ---------------------------------------------------------------------------
// WHEAT
// ---------------------------------------------------------------------------

const WHEAT_FIELD_CAPACITY_MM = 350;

const wheat: DemoCrop = {
  cropId: "wheat",
  canonicalName: "Wheat",
  scientificName: "Triticum aestivum",
  geometryType: "wheat",
  original: {
    label: "Rainfed (baseline)",
    sowingDate: "2026-11-01",
    irrigationStrategy: "rainfed",
    waterStressKs: 0.68,
    rootZoneDepletionMm: 78,
    actualEtMmPerDay: 3.8,
    dailyStates: generateDailyStates({
      startDate: "2026-11-07",
      baseKs: 0.68,
      baseDepletion: 78,
      baseActualEt: 3.8,
      basePotentialEt: 5.6,
      avgRainfall: 4.0,
      avgIrrigation: 0,
      fieldCapacityMm: WHEAT_FIELD_CAPACITY_MM,
      trend: "stable",
    }),
    viz3D: {
      vigor: 0.55,
      plantHeight: 0.50,
      canopyCoverage: 0.45,
      geometryType: "wheat",
      leafColor: "#8aad48",
      showStressMarkers: true,
    },
  },
  alternative: {
    label: "Improved water management",
    sowingDate: "2026-10-20",
    irrigationStrategy: "improved_water_management",
    waterStressKs: 0.84,
    rootZoneDepletionMm: 45,
    actualEtMmPerDay: 5.1,
    dailyStates: generateDailyStates({
      startDate: "2026-11-07",
      baseKs: 0.84,
      baseDepletion: 45,
      baseActualEt: 5.1,
      basePotentialEt: 6.1,
      avgRainfall: 4.0,
      avgIrrigation: 20,
      fieldCapacityMm: WHEAT_FIELD_CAPACITY_MM,
      trend: "improving",
    }),
    viz3D: {
      vigor: 0.85,
      plantHeight: 0.85,
      canopyCoverage: 0.75,
      geometryType: "wheat",
      leafColor: "#5a9e30",
      showStressMarkers: false,
    },
  },
  comparisonMetrics: [
    { name: "waterStressKs",         unit: "dimensionless", branchA: 0.68, branchB: 0.84, differenceBMinusA: +0.16, higherIsBetter: true  },
    { name: "rootZoneDepletionMm",   unit: "mm",            branchA: 78,   branchB: 45,   differenceBMinusA: -33,   higherIsBetter: false },
    { name: "actualEtMm",            unit: "mm/day",        branchA: 3.8,  branchB: 5.1,  differenceBMinusA: +1.3,  higherIsBetter: true  },
    { name: "canopyCoverage",        unit: "fraction",      branchA: 0.45, branchB: 0.75, differenceBMinusA: +0.30, higherIsBetter: true  },
    { name: "vigor",                 unit: "index",         branchA: 0.55, branchB: 0.85, differenceBMinusA: +0.30, higherIsBetter: true  },
  ],
  experimentTemplates: EXPERIMENT_TEMPLATES,
};

// ---------------------------------------------------------------------------
// TURMERIC
// ---------------------------------------------------------------------------

const TURMERIC_FIELD_CAPACITY_MM = 350;

const turmeric: DemoCrop = {
  cropId: "turmeric",
  canonicalName: "Turmeric",
  scientificName: "Curcuma longa",
  geometryType: "broadleaf",
  original: {
    label: "Standard irrigation (baseline)",
    sowingDate: "2026-04-10",
    irrigationStrategy: "standard_irrigation",
    waterStressKs: 0.75,
    rootZoneDepletionMm: 65,
    actualEtMmPerDay: 4.5,
    dailyStates: generateDailyStates({
      startDate: "2026-11-07",
      baseKs: 0.75,
      baseDepletion: 65,
      baseActualEt: 4.5,
      basePotentialEt: 6.0,
      avgRainfall: 5.0,
      avgIrrigation: 15,
      fieldCapacityMm: TURMERIC_FIELD_CAPACITY_MM,
      trend: "stable",
    }),
    viz3D: {
      vigor: 0.65,
      plantHeight: 0.40,
      canopyCoverage: 0.60,
      geometryType: "broadleaf",
      leafColor: "#4e8c35",
      showStressMarkers: true,
    },
  },
  alternative: {
    label: "Optimised drip irrigation",
    sowingDate: "2026-04-01",
    irrigationStrategy: "optimized_drip",
    waterStressKs: 0.91,
    rootZoneDepletionMm: 35,
    actualEtMmPerDay: 5.5,
    dailyStates: generateDailyStates({
      startDate: "2026-11-07",
      baseKs: 0.91,
      baseDepletion: 35,
      baseActualEt: 5.5,
      basePotentialEt: 6.0,
      avgRainfall: 5.0,
      avgIrrigation: 18,
      fieldCapacityMm: TURMERIC_FIELD_CAPACITY_MM,
      trend: "improving",
    }),
    viz3D: {
      vigor: 0.92,
      plantHeight: 0.70,
      canopyCoverage: 0.88,
      geometryType: "broadleaf",
      leafColor: "#2d7a1a",
      showStressMarkers: false,
    },
  },
  comparisonMetrics: [
    { name: "waterStressKs",         unit: "dimensionless", branchA: 0.75, branchB: 0.91, differenceBMinusA: +0.16, higherIsBetter: true  },
    { name: "rootZoneDepletionMm",   unit: "mm",            branchA: 65,   branchB: 35,   differenceBMinusA: -30,   higherIsBetter: false },
    { name: "actualEtMm",            unit: "mm/day",        branchA: 4.5,  branchB: 5.5,  differenceBMinusA: +1.0,  higherIsBetter: true  },
    { name: "canopyCoverage",        unit: "fraction",      branchA: 0.60, branchB: 0.88, differenceBMinusA: +0.28, higherIsBetter: true  },
    { name: "vigor",                 unit: "index",         branchA: 0.65, branchB: 0.92, differenceBMinusA: +0.27, higherIsBetter: true  },
  ],
  experimentTemplates: EXPERIMENT_TEMPLATES,
};

// ---------------------------------------------------------------------------
// Exported dataset
// ---------------------------------------------------------------------------

export const DEMO_SCENARIO_DATASET: DemoScenarioDataset = {
  version: "1.0.0",
  generatedAt: "2026-11-14",
  crops: [maize, wheat, turmeric],
};

/** Convenience lookup by canonical name (case-insensitive). */
export function getDemoCrop(name: string): DemoCrop | undefined {
  return DEMO_SCENARIO_DATASET.crops.find(
    (c) => c.canonicalName.toLowerCase() === name.toLowerCase() ||
           c.cropId.toLowerCase() === name.toLowerCase(),
  );
}

export { EXPERIMENT_TEMPLATES };
