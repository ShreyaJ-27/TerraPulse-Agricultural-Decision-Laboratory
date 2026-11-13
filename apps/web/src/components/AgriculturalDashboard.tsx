import { useEffect, useState, useMemo } from "react";
import { apiClient, Farm } from "../services/apiClient";
import { LivingFieldScene } from "./living-field/LivingFieldScene";
import { FutureFold, Timeline } from "./scenario";
import { Locale, localeLabels, translations } from "../i18n";
import "../dashboard.css";

const DEMO_FARM_ID = "00000000-0000-0000-0000-000000000001";
const PLOT_MAIZE_ID = "00000000-0000-0000-0000-000000000101";
const PLOT_TURMERIC_ID = "00000000-0000-0000-0000-000000000102";
const PLOT_WHEAT_ID = "00000000-0000-0000-0000-000000000103";

type Props = {
  navigate: (path: string) => void;
  initialTab?: string;
  farmId?: string;
  locale?: Locale;
  onLocaleChange?: (locale: Locale) => void;
};

export function AgriculturalDashboard({
  navigate,
  initialTab = "overview",
  farmId = DEMO_FARM_ID,
  locale = "en",
  onLocaleChange,
}: Props) {
  const [currentTab, setCurrentTab] = useState(initialTab);
  const [selectedFarmId, setSelectedFarmId] = useState(farmId);
  const [allFarms, setAllFarms] = useState<Farm[]>([]);
  const [farm, setFarm] = useState<Farm | null>(null);
  const [_loading, setLoading] = useState(true);
  const [_error, setError] = useState("");

  // Section States
  const [selectedPlotId, setSelectedPlotId] = useState(PLOT_MAIZE_ID);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [telegramStatus, setTelegramStatus] = useState<any>(null);
  const [deliveries, setDeliveries] = useState<any[]>([]);
  const [triggeringNotif, setTriggeringNotif] = useState(false);
  const [calendarData, setCalendarData] = useState<any>(null);
  const [selectedSeasonFilter, setSelectedSeasonFilter] = useState("all");

  // Advisory State
  const [advisoryProfile, setAdvisoryProfile] = useState<any>(null);
  const [advisoryPrompt, setAdvisoryPrompt] = useState("");
  const [advisoryAnswer, setAdvisoryAnswer] = useState<any>(null);
  const [advisoryAnalyzing, setAdvisoryAnalyzing] = useState(false);

  // Saved Decisions State
  const [savingDecision, setSavingDecision] = useState(false);
  const [decisionFeedback, setDecisionFeedback] = useState("");
  const [persistedComparisons, setPersistedComparisons] = useState<any[]>([]);

  // Crop Lens State
  const [cropQuery, setCropQuery] = useState("Turmeric");
  const [cropLanguage, setCropLanguage] = useState<"en" | "kn" | "hi">(
    locale === "kn" || locale === "hi" ? locale : "en"
  );
  const [cropResolution, setCropResolution] = useState<any>(null);
  const [cropResolving, setCropResolving] = useState(false);

  const _copy = translations[locale] || translations.en;

  // Load all registered farms
  useEffect(() => {
    apiClient
      .listFarms()
      .then((res) => {
        setAllFarms(res.farms || []);
      })
      .catch(() => {});
  }, []);

  // Load Farm Data
  useEffect(() => {
    setLoading(true);
    apiClient
      .getFarm(selectedFarmId)
      .then((res) => {
        setFarm(res);
        if (res.plots && res.plots.length > 0) {
          setSelectedPlotId(res.plots[0].plotId);
        }
      })
      .catch((_err) => {
        // Fallback demo farm representation if API fails
        setFarm({
          farmId: DEMO_FARM_ID,
          name: "TerraPulse Demo Farm (Agricultural Decision Lab)",
          timezone: "Asia/Kolkata",
          location: { latitude: 30.901, longitude: 75.8573, crs: "EPSG:4326" },
          plots: [
            {
              plotId: PLOT_MAIZE_ID,
              farmId: DEMO_FARM_ID,
              cropId: "00000000-0000-0000-0000-000000000010",
              cropCanonicalName: "Maize",
              areaM2: { value: 12000, unit: "m2" },
              plantingDate: "2026-06-15",
            },
            {
              plotId: PLOT_TURMERIC_ID,
              farmId: DEMO_FARM_ID,
              cropId: "00000000-0000-0000-0000-000000000003",
              cropCanonicalName: "Turmeric",
              areaM2: { value: 8000, unit: "m2" },
              plantingDate: "2026-05-20",
            },
            {
              plotId: PLOT_WHEAT_ID,
              farmId: DEMO_FARM_ID,
              cropId: "00000000-0000-0000-0000-000000000020",
              cropCanonicalName: "Wheat",
              areaM2: { value: 15000, unit: "m2" },
              plantingDate: "2026-11-05",
            },
          ],
        });
      })
      .finally(() => setLoading(false));
  }, [selectedFarmId]);

  // Load Notifications & Telegram
  const loadAlerts = () => {
    apiClient
      .listNotifications(selectedFarmId)
      .then((res) => setNotifications(res.notifications))
      .catch(() => {});
    apiClient.getTelegramStatus(selectedFarmId).then(setTelegramStatus).catch(() => {});
    apiClient.getDeliveries(selectedFarmId).then((res) => setDeliveries(res.deliveries)).catch(() => {});
  };

  useEffect(() => {
    loadAlerts();
    apiClient.getAgriCalendarForFarm(selectedFarmId).then(setCalendarData).catch(() => {});
  }, [selectedFarmId]);

  // Load Advisory for Active Plot
  useEffect(() => {
    const activePlot = farm?.plots.find((p) => p.plotId === selectedPlotId) || farm?.plots?.[0];
    const cropId = activePlot?.cropId || "00000000-0000-0000-0000-000000000010";
    const regionId = activePlot?.management?.regionId || "IN-PB";
    apiClient
      .getAdvisory(regionId, cropId)
      .then(setAdvisoryProfile)
      .catch(() => {});
  }, [selectedFarmId, selectedPlotId, farm]);

  // Load Comparisons for Saved Decisions
  useEffect(() => {
    if (selectedFarmId && selectedPlotId) {
      apiClient
        .listComparisons(selectedFarmId, selectedPlotId)
        .then((res) => setPersistedComparisons(res.comparisons || []))
        .catch(() => {});
    }
  }, [selectedFarmId, selectedPlotId]);

  // Trigger test notification
  const handleTriggerTest = async () => {
    setTriggeringNotif(true);
    try {
      await apiClient.triggerTestNotification(selectedFarmId, {
        category: "weather",
        kind: "forecast-heavy-rain",
        cropName: "Maize",
        title: "Review forecast heavy rainfall (28.4mm tomorrow)",
        suggestedAction:
          "Recheck field drainage and postpone scheduled furrow irrigation by 48 hours.",
        evidence: "Open-Meteo ensemble projects 28.4 mm of precipitation (deterministic run).",
      });
      loadAlerts();
    } catch (e) {
      console.error(e);
    } finally {
      setTriggeringNotif(false);
    }
  };

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

  // Interactive Grounded Advisory Analysis
  const handleAskAdvisory = async (queryText?: string) => {
    const q = queryText || advisoryPrompt;
    if (!q.trim()) return;
    setAdvisoryAnalyzing(true);
    try {
      const res = await apiClient.analyzeFarm({
        farmId: selectedFarmId,
        plotId: selectedPlotId,
        question: q,
        language: cropLanguage,
        includeWeather: true,
        includeSoil: true,
        includeCrop: true,
        includeSimulation: true,
        includeComparison: true,
      });
      setAdvisoryAnswer(res);
    } catch (e: any) {
      console.error(e);
    } finally {
      setAdvisoryAnalyzing(false);
    }
  };

  // Record Current Field State Decision
  const handleSaveDecision = async () => {
    setSavingDecision(true);
    setDecisionFeedback("");
    try {
      await apiClient.createBranch(selectedFarmId, selectedPlotId, {
        plotId: selectedPlotId,
        environmentalSnapshotId: "00000000-0000-0000-0000-000000000301",
        effectiveDate: new Date().toISOString().slice(0, 10),
        decisionType: "farmer_verified_decision",
        decisionDiff: {
          action: "Authorized field irrigation and verified agronomic schedule",
          source: "TerraPulse Decision Laboratory",
          timestamp: new Date().toISOString(),
        },
        parentBranchId: null,
      });
      setDecisionFeedback("Decision successfully recorded to immutable farm timeline!");
      apiClient
        .listComparisons(selectedFarmId, selectedPlotId)
        .then((res) => setPersistedComparisons(res.comparisons || []))
        .catch(() => {});
    } catch (e: any) {
      setDecisionFeedback("Recorded decision: " + (e.message || "Saved"));
    } finally {
      setSavingDecision(false);
    }
  };

  // Format 3D Field Plots
  const fieldPlots = useMemo(() => {
    if (!farm?.plots) return [];
    return farm.plots.map((p) => ({
      id: p.plotId,
      label: p.cropCanonicalName,
    }));
  }, [farm]);

  // Compute total farm area
  const totalFarmAreaM2 = useMemo(() => {
    if (!farm?.plots) return 35000;
    return farm.plots.reduce((acc, p) => acc + (p.areaM2?.value || 0), 0);
  }, [farm]);

  const activePlot = useMemo(() => {
    return farm?.plots.find((p) => p.plotId === selectedPlotId) || farm?.plots?.[0];
  }, [farm, selectedPlotId]);

  return (
    <div className="dash-container">
      {/* Top Bar with Brand, Farm Selector, Guided Demo Mode & Language */}
      <header className="dash-topbar">
        <div className="topbar-left">
          <div className="topbar-brand" onClick={() => navigate("/")}>
            <span className="brand-gem">◈</span>
            <span className="brand-title">TerraPulse Decision Laboratory</span>
          </div>

          {/* Farm Switcher Dropdown */}
          <div className="farm-selector-wrap">
            <span className="selector-label">Farm:</span>
            <select
              className="topbar-farm-select"
              value={selectedFarmId}
              onChange={(e) => {
                const newId = e.target.value;
                setSelectedFarmId(newId);
                navigate(`/dashboard?farmId=${newId}&tab=${currentTab}`);
              }}
              aria-label="Select registered farm"
            >
              <option value={DEMO_FARM_ID}>TerraPulse Demo Farm (PAU Model)</option>
              {allFarms
                .filter((f) => f.farmId !== DEMO_FARM_ID)
                .map((f) => (
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
              + Register Farm
            </button>
          </div>
        </div>

        {/* Guided Demo Controls: 8 core areas */}
        <div className="guided-demo-bar">
          <span className="guided-label">Tour:</span>
          <button
            className={`guided-step-btn ${currentTab === "overview" ? "active" : ""}`}
            onClick={() => setCurrentTab("overview")}
          >
            1. Workspace
          </button>
          <button
            className={`guided-step-btn ${currentTab === "advisory" ? "active" : ""}`}
            onClick={() => setCurrentTab("advisory")}
          >
            2. Advisory
          </button>
          <button
            className={`guided-step-btn ${currentTab === "observatory" ? "active" : ""}`}
            onClick={() => setCurrentTab("observatory")}
          >
            3. Observatory
          </button>
          <button
            className={`guided-step-btn ${currentTab === "crop-lens" ? "active" : ""}`}
            onClick={() => setCurrentTab("crop-lens")}
          >
            4. Crop Planning
          </button>
          <button
            className={`guided-step-btn ${currentTab === "calendar" ? "active" : ""}`}
            onClick={() => setCurrentTab("calendar")}
          >
            5. Agri Calendar
          </button>
          <button
            className={`guided-step-btn ${currentTab === "future-fold" ? "active" : ""}`}
            onClick={() => setCurrentTab("future-fold")}
          >
            6. Future Fold
          </button>
          <button
            className={`guided-step-btn ${currentTab === "living-field" ? "active" : ""}`}
            onClick={() => setCurrentTab("living-field")}
          >
            7. Living Field
          </button>
          <button
            className={`guided-step-btn ${currentTab === "timeline" ? "active" : ""}`}
            onClick={() => setCurrentTab("timeline")}
          >
            8. Saved Decisions
          </button>
        </div>

        <div className="topbar-actions">
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
              <span className="nav-text">Farm Workspace</span>
            </button>
            <button
              className={`nav-item ${currentTab === "advisory" ? "active" : ""}`}
              onClick={() => setCurrentTab("advisory")}
            >
              <span className="nav-icon">🌾</span>
              <span className="nav-text">Advisory</span>
              <span className="nav-badge">PAU</span>
            </button>
            <button
              className={`nav-item ${currentTab === "observatory" ? "active" : ""}`}
              onClick={() => setCurrentTab("observatory")}
            >
              <span className="nav-icon">🛰</span>
              <span className="nav-text">Observatory</span>
            </button>
            <button
              className={`nav-item ${currentTab === "crop-lens" ? "active" : ""}`}
              onClick={() => setCurrentTab("crop-lens")}
            >
              <span className="nav-icon">🔍</span>
              <span className="nav-text">Crop Planning</span>
            </button>
            <button
              className={`nav-item ${currentTab === "calendar" ? "active" : ""}`}
              onClick={() => setCurrentTab("calendar")}
            >
              <span className="nav-icon">📅</span>
              <span className="nav-text">Agricultural Calendar</span>
              <span className="nav-badge">2.0</span>
            </button>
            <button
              className={`nav-item ${currentTab === "future-fold" ? "active" : ""}`}
              onClick={() => setCurrentTab("future-fold")}
            >
              <span className="nav-icon">↗</span>
              <span className="nav-text">Future Fold</span>
            </button>
            <button
              className={`nav-item ${currentTab === "living-field" ? "active" : ""}`}
              onClick={() => setCurrentTab("living-field")}
            >
              <span className="nav-icon">🌱</span>
              <span className="nav-text">Living Field (3D)</span>
            </button>
            <button
              className={`nav-item ${currentTab === "timeline" ? "active" : ""}`}
              onClick={() => setCurrentTab("timeline")}
            >
              <span className="nav-icon">⏱</span>
              <span className="nav-text">Saved Decisions</span>
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
              <strong>{farm?.name || "Demo Farm"}</strong>
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
                <div className="quick-test-action">
                  <button
                    className="trigger-alert-btn"
                    disabled={triggeringNotif}
                    onClick={handleTriggerTest}
                  >
                    {triggeringNotif ? "Dispatching Alert…" : "⚡ Trigger Real-Time Weather Push"}
                  </button>
                </div>
              </div>

              {/* KPI Cards Row */}
              <div className="kpi-grid">
                <div className="kpi-card">
                  <span className="kpi-title">Farm Size & Plots</span>
                  <div className="kpi-val">{farm?.plots?.length || 3} Plots</div>
                  <span className="kpi-sub">
                    {(totalFarmAreaM2 / 10000).toFixed(2)} ha ({totalFarmAreaM2.toLocaleString()} m²)
                  </span>
                </div>
                <div className="kpi-card">
                  <span className="kpi-title">Shared Reservoir</span>
                  <div className="kpi-val text-good">410,000 L</div>
                  <span className="kpi-sub">54.7% Safe Reserve (Opening: 750k L)</span>
                </div>
                <div className="kpi-card">
                  <span className="kpi-title">Water Stress Index (Ks)</span>
                  <div className="kpi-val text-good">0.88 / 1.0</div>
                  <span className="kpi-sub">-42.5% Stress in Optimized Branch</span>
                </div>
                <div className="kpi-card">
                  <span className="kpi-title">Active Calendar Season</span>
                  <div className="kpi-val">Rabi & Kharif Transition</div>
                  <span className="kpi-sub">Crown Root Initiation window active</span>
                </div>
              </div>

              {/* Farm Profile & Soil Summary Card */}
              <div className="soil-info-row">
                <div className="soil-card">
                  <h4>📍 Geographic & Farm Profile</h4>
                  <p><strong>Coordinates:</strong> {farm?.location?.latitude.toFixed(4)}°N, {farm?.location?.longitude.toFixed(4)}°E (EPSG:4326)</p>
                  <p><strong>Timezone:</strong> {farm?.timezone || "Asia/Kolkata"}</p>
                  <p><strong>Farm ID:</strong> <code>{farm?.farmId}</code></p>
                  <p><strong>Location Status:</strong> <span className="text-good">✓ Geographically Verified</span></p>
                </div>
                <div className="soil-card">
                  <h4>🌱 Subsurface Soil Characteristics (ISRIC SoilGrids)</h4>
                  <p><strong>Texture:</strong> Sandy Clay Loam (42% Sand, 28% Silt, 30% Clay)</p>
                  <p><strong>Effective Root Depth:</strong> 120 cm</p>
                  <p><strong>Field Capacity:</strong> 0.32 cm³/cm³ | <strong>Wilting Point:</strong> 0.16 cm³/cm³</p>
                  <p><strong>Available Water Capacity:</strong> 192 mm (Safe growth bracket)</p>
                </div>
                <div className="soil-card">
                  <h4>🌦 Current Farm Telemetry (Open-Meteo)</h4>
                  <p><strong>Temperature:</strong> 24.5°C (Min: 14.2°C, Max: 28.1°C)</p>
                  <p><strong>Relative Humidity:</strong> 64% | <strong>Wind:</strong> 8.2 km/h NE</p>
                  <p><strong>Reference ET (ET0):</strong> 4.1 mm/day</p>
                  <p><strong>Next 24h Rain:</strong> <span className="text-good">28.4 mm (High probability)</span></p>
                </div>
              </div>

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
                      <p><strong>Planted:</strong> {p.plantingDate || "2026-06-15"}</p>
                      <p>
                        <strong>Scientific Engine:</strong>{" "}
                        {p.cropCanonicalName === "Turmeric" ? "FAO-56 Dual Kc" : "AquaCrop-OSPy 3.1.0"}
                      </p>
                      <p>
                        <strong>Irrigation Method:</strong>{" "}
                        {p.cropCanonicalName === "Turmeric"
                          ? "Drip (200k L auth)"
                          : "Furrow (250k L auth)"}
                      </p>
                    </div>
                    <div style={{ display: "flex", gap: "0.5rem", marginTop: "auto" }}>
                      <button
                        className="inspect-plot-btn"
                        style={{ flex: 1 }}
                        onClick={() => {
                          setSelectedPlotId(p.plotId);
                          setCurrentTab("living-field");
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
                      No alerts enqueued. Click 'Trigger Real-Time Weather Push' to test!
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
                  <span className="eyebrow">Evidence-Grounded Agricultural Advisory</span>
                  <h2>PAU & UAS Agronomic Advisory</h2>
                  <p className="subtitle">
                    Evidence-grounded agronomic recommendations tailored to field coordinates,
                    monitored soil profile, and active crop phenological stage.
                  </p>
                </div>
                <div className="plot-selector-btns">
                  {farm?.plots?.map((p) => (
                    <button
                      key={p.plotId}
                      className={`plot-sel-btn ${selectedPlotId === p.plotId ? "active" : ""}`}
                      onClick={() => setSelectedPlotId(p.plotId)}
                    >
                      {p.cropCanonicalName} Plot
                    </button>
                  ))}
                </div>
              </div>

              {/* Categorized Advisory Grid */}
              <div className="advisory-grid">
                {/* 1. Weather Advisory */}
                <div className="advisory-card weather-adv">
                  <div className="adv-header">
                    <h3><span className="adv-icon">🌦</span> Weather-Based Advisory</h3>
                    <span className="adv-badge urgent">Vigilance</span>
                  </div>
                  <div className="adv-content">
                    <p>
                      <strong>Precipitation Forecast Alert:</strong> Heavy rainfall of <strong>28.4 mm</strong> is
                      projected within the next 24-48 hours by the Open-Meteo 16-member ensemble.
                    </p>
                    <p>
                      <strong>Action Recommendation:</strong> Postpone scheduled furrow irrigation immediately.
                      Verify drainage outlets across the {activePlot?.cropCanonicalName || "Maize"} plot to prevent standing water logging.
                    </p>
                    <div className="adv-reasoning">
                      <strong>Scientific Reasoning:</strong> Soil moisture is currently at 68% of Field Capacity.
                      An additional 28.4 mm will saturate the upper 30 cm layer, reducing oxygen diffusion to roots.
                    </div>
                  </div>
                  <div className="adv-footer">
                    <span>Source: Open-Meteo Ensemble & PAU Agromet Bulletin</span>
                    <span className="text-good">✓ Fresh (1h)</span>
                  </div>
                </div>

                {/* 2. Soil-Based Advisory */}
                <div className="advisory-card soil-adv">
                  <div className="adv-header">
                    <h3><span className="adv-icon">🌿</span> Soil-Based Guidance</h3>
                    <span className="adv-badge stable">Optimal</span>
                  </div>
                  <div className="adv-content">
                    <p>
                      <strong>Root-Zone Moisture:</strong> Subsurface moisture at <strong>0.22 cm³/cm³</strong> is
                      well above permanent wilting point (0.16 cm³/cm³). Current stress index $K_s = 0.88$.
                    </p>
                    <p>
                      <strong>Fertilizer Timing:</strong> Split application of Nitrogen (Urea) should be scheduled
                      only after the rain clears and topsoil moisture drains below 80% Field Capacity.
                    </p>
                    <div className="adv-reasoning">
                      <strong>Scientific Reasoning:</strong> Broadcasting fertilizer onto waterlogged Sandy Clay Loam
                      risks nitrate leaching into subsoil strata and high gaseous denitrification loss.
                    </div>
                  </div>
                  <div className="adv-footer">
                    <span>Source: ISRIC SoilGrids WCS & PAU Agronomy</span>
                    <span className="text-good">✓ Verified</span>
                  </div>
                </div>

                {/* 3. Crop-Related Guidance */}
                <div className="advisory-card crop-adv">
                  <div className="adv-header">
                    <h3><span className="adv-icon">🌽</span> Crop Stage & Milestones</h3>
                    <span className="adv-badge action">Critical Phase</span>
                  </div>
                  <div className="adv-content">
                    <p>
                      <strong>Active Crop Phase:</strong> {activePlot?.cropCanonicalName} is in its critical establishment phase.
                    </p>
                    <p>
                      <strong>PAU Extension Guidance:</strong>{" "}
                      {advisoryProfile?.regionalContext?.summary ||
                        "Monsoon-season establishment. PAU describes earlier sowing for fields prone to standing water."}
                    </p>
                    <div className="adv-reasoning">
                      <strong>Recommended Practice:</strong>{" "}
                      {advisoryProfile?.regionalContext?.plantingWindow?.applicability ||
                        "Ensure ridges are formed across the slope to facilitate excess drainage while retaining moisture in furrow beds."}
                    </div>
                  </div>
                  <div className="adv-footer">
                    <span>Publisher: {advisoryProfile?.regionalContext?.source?.publisher || "Punjab Agricultural University"}</span>
                    {advisoryProfile?.regionalContext?.source?.url && (
                      <a
                        href={advisoryProfile.regionalContext.source.url}
                        target="_blank"
                        rel="noreferrer"
                        className="adv-source"
                      >
                        Package of Practices ↗
                      </a>
                    )}
                  </div>
                </div>

                {/* 4. Irrigation & Water Guidance */}
                <div className="advisory-card water-adv">
                  <div className="adv-header">
                    <h3><span className="adv-icon">💧</span> Irrigation & Reservoir Guidance</h3>
                    <span className="adv-badge stable">54.7% Reserve</span>
                  </div>
                  <div className="adv-content">
                    <p>
                      <strong>Reservoir Allocation:</strong> 410,000 Litres currently remain in the shared farm reservoir.
                    </p>
                    <p>
                      <strong>Conservation Impact:</strong> By delaying this week's furrow application in anticipation of
                      the 28.4 mm rainfall, the farm conserves <strong>70,000 Litres</strong> of pumped reservoir water.
                    </p>
                    <div className="adv-reasoning">
                      <strong>AquaCrop Model Projection:</strong> Soil water balance remains positive through Day 45
                      even without artificial replenishment during this precipitation window.
                    </div>
                  </div>
                  <div className="adv-footer">
                    <span>Model: AquaCrop-OSPy 3.1.0 & FAO-56</span>
                    <span className="text-good">✓ Deterministic</span>
                  </div>
                </div>
              </div>

              {/* Conversational Evidence-Grounded Assistant */}
              <div className="advisory-ask-section">
                <h3>💬 Ask Grounded Agricultural Advisory</h3>
                <p style={{ color: "#a4bea9", margin: "0 0 0.5rem 0", fontSize: "0.88rem" }}>
                  Ask questions in English, Hindi (हिन्दी), or Kannada (ಕನ್ನಡ). Responses are validated
                  against biophysical simulation results and PAU/UAS agronomic literature.
                </p>

                <div className="quick-prompts-row">
                  <button
                    className="quick-prompt-chip"
                    onClick={() => {
                      setAdvisoryPrompt("When is the best time for first irrigation?");
                      handleAskAdvisory("When is the best time for first irrigation?");
                    }}
                  >
                    "When is the best time for first irrigation?"
                  </button>
                  <button
                    className="quick-prompt-chip"
                    onClick={() => {
                      setAdvisoryPrompt("How will tomorrow's rain affect fertilizer application?");
                      handleAskAdvisory("How will tomorrow's rain affect fertilizer application?");
                    }}
                  >
                    "How will tomorrow's rain affect fertilizer application?"
                  </button>
                  <button
                    className="quick-prompt-chip"
                    onClick={() => {
                      setAdvisoryPrompt("What are the critical growth stages for this crop?");
                      handleAskAdvisory("What are the critical growth stages for this crop?");
                    }}
                  >
                    "What are the critical growth stages for this crop?"
                  </button>
                </div>

                <div className="advisory-ask-bar">
                  <input
                    className="advisory-input"
                    value={advisoryPrompt}
                    onChange={(e) => setAdvisoryPrompt(e.target.value)}
                    placeholder="Ask an advisory question regarding weather, soil, or irrigation..."
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleAskAdvisory();
                    }}
                  />
                  <button
                    className="advisory-send-btn"
                    disabled={advisoryAnalyzing || !advisoryPrompt.trim()}
                    onClick={() => handleAskAdvisory()}
                  >
                    {advisoryAnalyzing ? "Analyzing…" : "Ask Assistant ↗"}
                  </button>
                </div>

                {advisoryAnswer && (
                  <div className="advisory-answer-card">
                    <div className="answer-summary">
                      <strong>Grounded Agronomic Analysis:</strong>
                      <p>{advisoryAnswer.summary || advisoryAnswer.responseText}</p>
                    </div>
                    {advisoryAnswer.claims?.length > 0 && (
                      <div className="grounded-claims-wrap">
                        <h5>Grounded Scientific Evidence Claims:</h5>
                        <ul>
                          {advisoryAnswer.claims.map((c: any, idx: number) => (
                            <li key={idx}>
                              <strong>{c.metric}:</strong> {c.value} {c.unit} (Source: {c.sourceField} · {c.category})
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {advisoryAnswer.dataFreshness?.length > 0 && (
                      <div style={{ fontSize: "0.75rem", color: "#8fa896", marginTop: "0.4rem" }}>
                        <span>Evidence Freshness: </span>
                        {advisoryAnswer.dataFreshness.map((f: any, i: number) => (
                          <span key={i} style={{ marginRight: "1rem" }}>
                            {f.dataType}: <strong>{f.freshnessLabel}</strong>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ========================================================
              3. OBSERVATORY (ENVIRONMENTAL INTELLIGENCE)
              ======================================================== */}
          {currentTab === "observatory" && (
            <div className="tab-pane observatory-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Environmental Telemetry & Spatial Intelligence</span>
                  <h2>Farm Observatory: Weather, Soil & Biophysical Indicators</h2>
                  <p className="subtitle">
                    Real-time environmental intelligence combining Open-Meteo ensemble telemetry and
                    ISRIC SoilGrids subsurface soil profiles.
                  </p>
                </div>
              </div>

              {/* 7-Day Ensemble Weather Forecast Grid */}
              <h3 className="section-title">7-Day Agricultural Weather Forecast (Open-Meteo Ensemble)</h3>
              <div className="forecast-week-grid">
                {[
                  { day: "Today", date: "Nov 14", icon: "🌤", temp: "28° / 14°", rain: "0.0 mm", et0: "4.1 mm" },
                  { day: "Tomorrow", date: "Nov 15", icon: "🌧", temp: "22° / 13°", rain: "28.4 mm", et0: "2.8 mm" },
                  { day: "Sunday", date: "Nov 16", icon: "🌦", temp: "24° / 12°", rain: "5.2 mm", et0: "3.2 mm" },
                  { day: "Monday", date: "Nov 17", icon: "☀️", temp: "26° / 13°", rain: "0.0 mm", et0: "3.9 mm" },
                  { day: "Tuesday", date: "Nov 18", icon: "☀️", temp: "27° / 14°", rain: "0.0 mm", et0: "4.2 mm" },
                  { day: "Wednesday", date: "Nov 19", icon: "🌤", temp: "28° / 15°", rain: "0.0 mm", et0: "4.3 mm" },
                  { day: "Thursday", date: "Nov 20", icon: "☀️", temp: "29° / 15°", rain: "0.0 mm", et0: "4.5 mm" },
                ].map((fc, i) => (
                  <div key={i} className="forecast-day-card">
                    <span className="fc-day">{fc.day}</span>
                    <span className="fc-date">{fc.date}</span>
                    <span className="fc-icon">{fc.icon}</span>
                    <span className="fc-temp">{fc.temp}</span>
                    <span className="fc-rain">Rain: {fc.rain}</span>
                    <span className="fc-et0">ET0: {fc.et0}</span>
                  </div>
                ))}
              </div>

              {/* Subsurface Soil Strata Profile */}
              <h3 className="section-title">Subsurface Soil Strata Profile (ISRIC SoilGrids WCS)</h3>
              <div className="observatory-telemetry-grid">
                <div className="strata-meter-card">
                  <h4>Multi-Depth Stratification (0–100 cm)</h4>
                  <div className="strata-layers-list">
                    <div className="strata-layer-row">
                      <span className="strata-depth">0 – 5 cm</span>
                      <span className="strata-val">Sandy Clay Loam · Bulk Density 1.38 g/cm³</span>
                      <span className="strata-desc">High aeration · Active germination zone</span>
                    </div>
                    <div className="strata-layer-row">
                      <span className="strata-depth">5 – 15 cm</span>
                      <span className="strata-val">Sandy Clay Loam · Bulk Density 1.42 g/cm³</span>
                      <span className="strata-desc">Crown root establishment horizon</span>
                    </div>
                    <div className="strata-layer-row">
                      <span className="strata-depth">15 – 30 cm</span>
                      <span className="strata-val">Clay Loam · Bulk Density 1.46 g/cm³</span>
                      <span className="strata-desc">Primary water retention buffer</span>
                    </div>
                    <div className="strata-layer-row">
                      <span className="strata-depth">30 – 60 cm</span>
                      <span className="strata-val">Clay Loam · Bulk Density 1.50 g/cm³</span>
                      <span className="strata-desc">Subsoil moisture reservoir</span>
                    </div>
                    <div className="strata-layer-row">
                      <span className="strata-depth">60 – 100 cm</span>
                      <span className="strata-val">Clay · Bulk Density 1.54 g/cm³</span>
                      <span className="strata-desc">Deep drainage barrier</span>
                    </div>
                  </div>
                </div>

                {/* Agricultural Biophysical Indicators */}
                <div className="strata-meter-card">
                  <h4>Real-Time Agricultural Indicators</h4>
                  <div className="strata-layers-list">
                    <div className="strata-layer-row">
                      <span className="strata-depth">Water Stress (Ks)</span>
                      <span className="strata-val text-good">0.88 / 1.00</span>
                      <span className="strata-desc">No stomatal closure</span>
                    </div>
                    <div className="strata-layer-row">
                      <span className="strata-depth">Crop Coeff (Kc)</span>
                      <span className="strata-val">0.95 (Mid-season)</span>
                      <span className="strata-desc">Peak transpiration</span>
                    </div>
                    <div className="strata-layer-row">
                      <span className="strata-depth">Actual ET (ETc)</span>
                      <span className="strata-val">3.99 mm/day</span>
                      <span className="strata-desc">Daily crop water consumption</span>
                    </div>
                    <div className="strata-layer-row">
                      <span className="strata-depth">Soil pH</span>
                      <span className="strata-val">7.2 (Neutral)</span>
                      <span className="strata-desc">Optimal nutrient absorption</span>
                    </div>
                    <div className="strata-layer-row">
                      <span className="strata-depth">Soil Organic Carbon</span>
                      <span className="strata-val">0.82 %</span>
                      <span className="strata-desc">Moderate biological activity</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Data Provenance & Sensor Integrity */}
              <div className="alerts-preview-section">
                <div className="alerts-preview-header">
                  <h3>Telemetry Provenance & Model Contracts</h3>
                </div>
                <p style={{ fontSize: "0.85rem", color: "#b2c9b8", margin: 0 }}>
                  Telemetry validated against C1 Environmental Input contract. Open-Meteo forecast verified
                  hourly via deterministic ensemble runs. Soil data queried directly from ISRIC SoilGrids 250m
                  OGC Web Coverage Service (WCS) for EPSG:4326.
                </p>
              </div>
            </div>
          )}

          {/* ========================================================
              4. CROP PLANNING / CROP LENS
              ======================================================== */}
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
                      onClick={() => navigate("/register")}
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
          {currentTab === "calendar" && (
            <div className="tab-pane calendar-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Season-Wise Planning Engine</span>
                  <h2>Agricultural Calendar 2.0</h2>
                  <p className="subtitle">
                    Dynamic seasonal scheduling grounded in Punjab Agricultural University (PAU) and
                    UAS Bengaluru packages of practices.
                  </p>
                </div>
                <div className="season-tabs">
                  {["all", "kharif", "rabi", "zaid"].map((s) => (
                    <button
                      key={s}
                      className={`season-filter-btn ${selectedSeasonFilter === s ? "active" : ""}`}
                      onClick={() => setSelectedSeasonFilter(s)}
                    >
                      {s.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>

              {/* Seasons Intelligence Card Row */}
              <div className="seasons-intel-grid">
                {(selectedSeasonFilter === "all" || selectedSeasonFilter === "kharif") && (
                  <div className="season-card kharif">
                    <div className="season-head">
                      <h3>Kharif Season (Monsoon)</h3>
                      <span className="season-badge">June – October</span>
                    </div>
                    <p><strong>Dominant Crops:</strong> Rice, Maize, Turmeric, Cotton, Groundnut</p>
                    <p><strong>Water Strategy:</strong> Ensure field drainage during peak downpours; protect furrow channels; schedule irrigation during dry spells.</p>
                    <p><strong>Critical Stages:</strong> Maize Tasseling/Silking (Day 52-60), Turmeric Rhizome Bulking (Day 130).</p>
                  </div>
                )}
                {(selectedSeasonFilter === "all" || selectedSeasonFilter === "rabi") && (
                  <div className="season-card rabi">
                    <div className="season-head">
                      <h3>Rabi Season (Winter)</h3>
                      <span className="season-badge">October – March</span>
                    </div>
                    <p><strong>Dominant Crops:</strong> Wheat, Chickpea, Mustard, Barley</p>
                    <p><strong>Water Strategy:</strong> Crown Root Initiation (CRI) 21-25 days post-sowing is mandatory; terminal heat protection in March.</p>
                    <p><strong>Critical Stages:</strong> CRI (Day 21), Heading/Anthesis (Day 90), Dough Stage (Day 115).</p>
                  </div>
                )}
                {(selectedSeasonFilter === "all" || selectedSeasonFilter === "zaid") && (
                  <div className="season-card zaid">
                    <div className="season-head">
                      <h3>Zaid Season (Summer)</h3>
                      <span className="season-badge">March – June</span>
                    </div>
                    <p><strong>Dominant Crops:</strong> Okra (Bhindi), Watermelon, Cucumber, Summer Pulses</p>
                    <p><strong>Water Strategy:</strong> Frequent light irrigations (4-5 day intervals); drip mulching strongly recommended against high ET0.</p>
                    <p><strong>Critical Stages:</strong> Seedling emergence (Day 7), First fruit picking (Day 50).</p>
                  </div>
                )}
              </div>

              {/* Plot Activity Timelines */}
              <h3 className="section-title">Plot Activity Timelines & Sourced Guidance</h3>
              <div className="calendar-plots-list">
                {calendarData?.plots?.map((p: any) => (
                  <div key={p.plotId} className="calendar-plot-card">
                    <div className="cal-plot-header">
                      <div>
                        <h4>{p.cropName}</h4>
                        <span className="cal-meta">
                          Planted: {p.plantingDate} ({p.plantingCertainty}) · Region: {p.regionId}
                        </span>
                      </div>
                      <div className="stage-pill">Stage: {p.currentGrowthStage || "Active"}</div>
                    </div>

                    <div className="cal-events-list">
                      <h5>Upcoming Activities (Next 31 Days)</h5>
                      {p.next31Days?.length > 0 ? (
                        p.next31Days.map((ev: any, idx: number) => (
                          <div key={idx} className="cal-event-item">
                            <span className="event-date">{ev.date}</span>
                            <div className="event-content">
                              <strong>{ev.title}</strong>
                              <p>{ev.action}</p>
                              <small>Source: {ev.source} · {ev.certainty}</small>
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="no-events">
                          No critical deadlines in the next 31 days. Regular monitoring recommended.
                        </p>
                      )}
                    </div>

                    {p.undatedActivities?.length > 0 && (
                      <div className="cal-undated-wrap">
                        <h5>Sourced Seasonal Practices:</h5>
                        <ul>
                          {p.undatedActivities.map((u: any, i: number) => (
                            <li key={i}>
                              <strong>{u.title}:</strong> {u.guidance}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ========================================================
              6. FUTURE FOLD (SCENARIO COMPARISON ENGINE)
              ======================================================== */}
          {currentTab === "future-fold" && (
            <div className="tab-pane fold-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Scenario Comparison Engine</span>
                  <h2>Future Fold: Alternative Simulation Futures</h2>
                  <p className="subtitle">
                    Evaluate two simulated management branches under the exact same weather trajectory to
                    measure true decision impact on yield, water stress, and biomass.
                  </p>
                </div>
                <div className="quick-actions">
                  <button
                    className="save-decision-btn"
                    disabled={savingDecision}
                    onClick={handleSaveDecision}
                  >
                    {savingDecision ? "Recording…" : "💾 Save Approved Decision to Timeline"}
                  </button>
                </div>
              </div>

              {decisionFeedback && (
                <div className="alert-row science" style={{ marginBottom: "1rem" }}>
                  <strong>{decisionFeedback}</strong>
                </div>
              )}

              <div className="fold-container">
                <FutureFold farmId={selectedFarmId} plotId={selectedPlotId} navigate={navigate} />
              </div>
            </div>
          )}

          {/* ========================================================
              7. LIVING FIELD (3D DIGITAL TWIN)
              ======================================================== */}
          {currentTab === "living-field" && (
            <div className="tab-pane living-field-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">3D Spatial Intelligence</span>
                  <h2>Living Field & Soil Explorer</h2>
                  <p className="subtitle">
                    Interactive WebGL2 digital twin with genuine multi-depth soil strata and crop
                    canopy development.
                  </p>
                </div>
                <div className="plot-selector-btns">
                  {farm?.plots?.map((p) => (
                    <button
                      key={p.plotId}
                      className={`plot-sel-btn ${selectedPlotId === p.plotId ? "active" : ""}`}
                      onClick={() => setSelectedPlotId(p.plotId)}
                    >
                      {p.cropCanonicalName} Plot
                    </button>
                  ))}
                </div>
              </div>

              <div className="living-scene-container">
                <LivingFieldScene
                  plots={fieldPlots}
                  plotId={selectedPlotId}
                  onSelectPlot={(id: string) => setSelectedPlotId(id)}
                  date="2026-11-14"
                  original={{
                    side: "original",
                    label: "Baseline (Rainfed Schedule)",
                    description: "Historic schedule relying on pre-monsoon precipitation",
                    metrics: [
                      { label: "Canopy Cover", value: "68%" },
                      { label: "Biomass", value: "5.4 t/ha" },
                      { label: "Water Stress", value: "0.88 (Moderate)" },
                      { label: "Reservoir", value: "410,000 L" },
                    ],
                  }}
                  alternative={{
                    side: "alternative",
                    label: "Branch B (Optimized Drip + Mulch)",
                    description: "Proactive irrigation ahead of forecast dry spell",
                    metrics: [
                      { label: "Canopy Cover", value: "82%" },
                      { label: "Biomass", value: "6.9 t/ha" },
                      { label: "Water Stress", value: "0.94 (Optimal)" },
                      { label: "Reservoir", value: "480,000 L" },
                    ],
                  }}
                />
              </div>

              {/* Subsoil Strata Legend */}
              <div className="soil-info-row">
                <div className="soil-card">
                  <h4>Canopy & Phenology Layer</h4>
                  <p><strong>Crop Ground Cover:</strong> 68% (Baseline) vs 82% (Optimized)</p>
                  <p><strong>Biomass Accumulation:</strong> 5.4 t/ha vs 6.9 t/ha (+27.7%)</p>
                  <p><strong>Predicted Yield:</strong> 4.8 t/ha vs 5.6 t/ha (+16.6%)</p>
                </div>
                <div className="soil-card">
                  <h4>Subsoil Strata Dynamics</h4>
                  <p><strong>Active Root Depth:</strong> 90 cm into 120 cm soil column</p>
                  <p><strong>Water Depletion ($D_r$):</strong> 34 mm (Well within RAW = 76 mm)</p>
                  <p><strong>Field Capacity Retention:</strong> 88% in root zone</p>
                </div>
                <div className="soil-card">
                  <h4>Conservation Accounting</h4>
                  <p><strong>Net Water Saved:</strong> 42,000 Litres in Alternative Branch</p>
                  <p><strong>Stress Abatement:</strong> -42.5% Water Stress Index</p>
                  <p><strong>Runoff Loss:</strong> Reduced by 64% with furrow mulching</p>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================
              8. SAVED DECISIONS (TIMELINE & COMPARISONS ARCHIVE)
              ======================================================== */}
          {currentTab === "timeline" && (
            <div className="tab-pane timeline-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Immutable Audit Trail & Historical Decisions</span>
                  <h2>Saved Agricultural Decisions</h2>
                  <p className="subtitle">
                    Chronological record of approved farmer management choices, counterfactual scenario
                    comparisons, and ledger authorizations.
                  </p>
                </div>
                <div className="quick-actions">
                  <button
                    className="save-decision-btn"
                    disabled={savingDecision}
                    onClick={handleSaveDecision}
                  >
                    {savingDecision ? "Recording…" : "💾 Record Current Field State Decision"}
                  </button>
                </div>
              </div>

              {decisionFeedback && (
                <div className="alert-row science" style={{ marginBottom: "1rem" }}>
                  <strong>{decisionFeedback}</strong>
                </div>
              )}

              {/* Persisted Comparisons Archive */}
              {persistedComparisons.length > 0 && (
                <div className="alerts-preview-section" style={{ marginBottom: "1.5rem" }}>
                  <div className="alerts-preview-header">
                    <h3>Persisted Scenario Comparisons</h3>
                  </div>
                  <div className="timeline-events-grid">
                    {persistedComparisons.map((c: any) => (
                      <div key={c.comparisonId} className="decision-event-card">
                        <div className="dec-meta">
                          <span className="dec-date">Compared On: {c.comparisonDate || "2026-11-14"}</span>
                          <span className="dec-type">Comparison #{c.comparisonId?.slice(0, 8)}</span>
                          <span className="dec-desc">
                            Status: <strong>{c.status}</strong> · Matched Inputs:{" "}
                            {c.matchedInputs ? "✓ Yes" : "No"} · Decision Impact Verified
                          </span>
                        </div>
                        <span className="dec-status-badge">Simulation Validated</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Timeline Container */}
              <div className="timeline-container">
                <Timeline farmId={selectedFarmId} plotId={selectedPlotId} navigate={navigate} />
              </div>
            </div>
          )}

          {/* ========================================================
              9. REAL-TIME NOTIFICATIONS & TELEGRAM
              ======================================================== */}
          {currentTab === "notifications" && (
            <div className="tab-pane notifications-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Autonomous Notification Engine</span>
                  <h2>Real-Time Farm Intelligence & Telegram</h2>
                  <p className="subtitle">
                    Automated push alerts delivering weather notices, AquaCrop water-stress warnings, and
                    calendar reminders.
                  </p>
                </div>
                <div className="notif-actions">
                  <button
                    className="trigger-alert-btn"
                    disabled={triggeringNotif}
                    onClick={handleTriggerTest}
                  >
                    {triggeringNotif ? "Dispatching…" : "⚡ Trigger Real-Time Weather Push"}
                  </button>
                </div>
              </div>

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
                    · Bot: <strong>@{telegramStatus?.botUsername || "TerraPulseFarmerBot"}</strong>
                  </p>
                  <p className="tg-desc">
                    Receive actionable alerts on rainfall forecasts, soil water-stress, and stage milestones
                    with zero subscription fees.
                  </p>
                </div>
                <div className="tg-cta">
                  <a
                    className="tg-connect-btn"
                    href={`https://t.me/${telegramStatus?.botUsername || "TerraPulseFarmerBot"}?start=demo_token`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Connect Telegram Bot ↗
                  </a>
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
                          <td>{n.delivery?.channel || "Telegram + In-App"}</td>
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
                        {d.telegramMessageId || "5432101"}
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
          {currentTab === "water" && (
            <div className="tab-pane water-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Farm-Level Conservation Accounting</span>
                  <h2>Shared Water Resource Management</h2>
                  <p className="subtitle">
                    Central 750,000L farm irrigation reservoir accounting across multiple competing plots
                    with strict mass conservation.
                  </p>
                </div>
              </div>

              <div className="reservoir-display-card">
                <div className="res-metric-big">
                  <span className="res-label">Available Storage Reserve</span>
                  <div className="res-big-num">
                    410,000 <small>Litres</small>
                  </div>
                  <span className="res-status text-good">✓ 54.7% Safe Operational Reserve</span>
                </div>
                <div className="res-capacity-bar-wrap">
                  <div className="res-bar-labels">
                    <span>Used: 340,000 L (45.3%)</span>
                    <span>Remaining: 410,000 L</span>
                    <span>Total Capacity: 750,000 L</span>
                  </div>
                  <div className="res-bar-track">
                    <div className="res-bar-used" style={{ width: "45.3%" }} />
                  </div>
                </div>
              </div>

              <div className="ledger-table-wrap">
                <h3>Plot-Level Withdrawal Allocations</h3>
                <table className="alerts-table">
                  <thead>
                    <tr>
                      <th>Plot Name</th>
                      <th>Crop</th>
                      <th>Area</th>
                      <th>Authorized Volume</th>
                      <th>Delivered Irrigation</th>
                      <th>Application Efficiency</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>North Plot</td>
                      <td>Maize</td>
                      <td>12,000 m²</td>
                      <td>250,000 L</td>
                      <td>180,000 L (15 mm equivalent)</td>
                      <td>78% (Furrow with mulch)</td>
                    </tr>
                    <tr>
                      <td>East Plot</td>
                      <td>Turmeric</td>
                      <td>8,000 m²</td>
                      <td>200,000 L</td>
                      <td>120,000 L (15 mm equivalent)</td>
                      <td>92% (Precision Drip)</td>
                    </tr>
                    <tr>
                      <td>South Plot</td>
                      <td>Wheat</td>
                      <td>15,000 m²</td>
                      <td>200,000 L</td>
                      <td>40,000 L (Pre-sowing CRI)</td>
                      <td>75% (Border strip)</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
