import { useEffect, useState } from "react";
import { apiClient, CropInteraction, CropResolution, Farm } from "../services/apiClient";
import { ConnectedCalendar } from "./ConnectedCalendar";
import { PlotAdvisory } from "./PlotAdvisory";
import { PitchAlertControl } from "./PitchAlertControl";
import { ResourcePanel } from "./resources";
import { ErrorState, LoadingState } from "./ui";
import { DashboardLivingField, FutureFold, Timeline } from "./scenario";
import { farmOptionLabel } from "./farmLabels";
import { ExampleField } from "./living-field/fieldState";
import type { FieldSide } from "./living-field/LivingFieldScene";
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
  const locationParams = new URLSearchParams(window.location.search);
  const plotChoice = locationParams.get("plotId") || "";
  const [foldSide, setFoldSide] = useState<FieldSide>(() =>
    new URLSearchParams(window.location.search).get("side") === "alternative" ? "alternative" : "original");
  const [allFarms, setAllFarms] = useState<Farm[]>();
  const [error, setError] = useState("");
  const farm = allFarms?.find((item) => item.farmId === farmId) ?? (explicitFarm ? undefined : allFarms?.[0]);
  const selectedFarmId = farm?.farmId ?? "";
  const setCurrentTab = (tab: string) => {
    const params = new URLSearchParams({ tab });
    if (selectedFarmId || farmId) params.set("farmId", selectedFarmId || farmId);
    if (selectedPlotId) params.set("plotId", selectedPlotId);
    navigate(`/dashboard?${params}`);
  };

  // Section States
  const setSelectedPlotId = (plotId: string) =>
    navigate(`/dashboard?${new URLSearchParams({ farmId: selectedFarmId, tab: currentTab, plotId })}`);
  const selectedPlotId = (farm?.plots.find((plot) => plot.plotId === plotChoice) ?? farm?.plots[0])?.plotId ?? "";
  const [notifications, setNotifications] = useState<Awaited<ReturnType<typeof apiClient.listNotifications>>["notifications"]>();
  const [telegramByFarm, setTelegramByFarm] = useState<Record<string, Awaited<ReturnType<typeof apiClient.getTelegramStatus>> | null>>({});
  const [deliveries, setDeliveries] = useState<Awaited<ReturnType<typeof apiClient.getDeliveries>>["deliveries"]>();
  const [alertErrors, setAlertErrors] = useState<string[]>([]);
  const [alertsRefresh, refreshAlerts] = useState(0);
  const telegramStatus = telegramByFarm[selectedFarmId];

  // Crop Lens State
  const [cropQuery, setCropQuery] = useState("Turmeric");
  const [cropLanguage, setCropLanguage] = useState<"en" | "kn" | "hi">(
    locale === "kn" || locale === "hi" ? locale : "en"
  );
  const [cropResolution, setCropResolution] = useState<CropInteraction | CropResolution>();
  const [cropError, setCropError] = useState("");
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
    if (!allFarms?.length) return;
    let active = true;
    const selected = allFarms.find((item) => item.farmId === selectedFarmId);
    const farmsToCheck = allFarms.filter((item) => item === selected ||
      allFarms.some((other) => other !== item && other.name.trim().toLowerCase() === item.name.trim().toLowerCase()));
    for (const item of farmsToCheck) {
      apiClient.getTelegramStatus(item.farmId)
        .then((status) => { if (active) setTelegramByFarm((previous) => ({ ...previous, [item.farmId]: status })); })
        .catch(() => { if (active) setTelegramByFarm((previous) => ({ ...previous, [item.farmId]: null })); });
    }
    return () => { active = false; };
  }, [allFarms, selectedFarmId, alertsRefresh]);

  useEffect(() => {
    if (!selectedFarmId || (currentTab !== "overview" && currentTab !== "notifications")) return;
    let active = true;
    Promise.allSettled([
      apiClient.listNotifications(selectedFarmId),
      apiClient.getDeliveries(selectedFarmId),
    ]).then(([notices, history]) => {
      if (!active) return;
      setNotifications(notices.status === "fulfilled" ? notices.value.notifications : undefined);
      setDeliveries(history.status === "fulfilled" ? history.value.deliveries : undefined);
      setAlertErrors([
        ...(notices.status === "rejected" ? ["Farm alerts could not be loaded."] : []),
        ...(history.status === "rejected" ? ["Telegram delivery history could not be loaded."] : []),
      ]);
    });
    return () => { active = false; };
  }, [selectedFarmId, currentTab, alertsRefresh]);

  const handleResolveCrop = async () => {
    const query = cropQuery.trim();
    if (!query || cropResolving) return;
    setCropResolving(true);
    setCropError("");
    setCropResolution(undefined);
    try {
      setCropResolution(await apiClient.interactCrop({ query, language: cropLanguage }));
    } catch {
      try {
        setCropResolution(await apiClient.resolveCrop(query));
      } catch {
        setCropError("Crop lookup is unavailable. Try again in a moment.");
      }
    } finally {
      setCropResolving(false);
    }
  };

  const resolvedCrop = cropResolution && ("resolutionStatus" in cropResolution
    ? cropResolution.resolvedCrop : cropResolution.crop);
  const cropResponse = cropResolution && ("resolutionStatus" in cropResolution
    ? cropResolution.responseText : cropResolution.message);
  const cropSources = cropResolution && "resolutionStatus" in cropResolution ? cropResolution.sources : [];

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
      {/* Farm, atmosphere and language controls */}
      <header className="dash-topbar">
        <div className="topbar-left">
          <button className="topbar-brand" onClick={() => navigate("/")}>
            <span className="brand-gem">◈</span>
            <span className="brand-title">{tUI(locale, "brand")}</span>
          </button>

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
                    {farmOptionLabel(f)}{telegramByFarm[f.farmId]?.connected ? " · Telegram linked" : ""}
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
            ← Home
          </button>
        </div>
      </header>

      {/* Main Layout: Sidebar Navigation + Content Area */}
      <div className="dash-body">
        <aside className="dash-sidebar">
          <nav className="dash-nav" aria-label="Farm workspace">
            <button
              className={`nav-item ${currentTab === "overview" ? "active" : ""}`}
              aria-current={currentTab === "overview" ? "page" : undefined}
              onClick={() => setCurrentTab("overview")}
            >
              <span className="nav-icon">⌂</span>
              <span className="nav-text">{tUI(locale, "tabOverview")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "advisory" ? "active" : ""}`}
              aria-current={currentTab === "advisory" ? "page" : undefined}
              onClick={() => setCurrentTab("advisory")}
            >
              <span className="nav-icon">🌾</span>
              <span className="nav-text">{tUI(locale, "tabAdvisory")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "observatory" ? "active" : ""}`}
              aria-current={currentTab === "observatory" ? "page" : undefined}
              onClick={() => setCurrentTab("observatory")}
            >
              <span className="nav-icon">🛰</span>
              <span className="nav-text">{tUI(locale, "tabObservatory")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "crop-lens" ? "active" : ""}`}
              aria-current={currentTab === "crop-lens" ? "page" : undefined}
              onClick={() => setCurrentTab("crop-lens")}
            >
              <span className="nav-icon">🔍</span>
              <span className="nav-text">{tUI(locale, "tabCropPlanning")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "calendar" ? "active" : ""}`}
              aria-current={currentTab === "calendar" ? "page" : undefined}
              onClick={() => setCurrentTab("calendar")}
            >
              <span className="nav-icon">📅</span>
              <span className="nav-text">{tUI(locale, "tabCalendar")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "future-fold" ? "active" : ""}`}
              aria-current={currentTab === "future-fold" ? "page" : undefined}
              onClick={() => setCurrentTab("future-fold")}
            >
              <span className="nav-icon">↗</span>
              <span className="nav-text">{tUI(locale, "tabFutureFold")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "living-field" ? "active" : ""}`}
              aria-current={currentTab === "living-field" ? "page" : undefined}
              onClick={() => setCurrentTab("living-field")}
            >
              <span className="nav-icon">🌱</span>
              <span className="nav-text">{tUI(locale, "tabLivingField")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "timeline" ? "active" : ""}`}
              aria-current={currentTab === "timeline" ? "page" : undefined}
              onClick={() => setCurrentTab("timeline")}
            >
              <span className="nav-icon">⏱</span>
              <span className="nav-text">{tUI(locale, "tabSavedDecisions")}</span>
            </button>
            <button
              className={`nav-item ${currentTab === "notifications" ? "active" : ""}`}
              aria-current={currentTab === "notifications" ? "page" : undefined}
              onClick={() => setCurrentTab("notifications")}
            >
              <span className="nav-icon">🔔</span>
              <span className="nav-text">Alerts & Telegram</span>
              {Boolean(notifications?.length) && (
                <span className="nav-counter">{notifications?.length}</span>
              )}
            </button>
            <button
              className={`nav-item ${currentTab === "water" ? "active" : ""}`}
              aria-current={currentTab === "water" ? "page" : undefined}
              onClick={() => setCurrentTab("water")}
            >
              <span className="nav-icon">💧</span>
              <span className="nav-text">Water Ledger</span>
            </button>
          </nav>

          <div className="sidebar-footer">
            <div className="farm-info-chip">
              <span className="chip-label">Selected farm</span>
              <strong>{farm?.name || "No farm selected"}</strong>
              <small>
                {farm ? farmOptionLabel(farm, false) : "Choose a saved farm"}
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
            <div className="quick-actions">
              <button className="inspect-plot-btn" onClick={() => navigate("/register")}>Register farm</button>
              <button className="inspect-plot-btn" onClick={() => setCurrentTab("living-field")}>Explore an example field</button>
            </div>
            {currentTab === "living-field" && <ExampleField />}
          </section>}
          {farm && <>
          {currentTab === "overview" && (
            <div className="tab-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Farm Decision Workspace</span>
                  <h2>{farm?.name}</h2>
                  <p className="subtitle">
                    {farmOptionLabel(farm, false)}
                  </p>
                </div>
                <div className="quick-actions">
                  <button className="inspect-plot-btn" onClick={() => navigate(farmPath)}>Manage farm & plots</button>
                  <button className="inspect-plot-btn" onClick={() => setCurrentTab("calendar")}>Agricultural Calendar</button>
                  <button className="inspect-plot-btn" onClick={() => setCurrentTab("notifications")}>
                    {telegramStatus?.connected ? "Telegram linked · Alerts" : "Alerts & Telegram"}
                  </button>
                </div>
              </div>
              <div className="kpi-grid">
                <div className="kpi-card">
                  <span className="kpi-title">Farm size and plots</span>
                  <div className="kpi-val">{farm.plots.length} {farm.plots.length === 1 ? "plot" : "plots"}</div>
                  <span className="kpi-sub">{(totalFarmAreaM2 / 10000).toFixed(2)} ha</span>
                </div>
              </div>
              <PitchAlertControl key={selectedFarmId} farmId={selectedFarmId} onDelivered={() => refreshAlerts((value) => value + 1)} />

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
                  {notifications?.slice(0, 3).map((alert) => (
                    <div key={alert.id} className={`alert-row ${alert.category}`}>
                      <div className="alert-meta">
                        <span className="alert-cat-tag">{alert.category}</span>
                        <span className="alert-date">{alert.eventDate}</span>
                        <span className="alert-status-tag">{alert.delivery?.status?.replaceAll("_", " ") || "Status unavailable"}</span>
                      </div>
                      <div className="alert-text">
                        <strong>{alert.payload?.title || alert.kind}</strong>
                        <p>{alert.payload?.suggestedAction || alert.payload?.evidence}</p>
                      </div>
                    </div>
                  ))}
                  {notifications?.length === 0 && (
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
              {farm.plots.length > 1 && <label>Plot <select value={selectedPlotId} onChange={(event) => setSelectedPlotId(event.target.value)}>
                {farm.plots.map((plot) => <option key={plot.plotId} value={plot.plotId}>{plot.management?.plotName || plot.cropCanonicalName}</option>)}
              </select></label>}
              <button className="inspect-plot-btn" onClick={() => selectedPlotId ? openPlotView("environment") : navigate(farmPath + "/plots/new")}>
                {selectedPlotId ? "Open plot evidence" : "Add a crop plot"}
              </button>
            </div>
          )}

          {currentTab === "crop-lens" && (
            <div className="tab-pane crop-lens-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Multilingual Botanical Resolution</span>
                  <h2>Crop Planning & Crop Lens</h2>
                  <p className="subtitle">
                    Look up a crop to see its scientific identity and available model outputs.
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

                <form className="search-bar-row" onSubmit={(event) => { event.preventDefault(); void handleResolveCrop(); }}>
                  <input
                    className="crop-input"
                    value={cropQuery}
                    onChange={(e) => setCropQuery(e.target.value)}
                    placeholder="Enter crop common name, vernacular alias, or scientific name..."
                    aria-label="Crop name"
                    disabled={cropResolving}
                  />
                  <button
                    className="resolve-btn"
                    disabled={cropResolving || !cropQuery.trim()}
                    type="submit"
                  >
                    {cropResolving ? "Resolving…" : "Resolve Identity & Engine ↗"}
                  </button>
                </form>

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

              {cropError && <ErrorState label={cropError} />}
              {cropResolution && <div className="resolution-card" aria-live="polite">
                {resolvedCrop ? <>
                  <div className="res-header">
                    <div>
                      <h3>{resolvedCrop.canonicalName}</h3>
                      {resolvedCrop.scientificName && <p className="sci-name"><em>{resolvedCrop.scientificName}</em></p>}
                    </div>
                  </div>
                  <div className="res-grid">
                    <div className="res-col">
                      {resolvedCrop.family && <p>Family · {resolvedCrop.family}</p>}
                      {resolvedCrop.matchedAlias && <p>Matched name · {resolvedCrop.matchedAlias}</p>}
                      {Boolean(cropSources.length) && <p>Sources · {cropSources.join(", ")}</p>}
                    </div>
                    <div className="res-col">
                      <h4>Model capability</h4>
                      <p>{resolvedCrop.selectedEngine === "identity/ecology-only" ? "Crop identity and ecology" : resolvedCrop.selectedEngine || "Model unavailable"} {resolvedCrop.engineVersion}</p>
                      {Boolean(resolvedCrop.supportedOutputs?.length) && <p>Supported outputs · {resolvedCrop.supportedOutputs?.join(", ")}</p>}
                    </div>
                  </div>
                  <button className="primary-button" onClick={() => navigate(farmPath + "/plots/new?" + new URLSearchParams({ crop: resolvedCrop.canonicalName }))}>
                    Add plot with {resolvedCrop.canonicalName}
                  </button>
                </> : <h3>Crop needs a closer match</h3>}
                {cropResponse && <p className="indic-response-box">{cropResponse}</p>}
                {!resolvedCrop && Boolean(cropResolution.candidates?.length) && <div className="sample-chips">
                  {cropResolution.candidates?.map((candidate) => <button key={candidate.cropId} onClick={() => setCropQuery(candidate.canonicalName)}>{candidate.canonicalName}</button>)}
                </div>}
              </div>}
            </div>
          )}

          {/* ========================================================
              5. AGRICULTURAL CALENDAR 2.0
              ======================================================== */}
          {currentTab === "calendar" && <div className="tab-pane calendar-pane">
            <ConnectedCalendar key={selectedFarmId} farmId={selectedFarmId} navigate={navigate} />
          </div>}

          {["living-field", "future-fold", "timeline"].includes(currentTab) && (
            <div className="tab-pane">
              {farm.plots.length > 1 && <label>Plot <select value={selectedPlotId} onChange={(event) => setSelectedPlotId(event.target.value)}>
                {farm.plots.map((plot) => <option key={plot.plotId} value={plot.plotId}>{plot.management?.plotName || plot.cropCanonicalName}</option>)}
              </select></label>}
              {!selectedPlotId && <button className="inspect-plot-btn" onClick={() => navigate(farmPath + "/plots/new")}>Add a crop plot</button>}
              {selectedPlotId && currentTab === "living-field" && <div className="living-scene-container">
                <DashboardLivingField key={selectedPlotId} farmId={selectedFarmId} plotId={selectedPlotId} side={foldSide}
                  onChangeSide={setFoldSide} onSelectPlot={setSelectedPlotId} />
              </div>}
              {selectedPlotId && currentTab === "future-fold" && <FutureFold key={selectedPlotId}
                farmId={selectedFarmId} plotId={selectedPlotId} navigate={navigate}
                onOpenLivingField={(side) => { setFoldSide(side); setCurrentTab("living-field"); }} />}
              {selectedPlotId && currentTab === "timeline" && <Timeline key={selectedPlotId} farmId={selectedFarmId} plotId={selectedPlotId} navigate={navigate} />}
            </div>
          )}

          {currentTab === "notifications" && (
            <div className="tab-pane notifications-pane">
              <div className="pane-header">
                <div>
                  <h2>Farm Alerts & Telegram</h2>
                  <p className="subtitle">
                    Telegram delivers eligible notices from daily evidence and calendar checks.
                  </p>
                </div>
              </div>
              <PitchAlertControl key={selectedFarmId} farmId={selectedFarmId} onDelivered={() => refreshAlerts((value) => value + 1)} />

              {/* Telegram Connection Widget */}
              <div className="telegram-widget-card">
                <div className="tg-icon-wrap">✈</div>
                <div className="tg-info">
                  <h3>Telegram Farmer Alert Gateway</h3>
                  <p>
                    Status:{" "}
                    <strong className="text-good">
                      {telegramStatus === null ? "Status unavailable" : !telegramStatus ? "Checking…" : telegramStatus.connected ? "Connected" : "Not connected"}
                    </strong>{" "}
                   {telegramStatus?.botUsername && <> · Bot: <strong>@{telegramStatus.botUsername}</strong></>}
                  </p>
                  <p className="tg-desc">
                    Delivery depends on your subscription and the evidence available for this farm.
                  </p>
                </div>
                <div className="tg-cta">
                  <button className="tg-connect-btn" onClick={() => navigate(farmPath)}>
                    {telegramStatus?.connected ? "Manage farm" : "Open Telegram settings"}
                  </button>
                </div>
              </div>

              {/* Active Alerts List */}
              <div className="alerts-full-section">
                <h3>Farm alerts</h3>
                {alertErrors.map((item) => <ErrorState key={item} label={item} />)}
                {(alertErrors.length > 0 || telegramStatus === null) &&
                  <button className="secondary-button" onClick={() => refreshAlerts((value) => value + 1)}>Refresh alerts</button>}
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
                      {notifications?.map((n) => (
                        <tr key={n.id}>
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
                            <span className={`status-badge ${n.delivery?.status || ""}`}>
                              {n.delivery?.status?.replaceAll("_", " ") || "Status unavailable"}
                            </span>
                          </td>
                          <td>{n.delivery?.channel || "—"}</td>
                        </tr>
                      ))}
                      {notifications?.length === 0 && (
                        <tr>
                          <td colSpan={6} className="text-center">
                            No alerts have been recorded for this farm.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Delivery History Log */}
              <div className="deliveries-log-section">
                <h3>Telegram delivery history</h3>
                <div className="deliveries-grid">
                  {deliveries?.slice(0, 5).map((d) => (
                    <div key={d.deliveryId} className="delivery-card">
                      <div className="deliv-top">
                        <span className="deliv-id">Delivery #{d.deliveryId?.slice(0, 8)}</span>
                        <span className={`deliv-status ${d.status}`}>{d.status}</span>
                      </div>
                      <p>
                        <strong>Attempts:</strong> {d.attempts} | <strong>Msg ID:</strong>{" "}
                        {d.telegramMessageId ?? "Pending"}
                      </p>
                      <small>Timestamp: {d.updatedAt ? new Date(d.updatedAt).toLocaleString() : "Unavailable"}</small>
                    </div>
                  ))}
                  {deliveries?.length === 0 && (
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
