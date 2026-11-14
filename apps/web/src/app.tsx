import { FarmerApp } from "./FarmerApp";
import { WorkspaceFeature, WorkspaceFeatures } from "./components/WorkspaceFeatures";
import { TelegramConnect } from "./components/TelegramConnect";
import { PitchAlertControl } from "./components/PitchAlertControl";
import { FarmOpenLink } from "./components/FarmOpenLink";
import { Component, ErrorInfo, ReactNode, useCallback, useEffect, useState } from "react";
import { AppShell, Route } from "./components/layout";
import { EmptyState, ErrorState, LoadingState, PageContainer, ReusableCard } from "./components/ui";
import { apiClient, ApiError, Crop, CropResolution, Environment, Farm, Simulation } from "./services/apiClient";
import { getInitialLocale, translations } from "./i18n";
import { FutureFold, Observatory, Timeline } from "./components/scenario";
import { ResourcePanel } from "./components/resources";
import { FarmerInteraction } from "./components/interaction";
import { LandingPage } from "./components/LandingPage";
import { AgriculturalDashboard } from "./components/AgriculturalDashboard";
import { type SylvaLivingWorldVariant } from "@designcodeio/threeui";

const routePath = () => window.location.pathname.replace(/\/+$/, "") || "/";
const readUrl = () => window.location.pathname + window.location.search;
function useNavigation() {
  const [, setUrl] = useState(readUrl);
  const path = routePath();
  useEffect(() => { const onPop = () => setUrl(readUrl()); window.addEventListener("popstate", onPop); return () => window.removeEventListener("popstate", onPop); }, []);
  const navigate = useCallback((next: string) => { window.history.pushState({}, "", next); setUrl(readUrl()); }, []);
  return { path, navigate };
}
const message = (error: unknown) => error instanceof ApiError ? error.message : "Something went wrong. Please retry.";

function FarmList({ navigate, copy }: { navigate: (path: string) => void; copy: typeof translations.en }) {
  const [farms, setFarms] = useState<Farm[]>(); const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    apiClient.listFarms()
      .then(({ farms }) => { if (active) setFarms(farms); })
      .catch((reason) => { if (active) setError(message(reason)); });
    return () => { active = false; };
  }, []);
  if (error) return <PageContainer><ErrorState label={error} /></PageContainer>;
  if (!farms) return <PageContainer><LoadingState label="Loading saved farms…" /></PageContainer>;
  return <PageContainer><div className="page-intro"><p className="eyebrow">01 / Registered farms</p><h2>Your farms</h2><p>Connect to persisted farm records and continue into a plot workspace.</p><div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}><button className="primary-button" onClick={() => navigate("/farms/new")}>Register New Farm <span>→</span></button><button className="secondary-button" onClick={() => navigate("/assisted")}>{copy.interactionTitle} <span>🎙</span></button></div></div>{farms.length === 0 ? <EmptyState title="No farms on this browser yet" description="Already registered? Send /open in your connected TerraPulse Telegram chat and tap the link to restore your saved farms. No re-registration needed." action={<button className="secondary-button" onClick={() => navigate("/farms/new")}>Register New Farm</button>} /> : <div className="card-grid">{farms.map((farm) => <button className="info-card farm-card" key={farm.farmId} onClick={() => navigate(`/farms/${farm.farmId}`)}><span className="card-number">{farm.plots.length} plots</span><h3>{farm.name}</h3><p>{farm.location.latitude.toFixed(4)}, {farm.location.longitude.toFixed(4)}</p><span className="card-link">Open farm ↗</span></button>)}</div>}</PageContainer>;
}

