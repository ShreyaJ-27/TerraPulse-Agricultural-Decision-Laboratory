export class ApiError extends Error {
  constructor(public readonly status: number, public readonly code: string, message: string, public readonly fields?: Record<string, string[]>) {
    super(message);
  }
}

const baseUrl = (import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? "http://localhost:8000" : "")).replace(/\/$/, "");

function workspaceKey(): string {
  const keyName = "terrapulse-workspace-key";
  const existing = window.localStorage.getItem(keyName);
  if (existing && /^[a-f0-9]{64}$/.test(existing)) return existing;
  const bytes = window.crypto.getRandomValues(new Uint8Array(32));
  const generated = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  window.localStorage.setItem(keyName, generated);
  return generated;
}

export async function api<T>(path: string, init?: Parameters<typeof window.fetch>[1]): Promise<T> {
  let key: string;
  try {
    key = workspaceKey();
  } catch {
    throw new ApiError(0, "STORAGE_UNAVAILABLE", "Allow browser storage to use your private farm workspace.");
  }
  const correlationId = window.crypto.randomUUID();
  let response: Awaited<ReturnType<typeof window.fetch>>;
  try {
    response = await window.fetch(`${baseUrl}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", "X-Correlation-ID": correlationId, Authorization: `Bearer ${key}`, ...(init?.headers || {}) },
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "The TerraPulse API could not be reached.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = body.error || {};
    const detail = body.detail || {};
    throw new ApiError(response.status, error.code || detail.code || "HTTP_ERROR", error.message || (typeof detail === "string" ? detail : detail.message) || "The request failed.", error.fields);
  }
  return (body.data ?? body) as T;
}

export const apiClient = {
  listFarms: () => api<{ farms: Farm[]; total: number }>("/api/v1/farms"),
  redeemFarmOpenLink: (token: string) => api<{ farmIds: string[]; total: number }>("/api/v1/workspace-link/redeem", { method: "POST", body: JSON.stringify({ token }) }),
  getCalendar: (farmId: string) => api<{ asOfDate: string; plots: CalendarPlot[] }>(`/api/v1/agri-calendar/farms/${farmId}`),
  issueTelegramLink: (farmId: string) => api<{ telegramConnectUrl: string }>(`/api/v1/farms/${farmId}/telegram-link`, { method: "POST" }),
  getPitchAlertStatus: (farmId: string) => api<{ available: boolean; connected?: boolean; cooldownSeconds?: number }>(`/api/v1/farms/${farmId}/pitch-alert`),
  sendPitchAlert: (farmId: string, requestId: string) => api<{ sent: boolean; receiptId: string; telegramMessageId?: number }>(`/api/v1/farms/${farmId}/pitch-alert`, { method: "POST", body: JSON.stringify({ requestId }) }),
  getFarm: (id: string) => api<Farm>(`/api/v1/farms/${id}`),
  createFarm: (value: unknown) => api<Farm>("/api/v1/farms", { method: "POST", body: JSON.stringify(value) }),
  createPlot: (farmId: string, value: unknown) => api<Plot>(`/api/v1/farms/${farmId}/plots`, { method: "POST", body: JSON.stringify(value) }),
  confirmPlantingDate: (farmId: string, plotId: string, plantingDate: string) =>
    api<Plot>(`/api/v1/farms/${farmId}/plots/${plotId}/planting-date`, {
      method: "PATCH", body: JSON.stringify({ plantingDate }),
    }),
  listResources: (farmId: string) => api<{ resources: Resource[] }>(`/api/v1/farms/${farmId}/resources`),
  createResource: (farmId: string, value: unknown) => api<Resource>(`/api/v1/farms/${farmId}/resources`, { method: "POST", body: JSON.stringify(value) }),
  assignResourcePlot: (farmId: string, resourceId: string, plotId: string) => api<unknown>(`/api/v1/farms/${farmId}/resources/${resourceId}/plots/${plotId}`, { method: "POST" }),
  resolveCrop: (query: string) => api<CropResolution>(`/api/v1/crops/resolve?q=${encodeURIComponent(query)}`),
  prepareEnvironment: (value: unknown) => api<Environment>(`/api/v1/environment/prepare`, { method: "POST", body: JSON.stringify(value) }),
  listSimulations: (farmId: string, plotId: string) => api<{ simulations: Simulation[]; total: number }>(`/api/v1/farms/${farmId}/plots/${plotId}/simulations`),
  getSimulation: (id: string) => api<Simulation>(`/api/v1/simulations/${id}`),
  submitSimulation: (value: unknown) => api<{ simulationRunId: string; status: string }>("/api/v1/simulations", { method: "POST", body: JSON.stringify(value) }),
  listBranches: (farmId: string, plotId: string) => api<{ branches: Branch[] }>(`/api/v1/farms/${farmId}/plots/${plotId}/branches`),
  createBranch: (farmId: string, plotId: string, value: unknown) => api<Branch>(`/api/v1/farms/${farmId}/plots/${plotId}/branches`, { method: "POST", body: JSON.stringify(value) }),
  getTimeline: (farmId: string, plotId: string) => api<{ events: TimelineEvent[] }>(`/api/v1/farms/${farmId}/plots/${plotId}/timeline`),
  getScientificState: (farmId: string, plotId: string, branchId: string, date: string) => api<ScientificState>(`/api/v1/farms/${farmId}/plots/${plotId}/scientific-states?branch_id=${branchId}&state_date=${date}`),
  listComparisons: (farmId: string, plotId: string) => api<{ comparisons: Comparison[] }>(`/api/v1/farms/${farmId}/plots/${plotId}/comparisons`),
  createComparison: (farmId: string, plotId: string, value: unknown) => api<Comparison>(`/api/v1/farms/${farmId}/plots/${plotId}/comparisons`, { method: "POST", body: JSON.stringify(value) }),
  interactCrop: (payload: { query: string; language: "en" | "kn" | "hi" }) =>
    api<CropInteraction>("/api/v1/crops/interact", { method: "POST", body: JSON.stringify(payload) }),
  analyzeFarm: (payload: AnalysisRequest) =>
    api<AnalysisResult>("/api/v1/analysis", { method: "POST", body: JSON.stringify(payload) }),
  listNotifications: (farmId: string) =>
    api<{ farmId: string; notifications: any[]; total: number }>(`/api/v1/notifications/farms/${farmId}`),
  getTelegramStatus: (farmId: string) =>
    api<{ farmId: string; connected: boolean; botUsername: string; subscriptionCount: number; subscriptions: any[] }>(`/api/v1/notifications/telegram/status/${farmId}`),
  getDeliveries: (farmId: string) =>
    api<{ farmId: string; deliveries: any[]; total: number }>(`/api/v1/notifications/deliveries/${farmId}`),
  getAgriCalendarSeasons: () =>
    api<{ seasons: any[]; total: number }>("/api/v1/agri-calendar/seasons"),
  getAgriCalendarRegional: (regionId: string) =>
    api<{ regionId: string; profiles: any[]; total: number }>(`/api/v1/agri-calendar/regional/${regionId}`),
  getAgriCalendarForFarm: (farmId: string) =>
    api<{ farmId: string; asOfDate: string; plots: any[]; total: number; seasons: any[] }>(`/api/v1/agri-calendar/farms/${farmId}`),
  getAdvisory: (regionId: string, cropId: string) =>
    api<any>(`/api/v1/advisory/regions/${regionId}/crops/${cropId}`),
  generateCustomCalendar: (payload: any) =>
    api<any>("/api/v1/agri-calendar/generate", { method: "POST", body: JSON.stringify(payload) }),
};

export type CropInteraction = {
  intent: string;
  language: string;
  resolutionStatus: string;
  resolvedCrop?: Crop;
  candidates?: Crop[];
  responseText: string;
  speechText: string;
  limitations: string[];
  escalationRequired: boolean;
  sources: string[];
};

export type Farm = { farmId: string; name: string; timezone: string; location: { latitude: number; longitude: number; crs: string }; plots: Plot[]; createdAt?: string };
export type Plot = { plotId: string; farmId: string; areaM2: { value: number; unit: string }; cropId: string; cropCanonicalName: string; cropScientificName?: string; plantingDate?: string; management?: { plotName?: string; regionId?: string; plantingDateCertainty?: string }; sharedResourceIds?: string[] };
export type CalendarPlot = {
  plotId: string;
  plotName: string;
  cropName: string;
  plantingDate: string | null;
  plantingCertainty: string;
  regionId: string | null;
  regionalGuidanceAvailable: boolean;
  regionalSource?: string;
  regionalSourceVersion?: string;
  regionalSourceUrl?: string;
  plantingWindowNote?: string;
  next31Days: { date: string; endDate?: string; title: string; action: string; source: string; sourceVersion?: string; certainty: string }[];
  undatedActivities: { title: string; guidance: string; source: string; sourceVersion?: string }[];
};
export type Resource = { resourceId: string; farmId: string; name: string; resourceType: string; unit: string; openingVolume: number; metadata?: Record<string, unknown>; createdAt?: string };
export type Crop = {
  cropId: string;
  canonicalName: string;
  scientificName?: string;
  family?: string;
  selectedEngine?: string;
  engineVersion?: string;
  supportedOutputs?: string[];
  matchedAlias?: string;
  matchType?: string;
};
export type CropResolution = { status: string; crop?: Crop; candidates?: Crop[]; message?: string };
export type Environment = { environmentalSnapshotId: string; c1Input?: { dailyWeather?: Weather[]; soil?: Soil; simulationPeriod?: { startDate: string; endDate: string } }; capability?: Capability; isValid: boolean; simulationBlocker?: { code: string; message: string } | null; freshness?: string; warnings?: string[]; errors?: string[]; missingFields?: string[]; unsupportedOutputs?: string[]; provenance?: { sourceId: string; sourceVersion?: string; retrievedAt?: string; reference?: string }[]; retrievedAt?: string };
export type Weather = { date: string; temperatureMinC: Measurement; temperatureMaxC: Measurement; rainfallMm: Measurement; referenceEvapotranspirationMm?: Measurement; ensembleMemberId?: string };
export type Soil = { depthCm: Measurement; texture?: string; fieldCapacity: Measurement; wiltingPoint: Measurement; bulkDensity?: Measurement };
export type Measurement = { value?: number; unit: string; availability: { status: string; reason?: string } };
export type Capability = { selectedEngine: string; engineVersion: string; supportedOutputs: string[]; knownLimitations: string[]; parameterVersions?: string[] };
export type Simulation = { simulationRunId: string; farmId: string; plotId: string; branchId: string; status: string; engine?: string; engineVersion?: string; parameterVersion?: string; environmentalSnapshotId?: string; weatherMemberId?: string; requestedAt?: string; completedAt?: string; warnings?: string[]; errorCode?: string; errorMessage?: string; states?: Record<string, unknown>[]; scienceEnvelope?: Record<string, unknown> };
export type Branch = { branchId: string; farmId: string; plotId: string; parentBranchId?: string; baseSnapshotHash: string; effectiveDate: string; decisionType: string; decisionDiff: Record<string, unknown>; modelVersion: string; weatherMemberId?: string; inputHashes: string[]; createdAt?: string };
export type TimelineEvent = { eventId: string; eventType: string; eventDate: string; branchId?: string; description: string; payload: Record<string, unknown>; createdAt?: string };
export type ScientificState = { farmId: string; plotId: string; branchId: string; simulationRunId: string; date: string; availability: string; state: Record<string, unknown>; provenance: { engine?: string; engineVersion?: string; parameterVersion?: string; environmentalSnapshotId?: string; inputHash: string; weatherRealizationId?: string; weatherMemberId?: string; warnings: string[]; visualInterpolation: { allowed: boolean; scientificValuesMutated: boolean; label: string } } };
export type Comparison = { comparisonId: string; farmId: string; plotId: string; baselineBranchId: string; alternativeBranchId: string; baselineRunId: string; alternativeRunId: string; comparisonDate: string; status: string; matchedInputs: boolean; reasons: string[]; payload: { result?: { daily?: { date: string; metrics: { name: string; unit: string; branchA: number; branchB: number; differenceBMinusA: number }[] }[]; metrics?: unknown[] }; provenance?: Record<string, unknown> } };
export type AnalysisRequest = {
  farmId: string;
  plotId: string;
  branchId?: string;
  comparisonBranchId?: string;
  comparisonId?: string;
  simulationRunId?: string;
  question: string;
  language: "en" | "kn" | "hi";
  includeWeather: boolean;
  includeSoil: boolean;
  includeCrop: boolean;
  includeSimulation: boolean;
  includeComparison: boolean;
};
export type GroundedClaim = {
  claimId: string;
  metric: string;
  value: number;
  unit: string;
  sourceField: string;
  sourceId: string;
  category: string;
  isStale: boolean;
  qualifications: string[];
};
export type AnalysisSection = { key: string; title: string; content: string; claims: GroundedClaim[] };
export type AnalysisResult = {
  analysisId: string;
  farmId: string;
  plotId: string;
  language: "en" | "kn" | "hi";
  summary: string;
  sections: AnalysisSection[];
  claims: GroundedClaim[];
  evidenceSummary: {
    farmId: string;
    plotId: string;
    cropCanonicalName: string;
    cropScientificName?: string;
    cropEngine: string;
    cropEngineVersion: string;
    c1Available: boolean;
    weatherDaysCount: number;
    soilAvailable: boolean;
    c3StatesCount: number;
    c5ComparisonAvailable: boolean;
    missingFields: string[];
    branchId?: string;
    simulationRunId?: string;
    simulationStatus?: string;
    simulationCompletedAt?: string;
    simulationEngine?: string;
    simulationEngineVersion?: string;
    parameterVersion?: string;
    simulationWarnings: string[];
    environmentalSnapshotId?: string;
    environmentalInputHash?: string;
    environmentalSource?: string;
    weatherMemberId?: string;
    comparisonId?: string;
    comparisonStatus?: string;
    comparisonMatchedInputs?: boolean;
    comparisonBaselineBranchId?: string;
    comparisonAlternativeBranchId?: string;
    comparisonBaselineRunId?: string;
    comparisonAlternativeRunId?: string;
    comparisonDate?: string;
    comparisonAssumptions: string[];
    comparisonProvenance: { sourceId: string; sourceVersion?: string; retrievedAt: string; reference?: string }[];
    comparisonReasons: string[];
    cropSupportedOutputs: string[];
    cropParameterVersions: string[];
    cropParameterSources: { sourceId: string; sourceVersion?: string; retrievedAt: string; reference?: string }[];
    cropLimitations: string[];
  };
  dataFreshness: { sourceId: string; dataType: string; isStale: boolean; ageHours?: number; freshnessLabel: string; warning?: string }[];
  scientificLimitations: { category: string; code: string; description: string; implications: string }[];
  escalations: { category: string; reason: string; recommendedAction: string; recommendedAuthority: string }[];
  guardrailStatus: { passed: boolean; flags: string[]; restrictedTopics: string[]; escalationRequired: boolean };
  generationMode: "deterministic" | "llm" | "deterministic_fallback";
  createdAt: string;
};
