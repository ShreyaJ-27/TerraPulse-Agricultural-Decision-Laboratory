import type { ISODate, ISODateTime, UUID } from "./index";

export type AdvisoryPlantingDate =
  | { kind: "farmer_confirmed"; date: ISODate }
  | { kind: "farmer_estimated"; date: ISODate }
  | { kind: "unconfirmed"; date: null };

export interface RegionalPlantingWindow {
  kind: "typical_regional_window";
  operation: "direct_sowing";
  label: string;
  applicability: string;
  sourceSection: string;
}

export interface AdvisoryCropProfile {
  schemaVersion: "1.0";
  regionId: string;
  status: "regional_context_available" | "region_unsupported" | "crop_context_unavailable";
  crop: {
    cropId: UUID;
    canonicalName: string;
    scientificName: string;
    family: string;
    aliases: string[];
  };
  regionalContext: {
    season: "kharif" | "rabi";
    summary: string;
    source: {
      publisher: string;
      title: string;
      edition: string;
      publishedMonth: string;
      reviewedOn: ISODate;
      url: string;
    };
    plantingWindow: RegionalPlantingWindow;
    milestones: {
      id: string;
      label: string;
      definition: string;
      sourceSection: string;
      definitionUrl: string | null;
    }[];
  } | null;
  capabilities: {
    regionalPlantingWindow: boolean;
    cultivationMilestones: boolean;
    numericalIrrigationAdvice: false;
    harvestDatePrediction: false;
    yieldPrediction: false;
    simulation: false;
  };
}

export interface AdvisoryCropResponse {
  data: AdvisoryCropProfile;
  correlationId: string;
  contractVersion: "1.0";
}

type WeatherEventSource =
  | {
      kind: "forecast" | "observation";
      provider: string;
      issuedAt: ISODateTime;
      referenceUrl?: string;
    }
  | { kind: "synthetic_fixture"; fixtureId: string };

export interface AdvisoryWeatherEvent {
  eventId: string;
  regionId: string;
  farmId?: UUID;
  type: "rain" | "heat" | "cold" | "wind" | "other";
  title: string;
  startsAt: ISODateTime;
  endsAt: ISODateTime;
  source: WeatherEventSource;
}

export interface AdvisoryDemoFixture {
  fixtureId: string;
  regionId: "IN-PB";
  timezone: "Asia/Kolkata";
  profiles: AdvisoryCropProfile[];
  weatherEvents: AdvisoryWeatherEvent[];
}
