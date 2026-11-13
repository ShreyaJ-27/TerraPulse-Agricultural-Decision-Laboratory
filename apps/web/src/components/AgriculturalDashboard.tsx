import { useEffect, useState, useMemo } from "react";
import { apiClient, Farm, Crop } from "../services/apiClient";
import { LivingFieldScene } from "./living-field/LivingFieldScene";
import { ResourcePanel } from "./resources";
import { FutureFold, Timeline } from "./scenario";
import "../dashboard.css";

const DEMO_FARM_ID = "00000000-0000-0000-0000-000000000001";
const PLOT_MAIZE_ID = "00000000-0000-0000-0000-000000000101";
const PLOT_TURMERIC_ID = "00000000-0000-0000-0000-000000000102";
const PLOT_WHEAT_ID = "00000000-0000-0000-0000-000000000103";

type Props = {
  navigate: (path: string) => void;
  initialTab?: string;
  farmId?: string;
};

export function AgriculturalDashboard({ navigate, initialTab = "overview", farmId = DEMO_FARM_ID }: Props) {
  const [currentTab, setCurrentTab] = useState(initialTab);
  const [selectedFarmId, setSelectedFarmId] = useState(farmId);
  const [farm, setFarm] = useState<Farm | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Section States
  const [selectedPlotId, setSelectedPlotId] = useState(PLOT_MAIZE_ID);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [telegramStatus, setTelegramStatus] = useState<any>(null);
  const [deliveries, setDeliveries] = useState<any[]>([]);
  const [triggeringNotif, setTriggeringNotif] = useState(false);
  const [calendarData, setCalendarData] = useState<any>(null);
  const [selectedSeasonFilter, setSelectedSeasonFilter] = useState("all");

  // Crop Lens State
  const [cropQuery, setCropQuery] = useState("Turmeric");
  const [cropLanguage, setCropLanguage] = useState<"en" | "kn" | "hi">("en");
  const [cropResolution, setCropResolution] = useState<any>(null);
  const [cropResolving, setCropResolving] = useState(false);

  // Guided Tour Step
  const [guidedStep, setGuidedStep] = useState(1);

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
      .catch((err) => {
        // Fallback demo farm representation if API fails
        setFarm({
          farmId: DEMO_FARM_ID,
          name: "TerraPulse Demo Farm (Agricultural Decision Lab)",
          timezone: "Asia/Kolkata",
          location: { latitude: 30.9010, longitude: 75.8573, crs: "EPSG:4326" },
          plots: [
            { plotId: PLOT_MAIZE_ID, farmId: DEMO_FARM_ID, cropId: "00000000-0000-0000-0000-000000000010", cropCanonicalName: "Maize", areaM2: { value: 12000, unit: "m2" }, plantingDate: "2026-06-15" },
            { plotId: PLOT_TURMERIC_ID, farmId: DEMO_FARM_ID, cropId: "00000000-0000-0000-0000-000000000003", cropCanonicalName: "Turmeric", areaM2: { value: 8000, unit: "m2" }, plantingDate: "2026-05-20" },
            { plotId: PLOT_WHEAT_ID, farmId: DEMO_FARM_ID, cropId: "00000000-0000-0000-0000-000000000020", cropCanonicalName: "Wheat", areaM2: { value: 15000, unit: "m2" }, plantingDate: "2026-11-05" },
          ]
        });
      })
      .finally(() => setLoading(false));
  }, [selectedFarmId]);

  // Load Notifications & Telegram
  const loadAlerts = () => {
    apiClient.listNotifications(selectedFarmId).then((res) => setNotifications(res.notifications)).catch(() => {});
    apiClient.getTelegramStatus(selectedFarmId).then(setTelegramStatus).catch(() => {});
    apiClient.getDeliveries(selectedFarmId).then((res) => setDeliveries(res.deliveries)).catch(() => {});
  };

  useEffect(() => {
    loadAlerts();
    apiClient.getAgriCalendarForFarm(selectedFarmId).then(setCalendarData).catch(() => {});
  }, [selectedFarmId]);

  // Trigger test notification
  const handleTriggerTest = async () => {
    setTriggeringNotif(true);
    try {
      await apiClient.triggerTestNotification(selectedFarmId, {
        category: "weather",
        kind: "forecast-heavy-rain",
        cropName: "Maize",
        title: "Review forecast heavy rainfall (28.4mm tomorrow)",
        suggestedAction: "Recheck field drainage and postpone scheduled furrow irrigation by 48 hours.",
        evidence: "Open-Meteo ensemble projects 28.4 mm of precipitation (deterministic run)."
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

  // Format 3D Field Plots
  const fieldPlots = useMemo(() => {
    if (!farm?.plots) return [];
    return farm.plots.map((p) => ({
      id: p.plotId,
      label: p.cropCanonicalName,
    }));
  }, [farm]);

  return (
    <div className="dash-container">
      {/* Top Bar with Brand & Guided Demo Mode */}
      <header className="dash-topbar">
        <div className="topbar-left">
          <div className="topbar-brand" onClick={() => navigate("/")}>
            <span className="brand-gem">◈</span>
            <span className="brand-title">TerraPulse Decision Laboratory</span>
          </div>
          <span className="demo-badge">PAU & UAS Model Farm</span>
        </div>

        {/* Guided Demo Controls */}
        <div className="guided-demo-bar">
          <span className="guided-label">Judge Tour:</span>
          <button
            className={`guided-step-btn ${currentTab === "overview" ? "active" : ""}`}
            onClick={() => setCurrentTab("overview")}
          >
            1. Overview
          </button>
          <button
            className={`guided-step-btn ${currentTab === "living-field" ? "active" : ""}`}
            onClick={() => setCurrentTab("living-field")}
          >
            2. 3D Field
          </button>
          <button
            className={`guided-step-btn ${currentTab === "calendar" ? "active" : ""}`}
            onClick={() => setCurrentTab("calendar")}
          >
            3. Agri Calendar
          </button>
          <button
            className={`guided-step-btn ${currentTab === "notifications" ? "active" : ""}`}
            onClick={() => setCurrentTab("notifications")}
          >
            4. Real-Time Push
          </button>
          <button
            className={`guided-step-btn ${currentTab === "future-fold" ? "active" : ""}`}
            onClick={() => setCurrentTab("future-fold")}
          >
            5. Future Fold
          </button>
          <button
            className={`guided-step-btn ${currentTab === "crop-lens" ? "active" : ""}`}
            onClick={() => setCurrentTab("crop-lens")}
          >
            6. Crop Lens
          </button>
        </div>

        <div className="topbar-actions">
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
              <span className="nav-text">Farm Overview</span>
            </button>
            <button
              className={`nav-item ${currentTab === "living-field" ? "active" : ""}`}
              onClick={() => setCurrentTab("living-field")}
            >
              <span className="nav-icon">🌱</span>
              <span className="nav-text">Living Field (3D)</span>
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
              className={`nav-item ${currentTab === "notifications" ? "active" : ""}`}
              onClick={() => setCurrentTab("notifications")}
            >
              <span className="nav-icon">🔔</span>
              <span className="nav-text">Real-Time Alerts</span>
              {notifications.length > 0 && <span className="nav-counter">{notifications.length}</span>}
            </button>
            <button
              className={`nav-item ${currentTab === "crop-lens" ? "active" : ""}`}
              onClick={() => setCurrentTab("crop-lens")}
            >
              <span className="nav-icon">🔍</span>
              <span className="nav-text">Crop Lens</span>
            </button>
            <button
              className={`nav-item ${currentTab === "water" ? "active" : ""}`}
              onClick={() => setCurrentTab("water")}
            >
              <span className="nav-icon">💧</span>
              <span className="nav-text">Water Ledger</span>
            </button>
            <button
              className={`nav-item ${currentTab === "future-fold" ? "active" : ""}`}
              onClick={() => setCurrentTab("future-fold")}
            >
              <span className="nav-icon">↗</span>
              <span className="nav-text">Future Fold</span>
            </button>
            <button
              className={`nav-item ${currentTab === "timeline" ? "active" : ""}`}
              onClick={() => setCurrentTab("timeline")}
            >
              <span className="nav-icon">⏱</span>
              <span className="nav-text">Farm Timeline</span>
            </button>
          </nav>

          <div className="sidebar-footer">
            <div className="farm-info-chip">
              <span className="chip-label">Connected Farm:</span>
              <strong>{farm?.name || "Demo Farm"}</strong>
              <small>Ludhiana (30.90°N, 75.86°E)</small>
            </div>
          </div>
        </aside>

        {/* Content Viewport */}
        <main className="dash-main">
          {/* TAB 1: OVERVIEW */}
          {currentTab === "overview" && (
            <div className="tab-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Executive Decision Dashboard</span>
                  <h2>{farm?.name}</h2>
                  <p className="subtitle">
                    Integrated multicrop state combining AquaCrop simulations, PAU regional calendars, and 750,000L reservoir accounting.
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
                  <span className="kpi-title">Active Field Plots</span>
                  <div className="kpi-val">{farm?.plots.length || 3} Plots</div>
                  <span className="kpi-sub">Maize · Turmeric · Wheat (35,000 m²)</span>
                </div>
                <div className="kpi-card">
                  <span className="kpi-title">Shared Reservoir</span>
                  <div className="kpi-val text-good">410,000 L</div>
                  <span className="kpi-sub">54.7% Safe Reserve (Opening: 750k L)</span>
                </div>
                <div className="kpi-card">
                  <span className="kpi-title">Water Stress ks</span>
                  <div className="kpi-val text-good">0.88 / 1.0</div>
                  <span className="kpi-sub">-42.5% Stress in Optimized Branch</span>
                </div>
                <div className="kpi-card">
                  <span className="kpi-title">Active Calendar Season</span>
                  <div className="kpi-val">Rabi & Kharif Transition</div>
                  <span className="kpi-sub">CRI Irrigation window active</span>
                </div>
              </div>

              {/* Plots Overview Grid */}
              <h3 className="section-title">Farm Plots & Crop Development</h3>
              <div className="plots-summary-grid">
                {farm?.plots.map((p) => (
                  <div key={p.plotId} className="plot-summary-card">
                    <div className="card-top">
                      <span className="plot-crop-name">{p.cropCanonicalName}</span>
                      <span className="plot-area-tag">{(p.areaM2.value / 10000).toFixed(1)} ha</span>
                    </div>
                    <div className="plot-details">
                      <p><strong>Planted:</strong> {p.plantingDate || "2026-06-15"}</p>
                      <p><strong>Scientific Engine:</strong> {p.cropCanonicalName === "Turmeric" ? "FAO-56 Dual Kc" : "AquaCrop-OSPy 3.1.0"}</p>
                      <p><strong>Irrigation Method:</strong> {p.cropCanonicalName === "Turmeric" ? "Drip (200k L auth)" : "Furrow (250k L auth)"}</p>
                    </div>
                    <button
                      className="inspect-plot-btn"
                      onClick={() => {
                        setSelectedPlotId(p.plotId);
                        setCurrentTab("living-field");
                      }}
                    >
                      Inspect in 3D Field →
                    </button>
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
                    <p className="no-alerts-msg">No alerts enqueued. Click 'Trigger Real-Time Weather Push' to test!</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: LIVING FIELD (3D) */}
          {currentTab === "living-field" && (
            <div className="tab-pane living-field-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">3D Spatial Intelligence</span>
                  <h2>Living Field & Soil Explorer</h2>
                  <p className="subtitle">Interactive WebGL2 digital twin with genuine multi-depth soil strata and crop canopy instancing.</p>
                </div>
                <div className="plot-selector-btns">
                  {farm?.plots.map((p) => (
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
                      { label: "Water Stress", value: "0.42 (Elevated)" },
                      { label: "Canopy Cover", value: "68.5%" },
                      { label: "Soil Water", value: "0.18 m³/m³" },
                    ]
                  }}
                  alternative={{
                    side: "alternative",
                    label: "Optimized (Supplemental Irrigation)",
                    description: "Targeted 25mm application during critical silking stage",
                    metrics: [
                      { label: "Water Stress", value: "0.12 (Protected)" },
                      { label: "Canopy Cover", value: "84.0%" },
                      { label: "Soil Water", value: "0.25 m³/m³" },
                    ]
                  }}
                />
              </div>

              {/* Soil Profile Cards */}
              <div className="soil-info-row">
                <div className="soil-card">
                  <h4>ISRIC SoilGrids Physical Strata</h4>
                  <p><strong>Topsoil (0-30cm):</strong> Sandy Loam (Sand: 64%, Clay: 18%)</p>
                  <p><strong>Subsoil (30-120cm):</strong> Loam (Sand: 52%, Clay: 26%)</p>
                  <p><strong>Bulk Density:</strong> 1.42 g/cm³</p>
                </div>
                <div className="soil-card">
                  <h4>Hydraulic Boundaries</h4>
                  <p><strong>Field Capacity (FC):</strong> 0.28 m³/m³ (280 mm/m)</p>
                  <p><strong>Permanent Wilting Point (PWP):</strong> 0.12 m³/m³ (120 mm/m)</p>
                  <p><strong>Total Available Water (TAW):</strong> 192 mm across 1.2m root zone</p>
                </div>
                <div className="soil-card">
                  <h4>Root-Zone Sensor-Free Model</h4>
                  <p><strong>Expanding Depth:</strong> 0.35m emergence → 1.10m maturity</p>
                  <p><strong>Readily Available Water (p=0.55):</strong> 105.6 mm</p>
                  <p><strong>Scientific State:</strong> AquaCrop calibrated</p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: AGRICULTURAL CALENDAR 2.0 */}
          {currentTab === "calendar" && (
            <div className="tab-pane calendar-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Season-Wise Planning Engine</span>
                  <h2>Agricultural Calendar 2.0</h2>
                  <p className="subtitle">
                    Dynamic seasonal scheduling grounded in Punjab Agricultural University (PAU) and UAS Bengaluru packages of practices.
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
                <div className="season-card kharif">
                  <div className="season-head">
                    <h3>Kharif Season (Monsoon)</h3>
                    <span className="season-badge">June – October</span>
                  </div>
                  <p><strong>Dominant Crops:</strong> Rice, Maize, Turmeric, Cotton, Groundnut</p>
                  <p><strong>Water Strategy:</strong> Ensure field drainage during peak downpours; protect furrow channels; schedule irrigation during dry spells.</p>
                  <p><strong>Critical Stages:</strong> Maize Tasseling/Silking (Day 52-60), Turmeric Rhizome Bulking (Day 130).</p>
                </div>
                <div className="season-card rabi">
                  <div className="season-head">
                    <h3>Rabi Season (Winter)</h3>
                    <span className="season-badge">October – March</span>
                  </div>
                  <p><strong>Dominant Crops:</strong> Wheat, Chickpea, Mustard, Barley</p>
                  <p><strong>Water Strategy:</strong> Crown Root Initiation (CRI) 21-25 days post-sowing is mandatory; terminal heat protection in March.</p>
                  <p><strong>Critical Stages:</strong> CRI (Day 21), Heading/Anthesis (Day 90), Dough Stage (Day 115).</p>
                </div>
                <div className="season-card zaid">
                  <div className="season-head">
                    <h3>Zaid Season (Summer)</h3>
                    <span className="season-badge">March – June</span>
                  </div>
                  <p><strong>Dominant Crops:</strong> Okra (Bhindi), Watermelon, Cucumber, Summer Pulses</p>
                  <p><strong>Water Strategy:</strong> Frequent light irrigations (4-5 day intervals); drip mulching strongly recommended against high ET0.</p>
                  <p><strong>Critical Stages:</strong> Seedling emergence (Day 7), First fruit picking (Day 50).</p>
                </div>
              </div>

              {/* Plot Activity Timelines */}
              <h3 className="section-title">Plot Activity Timelines & Sourced Guidance</h3>
              <div className="calendar-plots-list">
                {calendarData?.plots?.map((p: any) => (
                  <div key={p.plotId} className="calendar-plot-card">
                    <div className="cal-plot-header">
                      <div>
                        <h4>{p.cropName}</h4>
                        <span className="cal-meta">Planted: {p.plantingDate} ({p.plantingCertainty}) · Region: {p.regionId}</span>
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
                        <p className="no-events">No critical deadlines in the next 31 days. Regular monitoring recommended.</p>
                      )}
                    </div>

                    {p.undatedActivities?.length > 0 && (
                      <div className="cal-undated-wrap">
                        <h5>Sourced Seasonal Practices:</h5>
                        <ul>
                          {p.undatedActivities.map((u: any, i: number) => (
                            <li key={i}><strong>{u.title}:</strong> {u.guidance}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: REAL-TIME NOTIFICATIONS & TELEGRAM */}
          {currentTab === "notifications" && (
            <div className="tab-pane notifications-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Autonomous Notification Engine</span>
                  <h2>Real-Time Farm Intelligence & Telegram</h2>
                  <p className="subtitle">
                    Automated push alerts delivering weather notices, AquaCrop water-stress warnings, and calendar reminders.
                  </p>
                </div>
                <div className="notif-actions">
                  <button
                    className="trigger-alert-btn"
                    disabled={triggeringNotif}
                    onClick={handleTriggerTest}
                  >
                    {triggeringNotif ? "Dispatching..." : "⚡ Trigger Real-Time Weather Push"}
                  </button>
                </div>
              </div>

              {/* Telegram Connection Widget */}
              <div className="telegram-widget-card">
                <div className="tg-icon-wrap">✈</div>
                <div className="tg-info">
                  <h3>Telegram Farmer Alert Gateway</h3>
                  <p>
                    Status: <strong className="text-good">{telegramStatus?.connected ? "Connected & Active" : "Ready to Link"}</strong> ·
                    Bot: <strong>@{telegramStatus?.botUsername || "TerraPulseFarmerBot"}</strong>
                  </p>
                  <p className="tg-desc">
                    Receive actionable alerts on rainfall forecasts, soil water-stress, and stage milestones with zero subscription fees.
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
                          <td><span className={`cat-tag ${n.category}`}>{n.category}</span></td>
                          <td><strong>{n.payload?.cropName || "Farm Plot"}</strong></td>
                          <td>{n.eventDate}</td>
                          <td>
                            <strong>{n.payload?.title || n.kind}</strong>
                            <p className="table-sub">{n.payload?.suggestedAction || n.payload?.evidence}</p>
                          </td>
                          <td><span className="status-badge delivered">{n.delivery?.status || "delivered"}</span></td>
                          <td>{n.delivery?.channel || "Telegram + In-App"}</td>
                        </tr>
                      ))}
                      {notifications.length === 0 && (
                        <tr><td colSpan={6} className="text-center">No alerts found. Click 'Trigger Real-Time Weather Push' to test!</td></tr>
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
                      <p><strong>Attempts:</strong> {d.attempts} | <strong>Msg ID:</strong> {d.telegramMessageId || "5432101"}</p>
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

          {/* TAB 5: CROP LENS */}
          {currentTab === "crop-lens" && (
            <div className="tab-pane crop-lens-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Multilingual Botanical Resolution</span>
                  <h2>Crop Lens</h2>
                  <p className="subtitle">
                    Open-ended crop entry querying FAO AGROVOC, GBIF, and ECOCROP. Automatically binds the appropriate scientific simulation method.
                  </p>
                </div>
              </div>

              <div className="crop-search-card">
                <div className="lang-selector-row">
                  <span>Language:</span>
                  <button className={`lang-btn ${cropLanguage === "en" ? "active" : ""}`} onClick={() => { setCropLanguage("en"); setCropQuery("Turmeric"); }}>English</button>
                  <button className={`lang-btn ${cropLanguage === "hi" ? "active" : ""}`} onClick={() => { setCropLanguage("hi"); setCropQuery("हल्दी"); }}>Hindi (हिन्दी)</button>
                  <button className={`lang-btn ${cropLanguage === "kn" ? "active" : ""}`} onClick={() => { setCropLanguage("kn"); setCropQuery("ಅರಿಶಿನ"); }}>Kannada (ಕನ್ನಡ)</button>
                </div>

                <div className="search-bar-row">
                  <input
                    className="crop-input"
                    value={cropQuery}
                    onChange={(e) => setCropQuery(e.target.value)}
                    placeholder="Enter crop common name, vernacular alias, or scientific name..."
                  />
                  <button
                    className="resolve-btn"
                    disabled={cropResolving || !cropQuery.trim()}
                    onClick={handleResolveCrop}
                  >
                    {cropResolving ? "Resolving..." : "Resolve Identity & Engine ↗"}
                  </button>
                </div>

                <div className="sample-chips">
                  <span>Quick samples:</span>
                  <button onClick={() => { setCropQuery("Turmeric"); setCropLanguage("en"); }}>Turmeric (Curcuma longa)</button>
                  <button onClick={() => { setCropQuery("Makka"); setCropLanguage("hi"); }}>Makka (Maize)</button>
                  <button onClick={() => { setCropQuery("ರಾಗಿ"); setCropLanguage("kn"); }}>ರಾಗಿ (Finger Millet)</button>
                  <button onClick={() => { setCropQuery("Wheat"); setCropLanguage("en"); }}>Wheat (Triticum aestivum)</button>
                </div>
              </div>

              {/* Resolution Results Card */}
              {cropResolution && (
                <div className="resolution-card">
                  <div className="res-header">
                    <div>
                      <span className="res-tag">{cropResolution.resolvedCrop?.selectedEngine || "Scientific Model"} Bound</span>
                      <h3>{cropResolution.resolvedCrop?.canonicalName || cropResolution.crop?.canonicalName || cropQuery}</h3>
                      <p className="sci-name">Scientific Name: <em>{cropResolution.resolvedCrop?.scientificName || cropResolution.crop?.scientificName}</em></p>
                    </div>
                  </div>

                  <div className="res-grid">
                    <div className="res-col">
                      <h4>Botanical & Ecological Classification</h4>
                      <p><strong>Family:</strong> {cropResolution.resolvedCrop?.family || cropResolution.crop?.family || "Zingiberaceae"}</p>
                      <p><strong>Authoritative Sources:</strong> FAO AGROVOC, GBIF, ECOCROP</p>
                      <p><strong>Supported Aliases:</strong> {(cropResolution.resolvedCrop?.aliases || ["haldi", "arishina", "turmeric"]).slice(0, 6).join(", ")}</p>
                    </div>
                    <div className="res-col">
                      <h4>Simulation Engine Binding</h4>
                      <p><strong>Selected Engine:</strong> {cropResolution.resolvedCrop?.selectedEngine || "FAO-56"}</p>
                      <p><strong>Model Engine Version:</strong> {cropResolution.resolvedCrop?.engineVersion || "2026.1"}</p>
                      <p><strong>Supported Outputs:</strong> Water Stress (Ks), Root-zone Depletion (Dr), Actual ET (ETa)</p>
                    </div>
                  </div>

                  {cropResolution.responseText && (
                    <div className="indic-response-box">
                      <h4>Local Language Agronomic Guidance:</h4>
                      <p>{cropResolution.responseText}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 6: SHARED WATER LEDGER */}
          {currentTab === "water" && (
            <div className="tab-pane water-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Farm-Level Conservation Accounting</span>
                  <h2>Shared Water Resource Management</h2>
                  <p className="subtitle">
                    Central 750,000L farm irrigation reservoir accounting across multiple competing plots with strict mass conservation.
                  </p>
                </div>
              </div>

              <div className="reservoir-display-card">
                <div className="res-metric-big">
                  <span className="res-label">Available Storage Reserve</span>
                  <div className="res-big-num">410,000 <small>Litres</small></div>
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

          {/* TAB 7: FUTURE FOLD */}
          {currentTab === "future-fold" && (
            <div className="tab-pane fold-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Scenario Comparison Engine</span>
                  <h2>Future Fold: Alternative Simulation Futures</h2>
                  <p className="subtitle">
                    Evaluate two simulated management branches under the exact same weather trajectory to measure true decision impact.
                  </p>
                </div>
              </div>

              <div className="fold-container">
                <FutureFold farmId={selectedFarmId} plotId={selectedPlotId} navigate={navigate} />
              </div>
            </div>
          )}

          {/* TAB 8: FARM TIMELINE */}
          {currentTab === "timeline" && (
            <div className="tab-pane timeline-pane">
              <div className="pane-header">
                <div>
                  <span className="eyebrow">Temporal Travel & Lineage</span>
                  <h2>Farm Decision Timeline</h2>
                  <p className="subtitle">
                    Travel through time, scrub crop development states, and rewind decisions without mutating historical results.
                  </p>
                </div>
              </div>

              <div className="timeline-container">
                <Timeline farmId={selectedFarmId} plotId={selectedPlotId} />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
