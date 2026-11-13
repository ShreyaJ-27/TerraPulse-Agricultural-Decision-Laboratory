import type { Locale } from "./i18n";

export const cropNames = ["Rice", "Maize", "Turmeric", "Millet", "Groundnut", "Tomato"] as const;
export type CropName = typeof cropNames[number];
export type Channel = "inApp" | "whatsapp" | "sms";
export type Preferences = Record<Channel, boolean>;
export type CropPlan = {
  id: string;
  crop: CropName;
  plot: string;
  date: string;
  certainty: "estimated" | "confirmed";
  cycle: number;
  harvested: string | null;
  example?: boolean;
};
export type Draft = {
  name: string;
  district: string;
  language: Locale;
  crops: CropName[];
  date: string;
  certainty: CropPlan["certainty"];
  preferences: Preferences;
};
type AdvisoryState = "read" | "unread" | "dismissed";
export type FarmPlan = {
  version: 1;
  draft: Draft;
  profile: Omit<Draft, "crops" | "date" | "certainty"> | null;
  plots: CropPlan[];
  marks: Record<string, AdvisoryState>;
  forecastRevision: boolean;
  decisions: Record<string, { option: "current" | "alternative"; date: string }>;
};
const storageKey = "terrapulse-farmer-plan-v1";
export const defaultPreferences: Preferences = { inApp: false, whatsapp: false, sms: false };
export const farmToday = () => new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Kolkata" }).format(new Date());
const dayMs = 86_400_000;
const asTime = (date: string) => Date.parse(date + "T00:00:00Z");
const offset = (date: string, days: number) => new Date(asTime(date) + days * dayMs).toISOString().slice(0, 10);
export const dateLabel = (date: string) => new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeZone: "UTC" }).format(asTime(date));
export const validDate = (date: string) => /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(asTime(date)) && offset(date, 0) === date && date >= "1900-01-01" && date <= "2100-12-31";
export const newCrop = (crop: CropName, plot: string, date = "", certainty: CropPlan["certainty"] = "estimated"): CropPlan => ({
  id: Array.from(window.crypto.getRandomValues(new Uint8Array(12)), (byte) => byte.toString(16).padStart(2, "0")).join(""), crop, plot, date, certainty, cycle: 1, harvested: null,
});

function blankPlan(): FarmPlan {
  return {
    version: 1,
    draft: { name: "", district: "", language: "en", crops: [], date: "", certainty: "estimated", preferences: { ...defaultPreferences } },
    profile: null,
    plots: [],
    marks: {},
    forecastRevision: false,
    decisions: {},
  };
}

export const localFarmAdapter = {
  load(): FarmPlan {
    try {
      const saved = JSON.parse(window.localStorage.getItem(storageKey) || "null") as FarmPlan | null;
      if (saved?.version === 1 && saved.draft?.preferences && Array.isArray(saved.plots) && saved.marks && saved.decisions) return saved;
    } catch {
      // Storage may be unavailable or contain an unreadable draft.
    }
    return blankPlan();
  },
  save(plan: FarmPlan) {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(plan));
      return true;
    } catch {
      return false;
    }
  },
};

export function visiblePlots(plan: FarmPlan, today: string): CropPlan[] {
  if (plan.profile) return plan.plots;
  return [
    { id: "example-rice", crop: "Rice", plot: "River plot", date: offset(today, -18), certainty: "confirmed", harvested: null, cycle: 1, example: true },
    { id: "example-turmeric", crop: "Turmeric", plot: "East plot", date: offset(today, 4), certainty: "estimated", harvested: null, cycle: 1, example: true },
  ];
}

