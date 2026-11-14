import { useEffect, useState } from "react";
import { apiClient, Farm } from "../services/apiClient";
import { ConnectedCalendar } from "./ConnectedCalendar";
import { PlotAdvisory } from "./PlotAdvisory";
import { PitchAlertControl } from "./PitchAlertControl";
import { ResourcePanel } from "./resources";
import { ErrorState, LoadingState } from "./ui";
import { FutureFold, Observatory, Timeline } from "./scenario";
import { Locale, localeLabels, translations, tUI } from "../i18n";
import { type SylvaLivingWorldVariant } from "@designcodeio/threeui";
import "../dashboard.css";

type Props = {
  navigate: (path: string) => void;
  initialTab?: string;
  farmId?: string;
  explicitFarm?: boolean;
  locale?: Locale;
  onLocaleChange?: (locale: Locale) => void;
  atmosphere?: SylvaLivingWorldVariant;
  onAtmosphereChange?: (atmo: SylvaLivingWorldVariant) => void;
};

export function AgriculturalDashboard({
  navigate,
  initialTab = "overview",
  farmId = "",
  explicitFarm = false,
  locale = "en",
  onLocaleChange,
  atmosphere = "living-green",
  onAtmosphereChange,
}: Props) {
  const currentTab = initialTab;
  const [allFarms, setAllFarms] = useState<Farm[]>();
  const [error, setError] = useState("");
  const farm = allFarms?.find((item) => item.farmId === farmId) ?? (explicitFarm ? undefined : allFarms?.[0]);
  const selectedFarmId = farm?.farmId ?? "";
  const setCurrentTab = (tab: string) => {
    const params = new URLSearchParams({ tab });
    if (selectedFarmId || farmId) params.set("farmId", selectedFarmId || farmId);
    navigate(`/dashboard?${params}`);
  };

  // Section States
  const [plotChoice, setSelectedPlotId] = useState("");
  const selectedPlotId = (farm?.plots.find((plot) => plot.plotId === plotChoice) ?? farm?.plots[0])?.plotId ?? "";
  const [notifications, setNotifications] = useState<any[]>([]);
  const [telegramStatus, setTelegramStatus] = useState<any>(null);
  const [deliveries, setDeliveries] = useState<any[]>([]);

  // Crop Lens State
  const [cropQuery, setCropQuery] = useState("Turmeric");
  const [cropLanguage, setCropLanguage] = useState<"en" | "kn" | "hi">(
    locale === "kn" || locale === "hi" ? locale : "en"
  );
  const [cropResolution, setCropResolution] = useState<any>(null);
  const [cropResolving, setCropResolving] = useState(false);

  const _copy = translations[locale] || translations.en;

  useEffect(() => {
    let active = true;
    apiClient.listFarms()
      .then(({ farms }) => { if (active) setAllFarms(farms); })
      .catch(() => { if (active) setError("Your saved farms could not be loaded."); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (selectedFarmId) window.localStorage.setItem("terrapulse-active-farm-id", selectedFarmId);
  }, [selectedFarmId]);

  useEffect(() => {
    if (!selectedFarmId) return;
    let active = true;
    apiClient.listNotifications(selectedFarmId)
      .then(({ notifications }) => { if (active) setNotifications(notifications); })
      .catch(() => {});
    apiClient.getTelegramStatus(selectedFarmId)
      .then((status) => { if (active) setTelegramStatus(status); })
      .catch(() => {});
    apiClient.getDeliveries(selectedFarmId)
      .then(({ deliveries }) => { if (active) setDeliveries(deliveries); })
      .catch(() => {});
    return () => { active = false; };
  }, [selectedFarmId]);

  // Resolve Crop Lens
  const handleResolveCrop = async () => {
    setCropResolving(true);
    try {
      const res = await apiClient.interactCrop({ query: cropQuery, language: cropLanguage });
      setCropResolution(res);
    } catch {
      try {
        const fallbackRes = await apiClient.resolveCrop(cropQuery);
        setCropResolution(fallbackRes);
      } catch (err: any) {
        setError("Crop resolution failed: " + err.message);
      }
    } finally {
      setCropResolving(false);
    }
  };

  const totalFarmAreaM2 = farm?.plots.reduce((total, plot) => total + plot.areaM2.value, 0) ?? 0;
  const farmPath = "/farms/" + selectedFarmId;
  const plotPath = farmPath + "/plots/" + selectedPlotId;
  const openPlotView = (view: string) => navigate(selectedPlotId ? plotPath + "/" + view : farmPath);

  const atmoClass =
    atmosphere === "sakura-sunset"
      ? "atmosphere-sakura"
      : atmosphere === "maple-autumn"
      ? "atmosphere-autumn"
      : atmosphere === "sequoia-mist"
      ? "atmosphere-mist"
      : "atmosphere-green";

  return (
    <div className={`dash-container ${atmoClass}`} data-atmosphere={atmosphere}>
      {/* Top Bar with Brand, Farm Selector, Guided Demo Mode, Atmosphere & Language */}
      <header className="dash-topbar">
        <div className="topbar-left">
          <div className="topbar-brand" onClick={() => navigate("/")}>
            <span className="brand-gem">◈</span>
            <span className="brand-title">{tUI(locale, "brand")}</span>
          </div>

          {/* Farm Switcher Dropdown */}
          <div className="farm-selector-wrap">
            <span className="selector-label">{tUI(locale, "selectFarm")}</span>
            <select
              className="topbar-farm-select"
              value={selectedFarmId}
              onChange={(e) => {
                const newId = e.target.value;
                navigate(`/dashboard?farmId=${newId}&tab=${currentTab}`);
              }}
              aria-label="Select registered farm"
            >
              {!farm && <option value="">Choose a saved farm</option>}
              {allFarms?.map((f) => (
                  <option key={f.farmId} value={f.farmId}>
                    {f.name} ({f.location.latitude.toFixed(2)}°N, {f.location.longitude.toFixed(2)}°E)
                  </option>
                ))}
            </select>
            <button
              className="topbar-new-farm-btn"
              onClick={() => navigate("/register")}
              title="Register a new farm"
            >
              {tUI(locale, "registerNewFarm")}
            </button>
          </div>
        </div>

        {/* Guided Demo Controls: 8 core areas */}
        <div className="guided-demo-bar">
          <span className="guided-label">{tUI(locale, "tour")}</span>
          <button
            className={`guided-step-btn ${currentTab === "overview" ? "active" : ""}`}
            onClick={() => setCurrentTab("overview")}
          >
            1. {tUI(locale, "tabOverview")}
          </button>
          <button
            className={`guided-step-btn ${currentTab === "advisory" ? "active" : ""}`}
            onClick={() => setCurrentTab("advisory")}
          >
            2. {tUI(locale, "tabAdvisory")}
          </button>
          <button
            className={`guided-step-btn ${currentTab === "observatory" ? "active" : ""}`}
            onClick={() => setCurrentTab("observatory")}
          >
            3. {tUI(locale, "tabObservatory")}
          </button>
          <button
            className={`guided-step-btn ${currentTab === "crop-lens" ? "active" : ""}`}
            onClick={() => setCurrentTab("crop-lens")}
          >
            4. {tUI(locale, "tabCropPlanning")}
          </button>
          <button
            className={`guided-step-btn ${currentTab === "calendar" ? "active" : ""}`}
            onClick={() => setCurrentTab("calendar")}
          >
            5. {tUI(locale, "tabCalendar")}
          </button>
          <button
            className={`guided-step-btn ${currentTab === "future-fold" ? "active" : ""}`}
            onClick={() => setCurrentTab("future-fold")}
          >
            6. {tUI(locale, "tabFutureFold")}
          </button>
          <button
            className={`guided-step-btn ${currentTab === "living-field" ? "active" : ""}`}
            onClick={() => setCurrentTab("living-field")}
          >
            7. {tUI(locale, "tabLivingField")}
          </button>
          <button
            className={`guided-step-btn ${currentTab === "timeline" ? "active" : ""}`}
            onClick={() => setCurrentTab("timeline")}
          >
            8. {tUI(locale, "tabSavedDecisions")}
          </button>
        </div>

        <div className="topbar-actions">
          {/* Atmosphere Theme Selector in Dashboard Topbar */}
          <div className="topbar-atmo-group" title="Dashboard Atmosphere Theme">
            <button
              type="button"
              className={`topbar-atmo-btn ${atmosphere === "living-green" ? "active" : ""}`}
              onClick={() => onAtmosphereChange && onAtmosphereChange("living-green")}
              title="Living Green"
            >
              🌿 {tUI(locale, "green")}
            </button>
            <button
              type="button"
              className={`topbar-atmo-btn ${atmosphere === "sakura-sunset" ? "active" : ""}`}
              onClick={() => onAtmosphereChange && onAtmosphereChange("sakura-sunset")}
              title="Sakura Sunset"
            >
              🌸 {tUI(locale, "sakura")}
            </button>
            <button
              type="button"
              className={`topbar-atmo-btn ${atmosphere === "maple-autumn" ? "active" : ""}`}
              onClick={() => onAtmosphereChange && onAtmosphereChange("maple-autumn")}
              title="Maple Autumn"
            >
              🍁 {tUI(locale, "autumn")}
            </button>
            <button
              type="button"
              className={`topbar-atmo-btn ${atmosphere === "sequoia-mist" ? "active" : ""}`}
              onClick={() => onAtmosphereChange && onAtmosphereChange("sequoia-mist")}
              title="Sequoia Mist"
            >
              🌲 {tUI(locale, "mist")}
            </button>
          </div>

          {/* Language Selector */}
          {onLocaleChange && (
            <select
              className="topbar-lang-select"
              value={locale}
              onChange={(e) => {
                const nextLoc = e.target.value as Locale;
                onLocaleChange(nextLoc);
                if (nextLoc === "kn" || nextLoc === "hi" || nextLoc === "en") {
                  setCropLanguage(nextLoc);
                }
              }}
              aria-label="Interface language"
            >
              {Object.entries(localeLabels).map(([k, name]) => (
                <option key={k} value={k}>
                  {k.toUpperCase()} · {name}
                </option>
              ))}
            </select>
          )}

          <button className="landing-back-btn" onClick={() => navigate("/")}>
            ← 3D Landing Page
          </button>
        </div>
      </header>

      {/* Main Layout: Sidebar Navigation + Content Area */}
      <div className="dash-body">
        <aside className="dash-sidebar">
          <nav className="dash-nav">
            <button
              className={`nav-item ${currentTab === "overview" ? "active" : ""}`}
              onClick={() => setCurrentTab("overview")}
            >
              <span className="nav-icon">⌂</span>
              <span className="nav-text">{tUI(locale, "tabOverview")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "advisory" ? "active" : ""}`}
              onClick={() => setCurrentTab("advisory")}
            >
              <span className="nav-icon">🌾</span>
              <span className="nav-text">{tUI(locale, "tabAdvisory")}</span>
              <span className="nav-badge">PAU</span>
            </button>
            <button
              className={`nav-item ${currentTab === "observatory" ? "active" : ""}`}
              onClick={() => setCurrentTab("observatory")}
            >
              <span className="nav-icon">🛰</span>
              <span className="nav-text">{tUI(locale, "tabObservatory")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "crop-lens" ? "active" : ""}`}
              onClick={() => setCurrentTab("crop-lens")}
            >
              <span className="nav-icon">🔍</span>
              <span className="nav-text">{tUI(locale, "tabCropPlanning")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "calendar" ? "active" : ""}`}
              onClick={() => setCurrentTab("calendar")}
            >
              <span className="nav-icon">📅</span>
              <span className="nav-text">{tUI(locale, "tabCalendar")}</span>
              <span className="nav-badge">2.0</span>
            </button>
            <button
              className={`nav-item ${currentTab === "future-fold" ? "active" : ""}`}
              onClick={() => setCurrentTab("future-fold")}
            >
              <span className="nav-icon">↗</span>
              <span className="nav-text">{tUI(locale, "tabFutureFold")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "living-field" ? "active" : ""}`}
              onClick={() => setCurrentTab("living-field")}
            >
              <span className="nav-icon">🌱</span>
              <span className="nav-text">{tUI(locale, "tabLivingField")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "timeline" ? "active" : ""}`}
              onClick={() => setCurrentTab("timeline")}
            >
              <span className="nav-icon">⏱</span>
              <span className="nav-text">{tUI(locale, "tabSavedDecisions")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "notifications" ? "active" : ""}`}
              onClick={() => setCurrentTab("notifications")}
            >
              <span className="nav-icon">🔔</span>
              <span className="nav-text">Real-Time Alerts</span>
              {notifications.length > 0 && (
                <span className="nav-counter">{notifications.length}</span>
              )}
            </button>
            <button
              className={`nav-item ${currentTab === "water" ? "active" : ""}`}
              onClick={() => setCurrentTab("water")}
            >
              <span className="nav-icon">💧</span>
              <span className="nav-text">Water Ledger</span>
            </button>
          </nav>

          <div className="sidebar-footer">
            <div className="farm-info-chip">
              <span className="chip-label">Active Farm Profile:</span>
              <strong>{farm?.name || "No farm selected"}</strong>
              <small>
                {farm?.location?.latitude.toFixed(2)}°N, {farm?.location?.longitude.toFixed(2)}°E ·{" "}
                {farm?.timezone || "Asia/Kolkata"}
              </small>
            </div>
          </div>
        </aside>

        {/* Content Viewport */}
        <main className="dash-main">
          {/* ========================================================
              1. FARM WORKSPACE (OVERVIEW)
              ======================================================== */}
          {!allFarms && (error ? <ErrorState label={error} /> : <LoadingState label="Loading saved farms…" />)}
          {explicitFarm && !!allFarms?.length && !farm && <ErrorState label="This farm is unavailable in this browser. Choose an accessible farm from the farm selector." />}
          {allFarms?.length === 0 && <section className="tab-pane">
            <h2>Your saved farms</h2>
            <p>Already registered? Send /open in your connected TerraPulse Telegram chat and tap the link.</p>
            <button className="inspect-plot-btn" onClick={() => navigate("/farms")}>Open Farm Workspace</button>
          </section>}
          {farm && <>
          {currentTab === "overview" && (
            <div className="tab-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Farm Decision Workspace</span>
                  <h2>{farm?.name}</h2>
                  <p className="subtitle">
                    Grounded multicrop agricultural intelligence combining biophysical simulation,
                    regional weather telemetry, and soil-moisture accounting.
                  </p>
                </div>
                <div className="quick-actions">
                  <button className="inspect-plot-btn" onClick={() => navigate(farmPath)}>Open saved land</button>
                  <button className="inspect-plot-btn" onClick={() => setCurrentTab("calendar")}>Agricultural Calendar</button>
                </div>
              </div>
              <div className="kpi-grid">
                <div className="kpi-card">
                  <span className="kpi-title">Farm size and plots</span>
                  <div className="kpi-val">{farm.plots.length} plots</div>
                  <span className="kpi-sub">{(totalFarmAreaM2 / 10000).toFixed(2)} ha</span>
                </div>
              </div>
              <PitchAlertControl farmId={selectedFarmId} />

              {/* Plots Overview Grid */}
              <h3 className="section-title">Farm Plots & Crop Development</h3>
              <div className="plots-summary-grid">
                {farm?.plots?.map((p) => (
                  <div key={p.plotId} className="plot-summary-card">
                    <div className="card-top">
                      <span className="plot-crop-name">{p.cropCanonicalName}</span>
                      <span className="plot-area-tag">{(p.areaM2.value / 10000).toFixed(2)} ha</span>
                    </div>
                    <div className="plot-details">
                      <p><strong>Planted:</strong> {p.plantingDate || "Date unavailable"}</p>
                    </div>
                    <div style={{ display: "flex", gap: "0.5rem", marginTop: "auto" }}>
                      <button
                        className="inspect-plot-btn"
                        style={{ flex: 1 }}
                        onClick={() => {
                          navigate(farmPath + "/plots/" + p.plotId + "/observatory");
                        }}
                      >
                        Inspect 3D →
                      </button>
                      <button
                        className="inspect-plot-btn"
                        style={{ flex: 1 }}
                        onClick={() => {
                          setSelectedPlotId(p.plotId);
                          setCurrentTab("advisory");
                        }}
                      >
                        Advisory →
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Recent Notifications Tray */}
              <div className="alerts-preview-section">
                <div className="alerts-preview-header">
                  <h3>Recent Decision Alerts & Telegram Deliveries</h3>
                  <button className="view-all-link" onClick={() => setCurrentTab("notifications")}>
                    Manage Telegram Alerts →
                  </button>
                </div>
                <div className="alerts-list">
                  {notifications.slice(0, 3).map((alert, i) => (
                    <div key={i} className={`alert-row ${alert.category}`}>
                      <div className="alert-meta">
                        <span className="alert-cat-tag">{alert.category}</span>
                        <span className="alert-date">{alert.eventDate}</span>
                        <span className="alert-status-tag">{alert.delivery?.status || "delivered"}</span>
                      </div>
                      <div className="alert-text">
                        <strong>{alert.payload?.title || alert.kind}</strong>
                        <p>{alert.payload?.suggestedAction || alert.payload?.evidence}</p>
                      </div>
                    </div>
                  ))}
                  {notifications.length === 0 && (
                    <p className="no-alerts-msg">
                      No alerts have been recorded for this farm.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ========================================================
              2. ADVISORY WORKSPACE (EVIDENCE-GROUNDED RECOMMENDATIONS)
              ======================================================== */}
          {currentTab === "advisory" && (
            <div className="tab-pane advisory-pane">
              <div className="pane-header">
                <div>
                  <h2>Agricultural Advisory</h2>
                  <p className="subtitle">{farm.name} · Weather, soil and scientific evidence for the selected plot</p>
                </div>
                <div className="plot-selector-btns">
                  {farm?.plots?.map((p) => (
                    <button
                      key={p.plotId}
                      className={`plot-sel-btn ${selectedPlotId === p.plotId ? "active" : ""}`}
                      onClick={() => setSelectedPlotId(p.plotId)}
                    >
                      {p.management?.plotName || p.cropCanonicalName}
                    </button>
                  ))}
                </div>
              </div>

              {selectedPlotId
                ? <PlotAdvisory key={selectedPlotId} farmId={selectedFarmId} plotId={selectedPlotId} locale={locale} />
                : <button className="inspect-plot-btn" onClick={() => navigate(farmPath + "/plots/new")}>Add a crop plot</button>}
            </div>
          )}

          {/* ========================================================
              3. OBSERVATORY (ENVIRONMENTAL INTELLIGENCE)
              ======================================================== */}
          {currentTab === "observatory" && (
            <div className="tab-pane">
              <div className="pane-header"><h2>Environmental Evidence</h2></div>
              <button className="inspect-plot-btn" onClick={() => openPlotView("environment")}>Open plot evidence</button>
            </div>
          )}

          {currentTab === "crop-lens" && (
            <div className="tab-pane crop-lens-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Multilingual Botanical Resolution</span>
                  <h2>Crop Planning & Crop Lens</h2>
                  <p className="subtitle">
                    Open-ended crop entry querying FAO AGROVOC, GBIF, and ECOCROP. Automatically binds the
                    appropriate scientific biophysical simulation engine.
                  </p>
                </div>
              </div>

              <div className="crop-search-card">
                <div className="lang-selector-row">
                  <span>Language:</span>
                  <button
                    className={`lang-btn ${cropLanguage === "en" ? "active" : ""}`}
                    onClick={() => {
                      setCropLanguage("en");
                      setCropQuery("Turmeric");
                    }}
                  >
                    English
                  </button>
                  <button
                    className={`lang-btn ${cropLanguage === "hi" ? "active" : ""}`}
                    onClick={() => {
                      setCropLanguage("hi");
                      setCropQuery("हल्दी");
                    }}
                  >
                    Hindi (हिन्दी)
                  </button>
                  <button
                    className={`lang-btn ${cropLanguage === "kn" ? "active" : ""}`}
                    onClick={() => {
                      setCropLanguage("kn");
                      setCropQuery("ಅರಿಶಿನ");
                    }}
                  >
                    Kannada (ಕನ್ನಡ)
                  </button>
                </div>

                <div className="search-bar-row">
                  <input
                    className="crop-input"
                    value={cropQuery}
                    onChange={(e) => setCropQuery(e.target.value)}
                    placeholder="Enter crop common name, vernacular alias, or scientific name..."
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleResolveCrop();
                    }}
                  />
                  <button
                    className="resolve-btn"
                    disabled={cropResolving || !cropQuery.trim()}
                    onClick={handleResolveCrop}
                  >
                    {cropResolving ? "Resolving…" : "Resolve Identity & Engine ↗"}
                  </button>
                </div>

                <div className="sample-chips">
                  <span>Quick samples:</span>
                  <button
                    onClick={() => {
                      setCropQuery("Turmeric");
                      setCropLanguage("en");
                    }}
                  >
                    Turmeric (Curcuma longa)
                  </button>
                  <button
                    onClick={() => {
                      setCropQuery("Makka");
                      setCropLanguage("hi");
                    }}
                  >
                    Makka (Maize)
                  </button>
                  <button
                    onClick={() => {
                      setCropQuery("ರಾಗಿ");
                      setCropLanguage("kn");
                    }}
                  >
                    ರಾಗಿ (Finger Millet)
                  </button>
                  <button
                    onClick={() => {
                      setCropQuery("Wheat");
                      setCropLanguage("en");
                    }}
                  >
                    Wheat (Triticum aestivum)
                  </button>
                </div>
              </div>

              {/* Resolution Results Card */}
              {cropResolution && (
                <div className="resolution-card">
                  <div className="res-header">
                    <div>
                      <span className="res-tag">
                        {cropResolution.resolvedCrop?.selectedEngine || "Scientific Model"} Bound
                      </span>
                      <h3>
                        {cropResolution.resolvedCrop?.canonicalName ||
                          cropResolution.crop?.canonicalName ||
                          cropQuery}
                      </h3>
                      <p className="sci-name">
                        Scientific Name:{" "}
                        <em>
                          {cropResolution.resolvedCrop?.scientificName ||
                            cropResolution.crop?.scientificName}
                        </em>
                      </p>
                    </div>
                  </div>

                  <div className="res-grid">
                    <div className="res-col">
                      <h4>Botanical & Ecological Classification</h4>
                      <p>
                        <strong>Family:</strong>{" "}
                        {cropResolution.resolvedCrop?.family ||
                          cropResolution.crop?.family ||
                          "Zingiberaceae"}
                      </p>
                      <p>
                        <strong>Authoritative Sources:</strong> FAO AGROVOC, GBIF, ECOCROP
                      </p>
                      <p>
                        <strong>Supported Aliases:</strong>{" "}
                        {(cropResolution.resolvedCrop?.aliases || ["haldi", "arishina", "turmeric"])
                          .slice(0, 6)
                          .join(", ")}
                      </p>
                    </div>
                    <div className="res-col">
                      <h4>Simulation Engine Binding</h4>
                      <p>
                        <strong>Selected Engine:</strong>{" "}
                        {cropResolution.resolvedCrop?.selectedEngine || "FAO-56"}
                      </p>
                      <p>
                        <strong>Model Engine Version:</strong>{" "}
                        {cropResolution.resolvedCrop?.engineVersion || "2026.1"}
                      </p>
                      <p>
                        <strong>Supported Outputs:</strong> Water Stress (Ks), Root-zone Depletion
                        (Dr), Actual ET (ETa)
                      </p>
                    </div>
                  </div>

                  {cropResolution.responseText && (
                    <div className="indic-response-box">
                      <h4>Local Language Agronomic Guidance:</h4>
                      <p>{cropResolution.responseText}</p>
                    </div>
                  )}

                  <div style={{ marginTop: "1.2rem" }}>
                    <button
                      className="primary-button"
                      onClick={() => navigate(farmPath + "/plots/new")}
                    >
                      + Add Plot With This Crop →
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ========================================================
              5. AGRICULTURAL CALENDAR 2.0
              ======================================================== */}
          {currentTab === "calendar" && <div className="tab-pane calendar-pane">
            <ConnectedCalendar key={selectedFarmId} farmId={selectedFarmId} />
          </div>}

          {["living-field", "future-fold", "timeline"].includes(currentTab) && (
            <div className="tab-pane">
              {farm.plots.length > 1 && <label>Plot <select value={selectedPlotId} onChange={(event) => setSelectedPlotId(event.target.value)}>
                {farm.plots.map((plot) => <option key={plot.plotId} value={plot.plotId}>{plot.management?.plotName || plot.cropCanonicalName}</option>)}
              </select></label>}
              {!selectedPlotId && <button className="inspect-plot-btn" onClick={() => navigate(farmPath + "/plots/new")}>Add a crop plot</button>}
              {selectedPlotId && currentTab === "living-field" && <Observatory key={selectedPlotId} farmId={selectedFarmId} plotId={selectedPlotId} navigate={navigate} />}
              {selectedPlotId && currentTab === "future-fold" && <FutureFold key={selectedPlotId} farmId={selectedFarmId} plotId={selectedPlotId} navigate={navigate} />}
              {selectedPlotId && currentTab === "timeline" && <Timeline key={selectedPlotId} farmId={selectedFarmId} plotId={selectedPlotId} navigate={navigate} />}
            </div>
          )}

          {currentTab === "notifications" && (
            <div className="tab-pane notifications-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Autonomous Notification Engine</span>
                  <h2>Farm Alerts & Telegram</h2>
                  <p className="subtitle">
                    Telegram delivers eligible notices from daily evidence and calendar checks.
                  </p>
                </div>
              </div>
              <PitchAlertControl farmId={selectedFarmId} />

              {/* Telegram Connection Widget */}
              <div className="telegram-widget-card">
                <div className="tg-icon-wrap">✈</div>
                <div className="tg-info">
                  <h3>Telegram Farmer Alert Gateway</h3>
                  <p>
                    Status:{" "}
                    <strong className="text-good">
                      {telegramStatus?.connected ? "Connected & Active" : "Ready to Link"}
                    </strong>{" "}
                   {telegramStatus?.botUsername && <> · Bot: <strong>@{telegramStatus.botUsername}</strong></>}
                  </p>
                  <p className="tg-desc">
                    Receive actionable alerts on rainfall forecasts, soil water-stress, and stage milestones
                    with zero subscription fees.
                  </p>
                </div>
                <div className="tg-cta">
                  <button className="tg-connect-btn" onClick={() => navigate(farmPath)}>
                    {telegramStatus?.connected ? "Open farm workspace" : "Set up Telegram"}
                  </button>
                </div>
              </div>

              {/* Active Alerts List */}
              <div className="alerts-full-section">
                <h3>Current Enqueued Alerts</h3>
                <div className="alerts-table-wrap">
                  <table className="alerts-table">
                    <thead>
                      <tr>
                        <th>Category</th>
                        <th>Crop</th>
                        <th>Event Date</th>
                        <th>Alert & Recommendation</th>
                        <th>Delivery Status</th>
                        <th>Channel</th>
                      </tr>
                    </thead>
                    <tbody>
                      {notifications.map((n, i) => (
                        <tr key={i}>
                          <td>
                            <span className={`cat-tag ${n.category}`}>{n.category}</span>
                          </td>
                          <td>
                            <strong>{n.payload?.cropName || "Farm Plot"}</strong>
                          </td>
                          <td>{n.eventDate}</td>
                          <td>
                            <strong>{n.payload?.title || n.kind}</strong>
                            <p className="table-sub">{n.payload?.suggestedAction || n.payload?.evidence}</p>
                          </td>
                          <td>
                            <span className="status-badge delivered">
                              {n.delivery?.status || "delivered"}
                            </span>
                          </td>
                          <td>{n.delivery?.channel || "In-App"}</td>
                        </tr>
                      ))}
                      {notifications.length === 0 && (
                        <tr>
                          <td colSpan={6} className="text-center">
                            No alerts found. Click 'Trigger Real-Time Weather Push' to test!
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Delivery History Log */}
              <div className="deliveries-log-section">
                <h3>Telegram Delivery Outbox Log</h3>
                <div className="deliveries-grid">
                  {deliveries.slice(0, 5).map((d, i) => (
                    <div key={i} className="delivery-card">
                      <div className="deliv-top">
                        <span className="deliv-id">Delivery #{d.deliveryId?.slice(0, 8)}</span>
                        <span className={`deliv-status ${d.status}`}>{d.status}</span>
                      </div>
                      <p>
                        <strong>Attempts:</strong> {d.attempts} | <strong>Msg ID:</strong>{" "}
                        {d.telegramMessageId ?? "Pending"}
                      </p>
                      <small>Timestamp: {d.updatedAt || "Just now"}</small>
                    </div>
                  ))}
                  {deliveries.length === 0 && (
                    <p className="no-events">No delivery logs recorded yet.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ========================================================
              10. SHARED WATER LEDGER
              ======================================================== */}
          {currentTab === "water" && <div className="tab-pane water-pane"><ResourcePanel farm={farm} /></div>}
          </>}
        </main>
      </div>
    </div>
  );
}