function FarmWizard({
  navigate,
  existingFarmId,
  atmosphere = "living-green",
}: {
  navigate: (path: string) => void;
  existingFarmId?: string;
  atmosphere?: SylvaLivingWorldVariant;
}) {
  const atmoClass =
    atmosphere === "sakura-sunset"
      ? "atmosphere-sakura"
      : atmosphere === "maple-autumn"
      ? "atmosphere-autumn"
      : atmosphere === "sequoia-mist"
      ? "atmosphere-mist"
      : "atmosphere-green";
  const firstStep = existingFarmId ? 3 : 1;
  const [step, setStep] = useState(firstStep);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [farmId, setFarmId] = useState(existingFarmId || "");
  const [farm, setFarm] = useState({
    name: "",
    timezone: "Asia/Kolkata",
    latitude: "",
    longitude: "",
    confirmed: false,
  });
  const [plot, setPlot] = useState({
    name: "",
    area: "10000",
    regionId: "",
    certainty: "confirmed",
    plantingDate: "",
    query: "",
    cropId: "",
    crop: undefined as Crop | undefined,
  });
  const [resolution, setResolution] = useState<CropResolution>();
  const [telegramPrompt, setTelegramPrompt] = useState<{ url: string; target: string } | null>(null);
  const [telegramUrl, setTelegramUrl] = useState<string | null>(null);

  const PRESET_LOCATIONS = [
    { name: "Ludhiana (PB) — PAU Agro Region", lat: 30.9010, lon: 75.8573, regionId: "IN-PB" },
    { name: "Mysuru (KA) — UAS Mysore Plateau", lat: 12.2958, lon: 76.6394, regionId: "" },
    { name: "Dharwad (KA) — UAS Dharwad", lat: 15.4589, lon: 75.0078, regionId: "" },
    { name: "Nashik (MH) — Deccan Black Soil", lat: 19.9975, lon: 73.7898, regionId: "" },
  ];

  const CROP_SUGGESTIONS = [
    { name: "Maize", label: "Maize (Corn)" },
    { name: "Turmeric", label: "Turmeric (Haldi)" },
    { name: "Wheat", label: "Wheat (Gehun)" },
    { name: "Rice", label: "Rice (Paddy)" },
    { name: "Cotton", label: "Cotton (Kapas)" },
  ];

  const updateFarm = (key: string, value: string | boolean) => setFarm((current) => ({ ...current, [key]: value }));

  const resolve = async (cropQuery?: string) => {
    const q = cropQuery || plot.query;
    if (!q.trim()) return;
    setError("");
    setPlot((prev) => ({ ...prev, query: q, cropId: "", crop: undefined }));
    try {
      const result = await apiClient.resolveCrop(q);
      setResolution(result);
      if (result.crop) {
        setPlot((prev) => ({ ...prev, query: q, cropId: result.crop!.cropId, crop: result.crop }));
      }
    } catch (e) {
      setResolution(undefined);
      setError(message(e));
    }
  };

  const selectPresetLocation = (name: string, lat: number, lon: number, regionId: string) => {
    setFarm((prev) => ({
      ...prev,
      name: prev.name || `${name.split(" — ")[0]} Farm`,
      latitude: String(lat),
      longitude: String(lon),
      confirmed: true,
    }));
    setPlot((prev) => ({ ...prev, regionId }));
  };

  const next = () => {
    setError("");
    if (step === 1 && !farm.name.trim()) return setError("Farm name is required.");
    if (step === 2 && (!farm.confirmed || !farm.latitude || !farm.longitude || Number(farm.latitude) < -90 || Number(farm.latitude) > 90 || Number(farm.longitude) < -180 || Number(farm.longitude) > 180)) return setError("Enter valid coordinates and explicitly confirm the farm location.");
    if (step === 3 && (!plot.area || Number(plot.area) <= 0)) return setError("Plot area must be positive.");
    if (step === 4 && !plot.cropId) return setError("Resolve and explicitly select a crop.");
    setStep(Math.min(5, step + 1));
  };

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      type RegisteredFarm = Farm & { telegramConnectUrl?: string };
      const saved: RegisteredFarm = farmId
        ? ({ farmId } as RegisteredFarm)
        : (await apiClient.createFarm({
            name: farm.name.trim(),
            timezone: farm.timezone,
            location: {
              latitude: Number(farm.latitude),
              longitude: Number(farm.longitude),
              crs: "EPSG:4326",
            },
            locationConfirmed: true,
          })) as RegisteredFarm;

      setFarmId(saved.farmId);
      window.localStorage.setItem("terrapulse-active-farm-id", saved.farmId);
      if (saved.telegramConnectUrl) {
        setTelegramUrl(saved.telegramConnectUrl);
      }

      await apiClient.createPlot(saved.farmId, {
        areaM2: { value: Number(plot.area) || 10000, unit: "m2" },
        cropId: plot.cropId,
        plantingDate: plot.plantingDate || null,
        management: {
          plotName: plot.name.trim() || undefined,
          regionId: plot.regionId || undefined,
          plantingDateCertainty: plot.plantingDate ? plot.certainty : "unconfirmed",
        },
      });

      const target = `/dashboard?farmId=${saved.farmId}&tab=overview`;
      const connectUrl = saved.telegramConnectUrl || telegramUrl;

      if (connectUrl) {
        setTelegramPrompt({ url: connectUrl, target });
      } else {
        navigate(target);
      }
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  };

  if (telegramPrompt) {
    return (
      <div className={`wizard-dark-wrap ${atmoClass}`} data-atmosphere={atmosphere}>
        <div className="wizard-dark-card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.2rem" }}>
            <span style={{ background: "rgba(134, 239, 172, 0.15)", color: "#86efac", padding: "4px 10px", borderRadius: "12px", fontSize: "0.78rem", fontWeight: 700 }}>
              REGISTRATION COMPLETE
            </span>
          </div>
          <h2 style={{ color: "#ffffff", margin: "0 0 0.5rem 0" }}>Farm & Plot Successfully Persisted</h2>
          <p style={{ color: "#b2c9b8", fontSize: "0.92rem", marginBottom: "1.5rem" }}>
            Your farm is live in TerraPulse. Connect your Telegram account to receive real-time soil moisture and frost alerts, or proceed directly to your decision workspace.
          </p>
          <TelegramConnect url={telegramPrompt.url} />
          <div style={{ marginTop: "1.5rem" }}>
            <button
              className="dock-cta-btn"
              style={{ width: "100%", padding: "12px", textAlign: "center", fontSize: "0.95rem" }}
              onClick={() => navigate(telegramPrompt.target)}
            >
              Open Farm Workspace ↗
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`wizard-dark-wrap ${atmoClass}`} data-atmosphere={atmosphere}>
      <div className="wizard-dark-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <button
            type="button"
            className="dock-item"
            style={{ padding: "6px 12px", fontSize: "0.82rem", background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", color: "#b5c7ba", cursor: "pointer" }}
            onClick={() => navigate("/")}
          >
            ← Back to Landing
          </button>
          <span style={{ fontSize: "0.8rem", color: "#7f9986" }}>
            Step {step} of 5
          </span>
        </div>

        <h2 style={{ color: "#ffffff", margin: "0.5rem 0 0.3rem 0", fontSize: "1.6rem" }}>
          {existingFarmId ? "Add a Crop Plot" : "Register Your Farm"}
        </h2>
        <p style={{ color: "#8fa896", fontSize: "0.88rem", margin: 0 }}>
          {existingFarmId
            ? "Configure a new plot under your persisted farm."
            : "Set up your farm profile, geographic coordinates, and initial crop plot."}
        </p>

        {/* Dark Stepper */}
        <div className="wizard-stepper-dark">
          {["Farm Details", "Location", "Plot Details", "Crop Selection", "Review"].map((label, i) => (
            <span
              key={label}
              className={`wizard-step-tag ${i + 1 === step ? "active" : i + 1 < step ? "done" : ""}`}
            >
              0{i + 1} {label} {i + 1 < step ? "✓" : ""}
            </span>
          ))}
        </div>

        {/* Wizard Step Content */}
        {step === 1 && (
          <div className="wizard-field-group">
            <label className="wizard-label">
              Farm Name
              <input
                className="wizard-input"
                placeholder="e.g. Sahyadri Agro Estate, Ludhiana Green Farm"
                value={farm.name}
                onChange={(e) => updateFarm("name", e.target.value)}
                maxLength={200}
              />
            </label>
            <label className="wizard-label">
              Timezone
              <select
                className="wizard-select"
                value={farm.timezone}
                onChange={(e) => updateFarm("timezone", e.target.value)}
              >
                <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                <option value="UTC">UTC</option>
                <option value="Asia/Dubai">Asia/Dubai (GST)</option>
              </select>
            </label>
          </div>
        )}

        {step === 2 && (
          <div className="wizard-field-group">
            <div>
              <span style={{ fontSize: "0.85rem", color: "#a2c98a", fontWeight: 600 }}>
                1-Click Regional Presets:
              </span>
              <div className="wizard-presets-grid">
                {PRESET_LOCATIONS.map((preset) => (
                  <button
                    key={preset.name}
                    type="button"
                    className="wizard-preset-btn"
                    onClick={() => selectPresetLocation(preset.name, preset.lat, preset.lon, preset.regionId)}
                  >
                    <strong>{preset.name}</strong>
                    <div style={{ fontSize: "0.74rem", color: "#8fa896" }}>
                      {preset.lat.toFixed(4)}°N, {preset.lon.toFixed(4)}°E
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              <label className="wizard-label">
                Latitude (°N)
                <input
                  type="number"
                  className="wizard-input"
                  placeholder="e.g. 30.9010"
                  value={farm.latitude}
                  onChange={(e) => updateFarm("latitude", e.target.value)}
                  min="-90"
                  max="90"
                  step="any"
                />
              </label>
              <label className="wizard-label">
                Longitude (°E)
                <input
                  type="number"
                  className="wizard-input"
                  placeholder="e.g. 75.8573"
                  value={farm.longitude}
                  onChange={(e) => updateFarm("longitude", e.target.value)}
                  min="-180"
                  max="180"
                  step="any"
                />
              </label>
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: "0.6rem", color: "#c5d8ca", fontSize: "0.88rem", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={farm.confirmed}
                onChange={(e) => updateFarm("confirmed", e.target.checked)}
              />
              <span>I confirm these coordinates represent the verified farm location.</span>
            </label>

            <button
              className="dock-item"
              type="button"
              style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", padding: "8px 14px", borderRadius: "6px", color: "#c5d8ca", fontSize: "0.84rem", cursor: "pointer", width: "fit-content" }}
              onClick={() =>
                window.navigator.geolocation?.getCurrentPosition(
                  (p) => {
                    updateFarm("latitude", String(p.coords.latitude));
                    updateFarm("longitude", String(p.coords.longitude));
                    updateFarm("confirmed", true);
                  },
                  () => setError("Location permission was denied or unavailable.")
                )
              }
            >
              📍 Use Device Geolocation
            </button>
          </div>
        )}

        {step === 3 && (
          <div className="wizard-field-group">
            <label className="wizard-label">
              Plot Name (Optional)
              <input
                className="wizard-input"
                maxLength={80}
                placeholder="e.g. North Acre 1"
                value={plot.name}
                onChange={(e) => setPlot({ ...plot, name: e.target.value })}
              />
            </label>
            <label className="wizard-label">
              Advisory Region
              <select
                className="wizard-select"
                value={plot.regionId}
                onChange={(e) => setPlot({ ...plot, regionId: e.target.value })}
              >
                <option value="">Other or General Region</option>
                <option value="IN-PB">Punjab, India (PAU Package of Practices)</option>
                <option value="IN-KA">Karnataka, India (UAS Package of Practices)</option>
                <option value="IN-MH">Maharashtra, India (Deccan Agro-Climatic)</option>
              </select>
            </label>
            <label className="wizard-label">
              Plot Area (m²)
              <input
                type="number"
                className="wizard-input"
                value={plot.area}
                onChange={(e) => setPlot({ ...plot, area: e.target.value })}
                min="1"
                step="any"
              />
              <span style={{ fontSize: "0.76rem", color: "#8fa896" }}>10,000 m² = 1 Hectare ≈ 2.47 Acres</span>
            </label>
            <label className="wizard-label">
              Planting Date (Optional)
              <input
                type="date"
                className="wizard-input"
                value={plot.plantingDate}
                onChange={(e) => setPlot({ ...plot, plantingDate: e.target.value })}
              />
            </label>
            {plot.plantingDate && (
              <label className="wizard-label">
                Date Certainty
                <select
                  className="wizard-select"
                  value={plot.certainty}
                  onChange={(e) => setPlot({ ...plot, certainty: e.target.value })}
                >
                  <option value="confirmed">Confirmed (Sowing Recorded)</option>
                  <option value="estimated">Estimated (Target Sowing Window)</option>
                </select>
              </label>
            )}
          </div>
        )}

        {step === 4 && (
          <div className="wizard-field-group">
            <div>
              <span style={{ fontSize: "0.85rem", color: "#a2c98a", fontWeight: 600 }}>
                Popular Crops (1-Click Resolution):
              </span>
              <div className="crop-chips-grid">
                {CROP_SUGGESTIONS.map((item) => (
                  <button
                    key={item.name}
                    type="button"
                    className={`crop-chip-btn ${plot.query.toLowerCase() === item.name.toLowerCase() ? "active" : ""}`}
                    onClick={() => resolve(item.name)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <label className="wizard-label">
              Crop Name, Local Name or Scientific Name
              <div style={{ display: "flex", gap: "0.6rem" }}>
                <input
                  className="wizard-input"
                  style={{ flex: 1 }}
                  placeholder="e.g. Maize, Makka, Triticum, Turmeric..."
                  value={plot.query}
                  onChange={(e) => {
                    setPlot({ ...plot, query: e.target.value, cropId: "", crop: undefined });
                    setResolution(undefined);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      resolve();
                    }
                  }}
                />
                <button
                  className="dock-cta-btn"
                  type="button"
                  style={{ padding: "0 1.2rem", whiteSpace: "nowrap" }}
                  onClick={() => resolve()}
                >
                  Resolve Crop 🔍
                </button>
              </div>
            </label>

            {resolution?.status?.toLowerCase().includes("ambiguous") && (
              <div className="candidate-list" style={{ background: "rgba(0,0,0,0.25)", padding: "1rem", borderRadius: "8px", border: "1px solid rgba(229,179,66,0.3)" }}>
                <p style={{ margin: "0 0 0.5rem 0", color: "#e5b342", fontSize: "0.85rem", fontWeight: 600 }}>
                  Multiple taxonomic matches found. Please select one:
                </p>
                {resolution.candidates?.map((candidate) => (
                  <button
                    key={candidate.cropId}
                    type="button"
                    className={`candidate ${plot.cropId === candidate.cropId ? "selected" : ""}`}
                    style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 12px", margin: "4px 0", background: plot.cropId === candidate.cropId ? "#2d5833" : "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", color: "#ffffff", cursor: "pointer" }}
                    onClick={() => setPlot({ ...plot, cropId: candidate.cropId, crop: candidate })}
                  >
                    <strong>{candidate.canonicalName}</strong> · <em>{candidate.scientificName}</em>
                  </button>
                ))}
              </div>
            )}

            {resolution?.crop && (
              <div style={{ background: "rgba(45,88,51,0.3)", border: "1px solid rgba(134,239,172,0.4)", borderRadius: "8px", padding: "1rem" }}>
                <div style={{ color: "#86efac", fontWeight: 700, fontSize: "0.82rem", textTransform: "uppercase" }}>
                  ✓ Resolved Taxonomic Entity
                </div>
                <div style={{ color: "#ffffff", fontSize: "1.1rem", fontWeight: 600, marginTop: "0.2rem" }}>
                  {resolution.crop.canonicalName} <span style={{ color: "#a2c98a", fontStyle: "italic", fontSize: "0.9rem" }}>({resolution.crop.scientificName})</span>
                </div>
                <div style={{ color: "#8fa896", fontSize: "0.8rem", marginTop: "0.3rem" }}>
                  Crop ID: <code>{resolution.crop.cropId}</code>
                </div>
              </div>
            )}
          </div>
        )}

        {step === 5 && (
          <div className="wizard-field-group">
            <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(88,126,75,0.3)", borderRadius: "8px", padding: "1.2rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              {!existingFarmId && (
                <div>
                  <h4 style={{ color: "#a2c98a", margin: "0 0 0.5rem 0", fontSize: "0.95rem" }}>Farm Profile</h4>
                  <p style={{ margin: "0.3rem 0", color: "#ffffff", fontSize: "0.9rem" }}><strong>Name:</strong> {farm.name}</p>
                  <p style={{ margin: "0.3rem 0", color: "#b2c9b8", fontSize: "0.85rem" }}><strong>Timezone:</strong> {farm.timezone}</p>
                  <p style={{ margin: "0.3rem 0", color: "#b2c9b8", fontSize: "0.85rem" }}><strong>Coords:</strong> {farm.latitude}°N, {farm.longitude}°E</p>
                </div>
              )}
              <div>
                <h4 style={{ color: "#a2c98a", margin: "0 0 0.5rem 0", fontSize: "0.95rem" }}>Initial Plot</h4>
                <p style={{ margin: "0.3rem 0", color: "#ffffff", fontSize: "0.9rem" }}><strong>Crop:</strong> {plot.crop?.canonicalName || plot.query}</p>
                <p style={{ margin: "0.3rem 0", color: "#b2c9b8", fontSize: "0.85rem" }}><strong>Scientific:</strong> {plot.crop?.scientificName || "Taxonomic entity"}</p>
                <p style={{ margin: "0.3rem 0", color: "#b2c9b8", fontSize: "0.85rem" }}><strong>Area:</strong> {plot.area} m²</p>
                <p style={{ margin: "0.3rem 0", color: "#b2c9b8", fontSize: "0.85rem" }}><strong>Sowing:</strong> {plot.plantingDate || "Not specified"}</p>
              </div>
            </div>
          </div>
        )}

        {error && <ErrorState label={error} />}

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "2rem", borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "1.2rem" }}>
          {step > firstStep ? (
            <button
              type="button"
              className="dock-item"
              style={{ padding: "8px 18px", borderRadius: "6px", background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", color: "#c5d8ca", cursor: "pointer" }}
              onClick={() => setStep(step - 1)}
            >
              ← Back
            </button>
          ) : <div />}

          {step < 5 ? (
            <button
              type="button"
              className="dock-cta-btn"
              style={{ padding: "8px 22px" }}
              onClick={next}
            >
              Continue →
            </button>
          ) : (
            <button
              type="button"
              className="dock-cta-btn"
              disabled={busy}
              style={{ padding: "10px 26px" }}
              onClick={save}
            >
              {busy ? "Saving & Initializing…" : existingFarmId ? "Save Plot →" : "Register Farm & Open Decision Lab ◈"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function FarmDetail({ farmId, navigate }: { farmId: string; navigate: (path: string) => void }) {
  const [farm, setFarm] = useState<Farm>(); const [error, setError] = useState("");
  const [telegramUrl, setTelegramUrl] = useState("");
  const [telegramError, setTelegramError] = useState("");
  const connect = async () => {
    setTelegramError("");
    try {
      setTelegramUrl((await apiClient.issueTelegramLink(farmId)).telegramConnectUrl);
    } catch (e) { setTelegramError(message(e)); }
  };
  useEffect(() => {
    let active = true;
    apiClient.getFarm(farmId).then((savedFarm) => {
      if (!active) return;
      setFarm(savedFarm);
      window.localStorage.setItem("terrapulse-active-farm-id", savedFarm.farmId);
    }).catch((e) => { if (active) setError(message(e)); });
    return () => { active = false; };
  }, [farmId]);
  if (error) return <PageContainer><ErrorState label={error} /></PageContainer>; if (!farm) return <PageContainer><LoadingState label="Loading farm…" /></PageContainer>;
  return <PageContainer><div className="page-intro"><p className="eyebrow">Farm workspace</p><h2>{farm.name}</h2><p>{farm.location.latitude}, {farm.location.longitude} · {farm.timezone}</p><button className="primary-button" onClick={() => navigate(`/farms/${farm.farmId}/plots/new`)}>Add plot <span>→</span></button></div><div className="card-grid">{farm.plots.map((plot) => <button className="info-card farm-card" key={plot.plotId} onClick={() => navigate(`/farms/${farm.farmId}/plots/${plot.plotId}`)}><h3>{plot.cropCanonicalName}</h3><p>{plot.areaM2.value} m² · {plot.plantingDate || "Planting date unavailable"}</p><span className="card-link">Open evidence ↗</span></button>)}</div><section className="form-panel"><div className="form-actions">
    <button className="secondary-button" onClick={() => navigate(`/dashboard?farmId=${farmId}&tab=calendar`)}>Agricultural Calendar</button>
    <button className="secondary-button" onClick={() => navigate(`/dashboard?farmId=${farmId}&tab=living-field`)}>Living Field</button>
    <button className="secondary-button" onClick={() => navigate(`/saved-decisions/${farmId}`)}>Saved Decisions</button>
    <button className="secondary-button" onClick={() => navigate(`/advisory/${farmId}`)}>Advisory</button>
    <button className="secondary-button" onClick={connect}>Set up Telegram</button>
    </div>{telegramError && <ErrorState label={telegramError} />}<TelegramConnect url={telegramUrl} /></section><PitchAlertControl farmId={farmId} /><ResourcePanel farm={farm} /></PageContainer>;
}

function Evidence({ farmId, plotId, navigate }: { farmId: string; plotId: string; navigate: (path: string) => void }) {
  const [farm, setFarm] = useState<Farm>(); const [environment, setEnvironment] = useState<Environment>(); const [error, setError] = useState(""); const [running, setRunning] = useState(false); const [mapping, setMapping] = useState(""); const [preparing, setPreparing] = useState(false);
  useEffect(() => { apiClient.getFarm(farmId).then(setFarm).catch((e) => setError(message(e))); }, [farmId]);
  const plot = farm?.plots.find((p) => p.plotId === plotId);
  const prepare = async () => {
    if (!farm || !plot || preparing) return;
    setPreparing(true);
    setError("");
    const today = new Intl.DateTimeFormat("sv-SE", { timeZone: farm.timezone }).format(new Date());
    const startDate = plot.plantingDate || today;
    try {
      setEnvironment(await apiClient.prepareEnvironment({
        farmId, plotId, simulationPeriod: { startDate, endDate: startDate > today ? startDate : today },
        requestedOutputs: [], includeEnsemble: false, forceRefresh: false,
      }));
    } catch (e) { setError(message(e)); }
    finally { setPreparing(false); }
  };
  const run = async () => { if (!environment?.environmentalSnapshotId || !environment.isValid || (plot!.cropCanonicalName === "Turmeric" && !mapping)) return; setRunning(true); setError(""); try { const result = await apiClient.submitSimulation({ farmId, plotId, environmentalSnapshotId: environment.environmentalSnapshotId, irrigationMode: "rainfed", turmericMapping: mapping || undefined }); navigate(`/farms/${farmId}/plots/${plotId}/results/${result.simulationRunId}`); } catch (e) { setError(message(e)); } finally { setRunning(false); } };
  if (!farm || !plot) return <PageContainer>{error ? <ErrorState label={error} /> : <LoadingState label="Loading plot…" />}</PageContainer>;
  return <PageContainer><div className="page-intro"><p className="eyebrow">Environmental evidence</p><h2>{plot.cropCanonicalName}</h2><p>{farm.name} · {plot.areaM2.value} m² · {plot.plantingDate || "Planting date unavailable"}</p><button className="primary-button" disabled={preparing} onClick={prepare}>Prepare evidence <span>→</span></button><button className="secondary-button" onClick={() => navigate(`/farms/${farmId}/plots/${plotId}/observatory`)}>Living Field</button></div>{error && <ErrorState label={error} />}{environment && <><div className="evidence-grid"><ReusableCard><h3>Soil profile</h3><Metric label="Depth" value={environment.c1Input?.soil?.depthCm} /><Metric label="Texture" value={environment.c1Input?.soil?.texture} /><Metric label="Field capacity" value={environment.c1Input?.soil?.fieldCapacity} /><Metric label="Wilting point" value={environment.c1Input?.soil?.wiltingPoint} /></ReusableCard><ReusableCard><h3>Weather conditions</h3><p>{environment.c1Input?.dailyWeather?.length || 0} returned records</p>{environment.c1Input?.dailyWeather?.slice(0, 5).map((w) => <Metric key={w.date} label={w.date} value={w.rainfallMm} />)}</ReusableCard><ReusableCard><h3>Crop capability</h3><p>{environment.capability?.selectedEngine || "Unavailable"} {environment.capability?.engineVersion || ""}</p><p>{environment.capability?.knownLimitations?.join(" ")}</p></ReusableCard><ReusableCard><h3>Validation and provenance</h3><p>{environment.isValid ? "Validated for the requested inputs." : "Not simulation-ready."}</p><p>{environment.warnings?.join(" ")}</p><p>Freshness: {environment.freshness || "not reported"}</p></ReusableCard></div>{environment.isValid && environment.capability?.selectedEngine === "FAO-56" && <><label className="mapping-select">Turmeric stage mapping<select value={mapping} onChange={(e) => setMapping(e.target.value)}><option value="">Select A, B or C</option><option value="A">A — early season</option><option value="B">B — middle season</option><option value="C">C — late season</option></select></label><button className="primary-button" disabled={running || (plot.cropCanonicalName === "Turmeric" && !mapping)} onClick={run}>{running ? "Submitting…" : "Run Simulation"} <span>→</span></button></>}<button className="text-button evidence-link" onClick={() => navigate(`/farms/${farmId}/plots/${plotId}/results`)}>View simulation results →</button><div className="workspace-links"><button className="secondary-button" onClick={() => navigate(`/farms/${farmId}/plots/${plotId}/observatory`)}>Open Living Field</button><button className="secondary-button" onClick={() => navigate(`/farms/${farmId}/plots/${plotId}/timeline?snapshot=${environment.environmentalSnapshotId}`)}>Decision timeline</button><button className="secondary-button" onClick={() => navigate(`/farms/${farmId}/plots/${plotId}/future-fold`)}>Future Fold</button></div></>}</PageContainer>;
}
function Metric({ label, value }: { label: string; value: unknown }) { const m = value as { value?: number; unit?: string; availability?: { status: string; reason?: string } } | undefined; return <p className="metric"><span>{label}</span><strong>{typeof value === "string" ? value : m?.availability?.status === "available" ? `${m.value} ${m.unit}` : m?.availability?.reason || m?.availability?.status || "Unavailable"}</strong></p>; }

function Results({ farmId, plotId, navigate }: { farmId: string; plotId: string; navigate: (path: string) => void }) {
  const [runs, setRuns] = useState<Simulation[]>([]); const [error, setError] = useState("");
  useEffect(() => { apiClient.listSimulations(farmId, plotId).then((v) => setRuns(v.simulations)).catch((e) => setError(message(e))); }, [farmId, plotId]);
  if (error) return <PageContainer><ErrorState label={error} /></PageContainer>;
  return <PageContainer><div className="page-intro"><p className="eyebrow">Scientific results</p><h2>Simulation history</h2><p>Only persisted runs and available scientific metrics are shown.</p></div>{runs.length === 0 ? <EmptyState title="No simulation results are available for this plot yet." description="Prepare environmental evidence first, then submit a supported simulation." action={<button className="secondary-button" onClick={() => navigate(`/farms/${farmId}/plots/${plotId}/environment`)}>Environmental Evidence</button>} /> : <div className="card-grid">{runs.map((run) => <button className="info-card farm-card" key={run.simulationRunId} onClick={() => navigate(`/farms/${farmId}/plots/${plotId}/results/${run.simulationRunId}`)}><h3>{run.status}</h3><p>{run.engine} {run.engineVersion} · {run.requestedAt || ""}</p><span className="card-link">Inspect run ↗</span></button>)}</div>}</PageContainer>;
}
function ResultDetail({ runId }: { runId: string }) { const [run, setRun] = useState<Simulation>(); const [error, setError] = useState(""); useEffect(() => { apiClient.getSimulation(runId).then(setRun).catch((e) => setError(message(e))); }, [runId]); if (error) return <PageContainer><ErrorState label={error} /></PageContainer>; if (!run) return <PageContainer><LoadingState label="Loading simulation…" /></PageContainer>; return <PageContainer><div className="page-intro"><p className="eyebrow">Run {run.simulationRunId}</p><h2>{run.status}</h2><p>{run.engine} {run.engineVersion} · snapshot {run.environmentalSnapshotId}</p></div><section className="results-table">{run.warnings?.map((warning) => <p key={warning} className="warning">{warning}</p>)}{run.errorMessage && <ErrorState label={`${run.errorCode}: ${run.errorMessage}`} />}{run.states?.length ? run.states.map((state, index) => <article key={index}><strong>{String(state.date)}</strong><pre>{JSON.stringify(state, null, 2)}</pre></article>) : <p>No available dated scientific states.</p>}</section></PageContainer>; }

function AppErrorBoundary({ children, copy }: { children: ReactNode; copy: typeof translations.en }) { return <Boundary copy={copy}>{children}</Boundary>; }
class Boundary extends Component<{ children: ReactNode; copy: typeof translations.en }, { failed: boolean }> { state = { failed: false }; static getDerivedStateFromError() { return { failed: true }; } componentDidCatch(error: Error, info: ErrorInfo) { console.error("TerraPulse rendering failed", error, info); } render() { return this.state.failed ? <PageContainer><ErrorState label={this.props.copy.error} /></PageContainer> : this.props.children; } }

export function App() {
  const { path, navigate } = useNavigation();
  const [locale, setLocale] = useState(getInitialLocale);
  const copy = translations[locale];
  const legacyRoute: Route = path.startsWith("/farms") ? "connect" : path === "/assisted" ? "assisted" : path === "/observatory" ? "observatory" : "connect";

  const [atmosphere, setAtmosphere] = useState<SylvaLivingWorldVariant>(() => {
    const saved = typeof window !== "undefined" ? window.localStorage.getItem("terrapulse-atmosphere") : null;
    return saved === "sakura-sunset" || saved === "maple-autumn" || saved === "sequoia-mist"
      ? (saved as SylvaLivingWorldVariant)
      : "living-green";
  });

  const handleAtmosphereChange = (nextAtmo: SylvaLivingWorldVariant) => {
    setAtmosphere(nextAtmo);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("terrapulse-atmosphere", nextAtmo);
      document.documentElement.setAttribute("data-atmosphere", nextAtmo);
    }
  };

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-atmosphere", atmosphere);
    }
  }, [atmosphere]);

  // 1. Cinematic 3D Landing Page
  if (path === "/" || path === "/landing") {
    return (
      <LandingPage
        navigate={navigate}
        locale={locale}
        onLocaleChange={(l) => {
          setLocale(l);
          window.localStorage.setItem("terrapulse-locale", l);
        }}
        atmosphere={atmosphere}
        onAtmosphereChange={handleAtmosphereChange}
      />
    );
  }

  // 2. Direct Workspaces & Unified Agricultural Decision Laboratory Dashboard
  const directTabMap: Record<string, string> = {
    "/advisory": "advisory",
    "/advisories": "advisory",
    "/observatory": "observatory",
    "/crop-planning": "crop-lens",
    "/crop-lens": "crop-lens",
    "/calendar": "calendar",
    "/future-fold": "future-fold",
    "/living-field": "living-field",
    "/saved-decisions": "timeline",
    "/timeline": "timeline",
  };

  const scopedFeature = path.match(/^\/(advisory|advisories|saved-decisions|crop-planning)\/([^/]+)$/);
  const directTab = directTabMap[scopedFeature ? `/${scopedFeature[1]}` : path];
  if (path === "/dashboard" || path.startsWith("/dashboard/") || path === "/demo" || directTab) {
    const urlParams = new URLSearchParams(window.location.search);
    const requestedTab = urlParams.get("tab") || "overview";
    const tabParam = directTab || directTabMap[`/${requestedTab}`] || requestedTab;
    const storedFarmId = window.localStorage.getItem("terrapulse-active-farm-id");
    const explicitFarmId = scopedFeature?.[2] || urlParams.get("farmId");
    const farmIdParam = explicitFarmId || storedFarmId || "";
    return (
      <AgriculturalDashboard
        key={farmIdParam}
        navigate={navigate}
        initialTab={tabParam}
        farmId={farmIdParam}
        explicitFarm={Boolean(explicitFarmId)}
        locale={locale}
        onLocaleChange={(l) => {
          setLocale(l);
          window.localStorage.setItem("terrapulse-locale", l);
        }}
        atmosphere={atmosphere}
        onAtmosphereChange={handleAtmosphereChange}
      />
    );
  }

  // 3. Farm Registration & Onboarding (Dark Luxury Emerald Wizard)
  if (path === "/register" || path === "/farms/new") {
    return <FarmWizard key={path} navigate={navigate} atmosphere={atmosphere} />;
  }

  if (path === "/offline" || path.startsWith("/offline/")) {
    return (
      <AppErrorBoundary copy={copy}>
        <FarmerApp
          path={path.slice(8) || "/"}
          navigate={(next) => navigate(next.startsWith("/farms") ? next : "/offline" + next)}
        />
      </AppErrorBoundary>
    );
  }

  let content: ReactNode;
  const parts = path.split("/").filter(Boolean);
  const workspaceFeatures = ["crop-planning", "calendar", "future-fold", "living-field", "saved-decisions"];
  const feature = workspaceFeatures.includes(parts[0]) ? (parts[0] as WorkspaceFeature) : undefined;
  const route: Route =
    feature ||
    (["/assisted", "/interact", "/advisories"].includes(path)
      ? "advisories"
      : parts[4] === "observatory"
      ? "living-field"
      : parts[4] === "timeline"
      ? "saved-decisions"
      : parts[4] === "future-fold"
      ? "future-fold"
      : legacyRoute);

  if (feature) content = <WorkspaceFeatures feature={feature} farmId={parts[1]} navigate={navigate} />;
  else if (path === "/connect" || path === "/farm" || path === "/farms") content = <FarmList navigate={navigate} copy={copy} />;
  else if (["/assisted", "/interact", "/advisories"].includes(path)) content = <FarmerInteraction copy={copy} locale={locale} />;
  else if (path === "/recover") content = <FarmOpenLink navigate={navigate} />;
  else if (parts[0] === "farms" && parts[2] === "plots" && parts[3] === "new") content = <FarmWizard key={path} navigate={navigate} existingFarmId={parts[1]} />;
  else if (parts[0] === "farms" && parts[2] === "plots" && parts[4] === "environment") content = <Evidence key={path} farmId={parts[1]} plotId={parts[3]} navigate={navigate} />;
  else if (parts[0] === "farms" && parts[2] === "plots" && parts[4] === "results" && parts[5]) content = <ResultDetail runId={parts[5]} />;
  else if (parts[0] === "farms" && parts[2] === "plots" && parts[4] === "observatory") content = <Observatory key={path} farmId={parts[1]} plotId={parts[3]} navigate={navigate} />;
  else if (parts[0] === "farms" && parts[2] === "plots" && parts[4] === "timeline") content = <Timeline key={path} farmId={parts[1]} plotId={parts[3]} navigate={navigate} />;
  else if (parts[0] === "farms" && parts[2] === "plots" && parts[4] === "future-fold") content = <FutureFold key={path} farmId={parts[1]} plotId={parts[3]} navigate={navigate} />;
  else if (parts[0] === "farms" && parts[2] === "plots" && parts[4] === "results") content = <Results farmId={parts[1]} plotId={parts[3]} navigate={navigate} />;
  else if (parts[0] === "farms" && parts[2] === "plots" && parts[3]) content = <Evidence key={path} farmId={parts[1]} plotId={parts[3]} navigate={navigate} />;
  else if (parts[0] === "farms" && parts[1]) content = <FarmDetail key={parts[1]} farmId={parts[1]} navigate={navigate} />;
  else content = <FarmList navigate={navigate} copy={copy} />;

  return (
    <AppErrorBoundary copy={copy}>
      <AppShell
        route={route}
        copy={copy}
        locale={locale}
        onLocaleChange={(l) => {
          setLocale(l);
          window.localStorage.setItem("terrapulse-locale", l);
        }}
        onNavigate={(r) => {
          const currentFarm = parts[0] === "farms" && parts[1];
          if (currentFarm && directTabMap[`/${r}`]) {
            navigate(`/${r}?farmId=${encodeURIComponent(currentFarm)}`);
          } else {
            navigate(r === "connect" ? "/farms" : `/${r}`);
          }
        }}
        title={
          ({
            connect: copy.workspace,
            advisories: "Advisories",
            observatory: copy.observatory,
            "crop-planning": copy.cropPlanning,
            calendar: "Calendar",
            "future-fold": copy.futureFold,
            "living-field": "Living Field",
            "saved-decisions": copy.savedDecisions,
          })[route] || copy.workspace
        }
        subtitle={route === "advisories" ? copy.assistedDescription : ""}
      >
        {content}
      </AppShell>
    </AppErrorBoundary>
  );
}