export type AdvisoryKind = "Planting window" | "Irrigation review" | "Forecast change" | "Cultivation milestone" | "Season transition" | "Future Fold";
export type Advisory = {
  id: string;
  kind: AdvisoryKind;
  urgency: "Review soon" | "Plan ahead";
  crop: CropPlan;
  reason: string;
  source: string;
  date: string;
  action: string;
  topic?: string;
};
export function generateAdvisories(plan: FarmPlan, plots: CropPlan[], today: string): Advisory[] {
  const cards: Advisory[] = [];
  for (const crop of plots) {
    const dated = validDate(crop.date);
    const age = dated ? (asTime(today) - asTime(crop.date)) / dayMs : null;
    const id = crop.id + "-" + crop.cycle;
    const source = crop.example ? "Example farm plan" : "Saved farm plan";
    const add = (kind: AdvisoryKind, key: string, urgency: Advisory["urgency"], reason: string, evidence: string, date: string, action: string, topic?: string) =>
      cards.push({ id: id + "-" + key, kind, urgency, crop, reason, source: evidence, date, action, topic });
    if (crop.harvested) {
      add("Season transition", "harvest", "Plan ahead", "You marked this crop harvested.", source, crop.harvested, "Record what worked and plan the next cultivation cycle.");
      continue;
    }
    if (age !== null && age >= -7 && age <= 0) {
      add("Planting window", "plant-" + crop.date, "Review soon", "Your " + crop.certainty + " planting date is within the next seven days.", source, crop.date, "Check seed and field readiness before confirming the date.");
    }
    if (age === null || age >= 0) {
      add("Irrigation review", "water", "Review soon", age === null ? "No planting date is saved yet. A field check can help you plan your next decision." : "This crop is on your active farm plan.", source + " · field-check reminder", dated ? (age === 0 ? crop.date : today) : today, "Check soil moisture in the plot before deciding whether to irrigate.");
    }
    if (plan.forecastRevision || crop.example) {
      add("Forecast change", "forecast", "Review soon", "The example forecast moved the expected shower one day later.", "Example forecast · illustrative", today, "Compare checking the field today with waiting for the forecast to update.");
    }
    if (age !== null && age >= 14) {
      add("Cultivation milestone", "check-" + crop.date, "Plan ahead", "At least two weeks have passed since your " + crop.certainty + " planting date.", source + " · 14-day reminder", offset(crop.date, 14), "Walk the plot and record any emergence or establishment issues.");
    }
    for (const topic of ["water", "planting", "field-check"]) {
      const decision = plan.decisions[id + "-" + topic];
      if (decision) {
        add("Future Fold", "revisit-" + topic, "Plan ahead", "You saved an example option for this crop cycle.", "Saved Future Fold example", decision.date, "Reopen the comparison and review the assumptions with your field notes.", topic);
      }
    }
  }
  return cards.sort((a, b) => Number(b.urgency === "Review soon") - Number(a.urgency === "Review soon"));
}

export function scenarioTopic(kind?: AdvisoryKind) {
  if (kind === "Planting window" || kind === "Season transition") return "planting";
  if (kind === "Cultivation milestone") return "field-check";
  return "water";
}

export const advisoryUrl = (card: Advisory) => "/advisories/" + card.id;
export const foldUrl = (plot: CropPlan, kind?: AdvisoryKind, topic?: string) => "/future-fold/" + plot.id + "/" + (topic || scenarioTopic(kind));

export const messageCopy = {
  en: { title: "TerraPulse farm update", next: "Review this crop advisory in TerraPulse.", view: "View advisory", explore: "Explore options", categories: ["Planting window", "Irrigation review", "Forecast change", "Cultivation milestone", "Season transition", "Future Fold"] },
  hi: { title: "TerraPulse खेत अपडेट", next: "TerraPulse में इस फसल की सलाह देखें।", view: "सलाह देखें", explore: "विकल्प देखें", categories: ["बुवाई का समय", "सिंचाई की समीक्षा", "मौसम पूर्वानुमान में बदलाव", "फसल की प्रगति", "अगले मौसम की तैयारी", "Future Fold"] },
  kn: { title: "TerraPulse ಕೃಷಿ ಮಾಹಿತಿ", next: "TerraPulse ನಲ್ಲಿ ಈ ಬೆಳೆಯ ಸಲಹೆಯನ್ನು ನೋಡಿ.", view: "ಸಲಹೆ ನೋಡಿ", explore: "ಆಯ್ಕೆಗಳನ್ನು ನೋಡಿ", categories: ["ಬಿತ್ತನೆಯ ಸಮಯ", "ನೀರಾವರಿ ಪರಿಶೀಲನೆ", "ಹವಾಮಾನ ಮುನ್ಸೂಚನೆಯಲ್ಲಿ ಬದಲಾವಣೆ", "ಬೆಳೆಯ ಪ್ರಗತಿ", "ಮುಂದಿನ ಋತುವಿನ ಸಿದ್ಧತೆ", "Future Fold"] },
};
export const advisoryKinds: AdvisoryKind[] = ["Planting window", "Irrigation review", "Forecast change", "Cultivation milestone", "Season transition", "Future Fold"];
