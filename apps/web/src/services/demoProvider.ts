/**
 * TerraPulse Demo Scenario Provider
 * Provides deterministic demonstration scenarios when backend simulation results
 * are unavailable or when exploring alternative agricultural futures.
 */
import {
  getDemoCrop,
  DemoCrop,
  ScenarioBranch,
  ComparisonMetric,
  ExperimentTemplate,
  Viz3DParams,
  EXPERIMENT_TEMPLATES,
} from "./demoScenarios";

export interface PreparedFutureFoldScenario {
  cropId: string;
  cropName: string;
  isDemo: boolean;
  baseline: {
    label: string;
    strategy: string;
    sowingDate: string;
    ks: number;
    depletionMm: number;
    actualEt: number;
    viz: Viz3DParams;
  };
  alternative: {
    label: string;
    strategy: string;
    sowingDate: string;
    ks: number;
    depletionMm: number;
    actualEt: number;
    viz: Viz3DParams;
  };
  metrics: ComparisonMetric[];
  experiments: ExperimentTemplate[];
  interpretation: {
    waterUsageComparison: string;
    cropDevelopmentComparison: string;
    soilMoistureTrajectory: string;
    recommendedObjective: "crop" | "water" | "balance";
    recommendationText: string;
  };
}

export function getPreparedDemoScenario(
  cropType: string,
  activeExperimentId?: string,
  sowingOffsetDays: number = 0,
  irrigationChangePct: number = 0
): PreparedFutureFoldScenario {
  const crop: DemoCrop = getDemoCrop(cropType) || getDemoCrop("maize")!;

  let altKs = crop.alternative.waterStressKs;
  let altDepletion = crop.alternative.rootZoneDepletionMm;
  let altActualEt = crop.alternative.actualEtMmPerDay;
  let altVigor = crop.alternative.viz3D.vigor;
  let altHeight = crop.alternative.viz3D.plantHeight;
  let altCanopy = crop.alternative.viz3D.canopyCoverage;
  let altStrategy = crop.alternative.irrigationStrategy;

  // Apply experiment template modifications if provided
  if (activeExperimentId) {
    const exp = EXPERIMENT_TEMPLATES.find((e) => e.id === activeExperimentId);
    if (exp) {
      altKs = Math.min(0.98, Math.max(0.3, altKs + exp.effects.ksChange));
      altDepletion = Math.max(10, altDepletion * (1 + exp.effects.depletionChangePct / 100));
      altVigor = Math.min(1.0, Math.max(0.3, altVigor + exp.effects.ksChange * 0.8));
      altHeight = Math.min(1.0, Math.max(0.3, altHeight + (exp.effects.ksChange > 0 ? 0.1 : -0.1)));
      altCanopy = Math.min(0.95, Math.max(0.3, altCanopy + (exp.effects.ksChange > 0 ? 0.08 : -0.08)));
      altStrategy = exp.label;
    }
  }

  // Apply custom sliders
  if (sowingOffsetDays !== 0) {
    const shift = -sowingOffsetDays * 0.005;
    altKs = Math.min(0.98, Math.max(0.3, altKs + shift));
    altDepletion = Math.max(10, altDepletion * (1 - shift * 0.8));
  }
  if (irrigationChangePct !== 0) {
    const shift = (irrigationChangePct / 100) * 0.12;
    altKs = Math.min(0.98, Math.max(0.3, altKs + shift));
    altDepletion = Math.max(10, altDepletion * (1 - shift * 1.2));
    altActualEt = Math.max(2.0, altActualEt * (1 + (irrigationChangePct / 100) * 0.15));
  }

  // Derived metrics
  const metrics: ComparisonMetric[] = [
    {
      name: "Water Stress Coefficient (Ks)",
      unit: "dimensionless",
      branchA: crop.original.waterStressKs,
      branchB: parseFloat(altKs.toFixed(2)),
      differenceBMinusA: parseFloat((altKs - crop.original.waterStressKs).toFixed(2)),
      higherIsBetter: true,
    },
    {
      name: "Root-zone Depletion",
      unit: "mm",
      branchA: crop.original.rootZoneDepletionMm,
      branchB: parseFloat(altDepletion.toFixed(1)),
      differenceBMinusA: parseFloat((altDepletion - crop.original.rootZoneDepletionMm).toFixed(1)),
      higherIsBetter: false,
    },
    {
      name: "Actual Evapotranspiration (ETa)",
      unit: "mm/day",
      branchA: crop.original.actualEtMmPerDay,
      branchB: parseFloat(altActualEt.toFixed(1)),
      differenceBMinusA: parseFloat((altActualEt - crop.original.actualEtMmPerDay).toFixed(1)),
      higherIsBetter: true,
    },
    {
      name: "Canopy Coverage",
      unit: "%",
      branchA: Math.round(crop.original.viz3D.canopyCoverage * 100),
      branchB: Math.round(altCanopy * 100),
      differenceBMinusA: Math.round((altCanopy - crop.original.viz3D.canopyCoverage) * 100),
      higherIsBetter: true,
    },
    {
      name: "Biomass & Plant Vigor",
      unit: "index (0-1)",
      branchA: crop.original.viz3D.vigor,
      branchB: parseFloat(altVigor.toFixed(2)),
      differenceBMinusA: parseFloat((altVigor - crop.original.viz3D.vigor).toFixed(2)),
      higherIsBetter: true,
    },
  ];

  const ksImprovement = altKs - crop.original.waterStressKs;
  const depletionDelta = altDepletion - crop.original.rootZoneDepletionMm;

  return {
    cropId: crop.cropId,
    cropName: crop.canonicalName,
    isDemo: true,
    baseline: {
      label: crop.original.label,
      strategy: crop.original.irrigationStrategy,
      sowingDate: crop.original.sowingDate,
      ks: crop.original.waterStressKs,
      depletionMm: crop.original.rootZoneDepletionMm,
      actualEt: crop.original.actualEtMmPerDay,
      viz: crop.original.viz3D,
    },
    alternative: {
      label: crop.alternative.label,
      strategy: altStrategy,
      sowingDate: crop.alternative.sowingDate,
      ks: parseFloat(altKs.toFixed(2)),
      depletionMm: parseFloat(altDepletion.toFixed(1)),
      actualEt: parseFloat(altActualEt.toFixed(1)),
      viz: {
        ...crop.alternative.viz3D,
        vigor: parseFloat(altVigor.toFixed(2)),
        plantHeight: parseFloat(altHeight.toFixed(2)),
        canopyCoverage: parseFloat(altCanopy.toFixed(2)),
      },
    },
    metrics,
    experiments: EXPERIMENT_TEMPLATES,
    interpretation: {
      waterUsageComparison:
        depletionDelta < 0
          ? `Alternative future maintains ${Math.abs(Math.round(depletionDelta))} mm lower root-zone water depletion, preserving crucial subsoil moisture.`
          : `Alternative future uses additional water reserve, leading to slightly higher depletion.`,
      cropDevelopmentComparison:
        ksImprovement > 0
          ? `Alternative future increases water availability coefficient (Ks) by +${ksImprovement.toFixed(2)}, accelerating vegetative development and canopy formation.`
          : `Crop development experiences moderate water deficit under this management profile.`,
      soilMoistureTrajectory:
        `Under ${crop.canonicalName} field capacity (350 mm root zone depth), baseline reaches wilting threshold 12 days earlier than the alternative management future.`,
      recommendedObjective: ksImprovement > 0.05 ? "crop" : "water",
      recommendationText:
        ksImprovement > 0.05
          ? `The Alternative Future strongly outperforms the baseline in vegetative development and stress resilience (+${Math.round(ksImprovement * 100)}% Ks gain) with acceptable water drawdown.`
          : `The Baseline Future conserves water reserves with lower operational investment, suitable if severe drought persists.`,
    },
  };
}
