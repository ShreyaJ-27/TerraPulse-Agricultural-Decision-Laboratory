export type * from "./advisory";

export type UUID = string;
export type ISODate = string;
export type ISODateTime = string;
export type DataStatus = "available" | "missing" | "invalid" | "unsupported";
export type Availability = { status: DataStatus; reason?: string };
export type Measurement = { value?: number; unit: string; availability: Availability };
export type Provenance = {
  sourceId: string;
  sourceVersion?: string;
  retrievedAt: ISODateTime;
  reference?: string;
};
export type Coordinates = { latitude: number; longitude: number; crs: "EPSG:4326" };
export type Geometry = { type: "Polygon" | "MultiPolygon"; coordinates: number[][][][] };

export interface DailyWeather {
  date: ISODate;
  temperatureMinC: Measurement;
  temperatureMaxC: Measurement;
  rainfallMm: Measurement;
  referenceEvapotranspirationMm?: Measurement;
  ensembleMemberId?: string;
}

export interface C1EnvironmentalInput {
  contractVersion: "1.0";
  farmId: UUID;
  location: Coordinates;
  timezone: string;
  simulationPeriod: { startDate: ISODate; endDate: ISODate };
  dailyWeather: DailyWeather[];
  soil: {
    depthCm: Measurement;
    texture?: string;
    fieldCapacity: Measurement;
    wiltingPoint: Measurement;
    bulkDensity?: Measurement;
  };
  dataSourceIds: string[];
  retrievedAt: ISODateTime;
  availability: Availability;
  provenance: Provenance[];
}

export interface C2FarmDefinition {
  contractVersion: "1.0";
  farmId: UUID;
  farmName: string;
  location: Coordinates;
  boundary?: Geometry;
  timezone: string;
  plots: Array<{
    plotId: UUID;
    areaM2: Measurement;
    geometry?: Geometry;
    cropId?: UUID;
    plantingDate?: ISODate;
    management?: Record<string, unknown>;
    sharedResourceIds: UUID[];
  }>;
}

export interface C3ScientificState {
  contractVersion: "1.0";
  farmId: UUID;
  plotId: UUID;
  branchId: UUID;
  simulationRunId: UUID;
  date: ISODate;
  engine: { name: string; version: string };
  soilWater: Measurement;
  rootZone: Measurement;
  cropWaterDemand: Measurement;
  actualEvapotranspiration: Measurement;
  waterStress: Measurement;
  irrigation: Measurement;
  rainfall: Measurement;
  drainage: Measurement;
  runoff: Measurement;
  biomass?: Measurement;
  yield?: Measurement;
  availability: Availability;
  provenance: Provenance[];
}

export interface C4BranchDecision {
  contractVersion: "1.0";
  branchId: UUID;
  parentBranchId?: UUID;
  baseSnapshotHash: string;
  effectiveDate: ISODate;
  weatherMemberId?: string;
  managementDecisions: Record<string, unknown>;
  changedPlantingDate?: ISODate;
  changedIrrigation?: Measurement;
  changedCropId?: UUID;
  modelVersion: string;
  inputHashes: string[];
  createdAt: ISODateTime;
}

export interface C5Comparison {
  contractVersion: "1.0";
  branchA: UUID;
  branchB: UUID;
  comparisonDate: ISODate;
  matchedInputs: boolean;
  metrics: Array<{
    metric: string;
    valueA: Measurement;
    valueB: Measurement;
    difference: Measurement;
  }>;
  availability: Availability;
  assumptions: string[];
  provenance: Provenance[];
}

export interface C6VisualState {
  contractVersion: "1.0";
  plotId: UUID;
  branchId: UUID;
  date: ISODate;
  cropVisualIdentity: string;
  growthPresentation: Record<string, unknown>;
  soilLayerPresentation: Record<string, unknown>;
  scientificStateReference: UUID;
  interpolation: { enabled: boolean; method?: string; sourceDates: ISODate[] };
}

export interface C7ModelCapability {
  contractVersion: "1.0";
  cropId: UUID;
  acceptedCropNames: string[];
  scientificName?: string;
  selectedEngine: "AquaCrop" | "FAO-56" | "identity/ecology-only";
  engineVersion: string;
  supportedOutputs: string[];
  modelParameters: Record<string, number | string>;
  parameterSources: Provenance[];
  parameterVersions: string[];
  knownLimitations: string[];
  provenanceReferences: Provenance[];
}

export interface C8ResourceLedger {
  contractVersion: "1.0";
  farmId: UUID;
  branchId: UUID;
  resourceId: UUID;
  unit: string;
  openingVolume: Measurement;
  plotAllocations: Array<{ plotId: UUID; requestedAmount: Measurement; withdrawnAmount: Measurement; effectiveAmount: Measurement }>;
  losses: Measurement;
  closingVolume: Measurement;
  accountingValidation: { isValid: boolean; difference: Measurement };
  errors: string[];
}

export interface ApiResponse<T> { data: T; correlationId: string; contractVersion: "1.0"; }
export interface ApiError {
  error: { code: string; message: string; fields?: Record<string, string[]> };
  correlationId: string;
  contractVersion: "1.0";
}
