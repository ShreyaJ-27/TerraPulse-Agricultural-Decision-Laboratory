import { useState, useEffect } from "react";
import { SylvaLivingWorldScene, type SylvaLivingWorldVariant } from "@designcodeio/threeui";
import "@designcodeio/threeui/style.css";
import "../landing.css";
import { Locale, localeLabels, translations, tUI } from "../i18n";

type LandingPageProps = {
  navigate?: (path: string) => void;
  locale?: Locale;
  onLocaleChange?: (locale: Locale) => void;
  atmosphere?: SylvaLivingWorldVariant;
  onAtmosphereChange?: (atmo: SylvaLivingWorldVariant) => void;
};

const NAV_TABS = [
  "Farm Workspace",
  "Future Fold",
  "Living Field",
  "Crop Planning",
  "Calendar",
  "Dashboard",
] as const;

const TAB_KEY_MAP: Record<string, string> = {
  "Farm Workspace": "farmWorkspace",
  "Future Fold": "futureFold",
  "Living Field": "livingField",
  "Crop Planning": "cropPlanning",
  "Calendar": "calendar",
  "Dashboard": "dashboard",
};

export function LandingPage({
  navigate,
  locale = "en",
  onLocaleChange,
  atmosphere = "living-green",
  onAtmosphereChange,
}: LandingPageProps = {}) {
  const [internalVariant, setInternalVariant] = useState<SylvaLivingWorldVariant>(atmosphere);
  const [activeNavTab, setActiveNavTab] = useState<string>("Living Field");
  const _copy = translations[locale] || translations.en;

  const currentVariant = atmosphere || internalVariant;
  const updateVariant = (v: SylvaLivingWorldVariant) => {
    setInternalVariant(v);
    if (onAtmosphereChange) onAtmosphereChange(v);
  };

  // Smooth scroll helper for landing page internal sections
  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  const handleNavClick = (tab: typeof NAV_TABS[number]) => {
    setActiveNavTab(tab);
    if (tab === "Farm Workspace") {
      if (navigate) navigate("/dashboard?tab=overview");
      else scrollToSection("solution");
    } else if (tab === "Future Fold") {
      scrollToSection("future-fold");
    } else if (tab === "Living Field") {
      scrollToSection("living-field");
    } else if (tab === "Crop Planning") {
      if (navigate) navigate("/dashboard?tab=crop-lens");
      else scrollToSection("solution");
    } else if (tab === "Calendar") {
      scrollToSection("calendar");
    } else if (tab === "Dashboard") {
      if (navigate) navigate("/dashboard");
      else scrollToSection("hero");
    }
  };

  // Forward parent window pointermove events to the persistent Three.js background iframe
  useEffect(() => {
    const handlePointer = (e: MouseEvent) => {
      const iframe = document.querySelector(".sylva-persistent-background iframe") as HTMLIFrameElement | null;
      if (iframe?.contentWindow) {
        iframe.contentWindow.postMessage(
          {
            type: "TERRAPULSE_POINTER",
            clientX: e.clientX,
            clientY: e.clientY,
          },
          "*"
        );
      }
    };
    window.addEventListener("mousemove", handlePointer, { passive: true });
    return () => window.removeEventListener("mousemove", handlePointer);
  }, []);

  return (
    <div className="landing-root">
      {/* ========================================================
          PERSISTENT 3D BACKGROUND (STAYS PINNED WHILE SCROLLING)
          Renders the exact ThreeUI Sylva Living World:
          the large moss plant, ferns, spores, lighting & butterfly
          ======================================================== */}
      <div className="sylva-persistent-background" aria-hidden="true">
        <SylvaLivingWorldScene
          variant={currentVariant}
          style={{ width: "100%", height: "100%", border: "none" }}
        />
      </div>

      {/* ========================================================
          TOP NAVIGATION BAR (PREMIUM FLOATING PILL CAPSULE)
          Exact six tabs: Farm Workspace, Future Fold, Living Field,
          Crop Planning, Calendar, Dashboard (interactive placeholders)
          ======================================================== */}
      <header className="landing-floating-nav-wrap">
        <div className="tp-floating-dock-container">
          <nav className="tp-floating-dock" aria-label="Main Navigation">
            <div className="dock-brand" onClick={() => scrollToSection("hero")}>
              <span className="dock-brand-gem">◈</span>
              <span className="dock-brand-text">TerraPulse</span>
            </div>

            <div className="dock-divider" />

            {/* Exactly the six requested tabs — connected to routes and smooth scroll */}
            <div className="dock-tabs-group">
              {NAV_TABS.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  className={`dock-tab-pill ${activeNavTab === tab ? "active" : ""}`}
                  onClick={(e) => {
                    e.preventDefault();
                    handleNavClick(tab);
                  }}
                >
                  {activeNavTab === tab && <span className="dock-pill-indicator" />}
                  <span className="dock-tab-label">{tUI(locale, TAB_KEY_MAP[tab] || tab)}</span>
                </button>
              ))}
            </div>

            <div className="dock-divider" />

            {/* Language Selector */}
            {onLocaleChange && (
              <div className="dock-lang-group" title="Select interface language">
                <select
                  className="dock-lang-select"
                  value={locale}
                  onChange={(e) => onLocaleChange(e.target.value as Locale)}
                  aria-label="Interface language"
                >
                  {Object.entries(localeLabels).map(([k, name]) => (
                    <option key={k} value={k}>
                      {k.toUpperCase()} · {name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Living World Atmosphere Selector */}
            <div className="dock-atmosphere-group" title="Switch ThreeUI living world atmosphere">
              <span className="dock-atmo-label">{tUI(locale, "atmosphere")}</span>
              <button
                type="button"
                className={`dock-atmo-btn ${currentVariant === "living-green" ? "active" : ""}`}
                onClick={() => updateVariant("living-green")}
                title="Living Green"
              >
                🌿 {tUI(locale, "green")}
              </button>
              <button
                type="button"
                className={`dock-atmo-btn ${currentVariant === "sakura-sunset" ? "active" : ""}`}
                onClick={() => updateVariant("sakura-sunset")}
                title="Sakura Sunset"
              >
                🌸 {tUI(locale, "sakura")}
              </button>
              <button
                type="button"
                className={`dock-atmo-btn ${currentVariant === "maple-autumn" ? "active" : ""}`}
                onClick={() => updateVariant("maple-autumn")}
                title="Maple Autumn"
              >
                🍁 {tUI(locale, "autumn")}
              </button>
              <button
                type="button"
                className={`dock-atmo-btn ${currentVariant === "sequoia-mist" ? "active" : ""}`}
                onClick={() => updateVariant("sequoia-mist")}
                title="Sequoia Mist"
              >
                🌲 {tUI(locale, "mist")}
              </button>
            </div>

            <div className="dock-divider" />

            {/* Prominent Get Started / Farm Registration CTA */}
            <button
              type="button"
              className="dock-cta-btn"
              onClick={() => (navigate ? navigate("/register") : scrollToSection("hero"))}
              title="Register your farm in TerraPulse"
            >
              {tUI(locale, "getStarted")}
            </button>
          </nav>
        </div>
      </header>

      {/* ========================================================
          SCROLLING CONTENT LAYER (SCROLLS OVER PERSISTENT 3D WORLD)
          ======================================================== */}
      <div className="landing-content-layer">
        {/* ========================================================
            HERO SECTION: Fixed text overlap, clean 2-column layout
            with Restored Floating Window-Style Feature Displays
            ======================================================== */}
        <section id="hero" className="landing-hero-screen">
          <div className="hero-screen-container">
            <div className="hero-headline-col">
              <div className="hero-brand-badge">
                <span className="badge-gem">◈</span> {tUI(locale, "heroEyebrow")}
              </div>
              <h1 className="hero-headline">
                <span>{tUI(locale, "heroTitle")}</span>
              </h1>
              <p className="hero-lede-lead">
                {tUI(locale, "heroSubtitle")}
              </p>
              <div className="hero-cta-group">
                <button
                  type="button"
                  className="hero-btn-primary"
                  onClick={() => (navigate ? navigate("/register") : scrollToSection("hero"))}
                >
                  {tUI(locale, "getStarted")}
                </button>
                <button
                  type="button"
                  className="hero-btn-secondary"
                  onClick={() => (navigate ? navigate("/dashboard") : scrollToSection("solution"))}
                >
                  {tUI(locale, "openDecisionLab")}
                </button>
                <button
                  type="button"
                  className="hero-btn-secondary"
                  onClick={() => scrollToSection("solution")}
                >
                  Explore Capabilities <span>↓</span>
                </button>
              </div>
            </div>

            <div className="hero-floating-windows-col">
              {/* Floating Window 1: Decision Intelligence / Science-Grounded Field Simulation */}
              <article
                className="floating-feature-window window--decision"
                onClick={() => navigate ? navigate("/dashboard?tab=living-field") : scrollToSection("living-field")}
              >
                <figure className="window-portal-media">
                  <img
                    src="/landing-pages/inner-green-assets/card-ethos.jpg"
                    alt="Science-grounded field simulation"
                    loading="eager"
                  />
                  <div className="portal-glass-overlay" />
                </figure>
                <div className="window-content">
                  <span className="window-eyebrow">Decision Intelligence</span>
                  <h3 className="window-title">Science-grounded field simulation.</h3>
                  <p className="window-summary">
                    High-fidelity 3D digital twin simulating canopy development, subsurface soil moisture strata,
                    and crop phenology grounded in FAO-56 and AquaCrop models.
                  </p>
                  <div className="window-feature-pills">
                    <span className="wf-pill">Living Field</span>
                    <span className="wf-pill">Crop & Soil Intelligence</span>
                    <span className="wf-pill">Botanical Lens</span>
                  </div>
                </div>
              </article>

              {/* Floating Window 2: Climate Ensemble / Future-Fold Scenarios */}
              <article
                className="floating-feature-window window--climate"
                onClick={() => navigate ? navigate("/dashboard?tab=future-fold") : scrollToSection("future-fold")}
              >
                <div className="window-header-row">
                  <div className="window-text-block">
                    <span className="window-eyebrow">Climate Ensemble</span>
                    <h3 className="window-title">Future-Fold Scenarios.</h3>
                    <p className="window-summary">
                      Synchronized counterfactual engine projecting alternative irrigation choices,
                      water ledger balance, and stress relief under controlled climate trajectories.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="window-knob-btn"
                    aria-label="View Future Fold scenario modeling"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (navigate) navigate("/dashboard?tab=future-fold");
                      else scrollToSection("future-fold");
                    }}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 21v-7" />
                      <path d="M12 14c0-3.3 2.4-6 5.5-6 .3 3.6-2.2 6.4-5.5 6Z" />
                      <path d="M12 16c-.1-2.9-2.2-5.2-4.9-5.2C6.8 13.7 9 16 12 16Z" />
                    </svg>
                  </button>
                </div>
                <figure className="window-portal-media portal--lower">
                  <img
                    src="/landing-pages/inner-green-assets/card-ecostove.jpg"
                    alt="Future-Fold counterfactual scenarios"
                    loading="eager"
                  />
                  <div className="portal-glass-overlay" />
                </figure>
                <div className="window-feature-pills">
                  <span className="wf-pill">Future Fold</span>
                  <span className="wf-pill">Weather Intelligence</span>
                  <span className="wf-pill">Water Ledger</span>
                </div>
              </article>
            </div>
          </div>

          <div className="hero-scroll-cue" onClick={() => scrollToSection("challenge")}>
            <span>Explore</span>
            <div className="scroll-cue-track" />
          </div>
        </section>

        {/* ========================================================
            1. THE CHALLENGE
            ======================================================== */}
        <section id="challenge" className="landing-section">
          <div className="section-container">
            <div className="section-header-compact">
              <span className="section-eyebrow">The Challenge</span>
              <h2 className="section-title">The Agricultural Challenge</h2>
              <p className="section-subtitle">
                Modern agriculture operates in an environment of growing climatic and ecological uncertainty.
                Growers face multiple interacting risks without unified predictive decision support.
              </p>
            </div>

            <div className="feature-cards-grid">
              <div className="capability-card">
                <div className="card-glyph">🌦</div>
                <h3>Unpredictable Weather</h3>
                <p>
                  Extreme weather variability, shifting monsoon patterns, sudden temperature spikes, and
                  unforecast precipitation disrupt critical field operations and crop development.
                </p>
              </div>

              <div className="capability-card">
                <div className="card-glyph">💧</div>
                <h3>Irrigation Inefficiency</h3>
                <p>
                  Uncertainty around optimal irrigation timing and volumes leads to water wastage, unnecessary
                  pumping energy costs, or critical crop moisture stress during sensitive growth stages.
                </p>
              </div>

              <div className="capability-card">
                <div className="card-glyph">🌱</div>
                <h3>Soil-Water Uncertainty</h3>
                <p>
                  Difficulty observing subsurface moisture tension, available water capacity, and root-zone
                  depletion rates creates blind spots beneath the topsoil.
                </p>
              </div>

              <div className="capability-card">
                <div className="card-glyph">🔍</div>
                <h3>Crop Condition Opacity</h3>
                <p>
                  Stomatal closure and internal moisture stress occur days before visual wilting appears, making
                  it difficult to detect declining crop conditions before yield damage occurs.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================
            2. OUR SOLUTION
            ======================================================== */}
        <section id="solution" className="landing-section">
          <div className="section-container">
            <div className="section-header-compact">
              <span className="section-eyebrow">Our Solution</span>
              <h2 className="section-title">TerraPulse Decision Laboratory</h2>
              <p className="section-subtitle">
                An integrated biophysical decision framework connecting atmospheric telemetry, crop simulation,
                soil-water dynamics, and scenario comparison into one continuous predictive feedback loop.
              </p>
            </div>

            <div className="pillars-grid">
              <div className="pillar-card">
                <span className="pillar-num">01</span>
                <h3>Real-Time Weather Integration</h3>
                <p>
                  Ingests atmospheric telemetry and multi-day meteorological ensembles to model evaporative
                  demand, temperature ranges, and environmental stress.
                </p>
              </div>

              <div className="pillar-card">
                <span className="pillar-num">02</span>
                <h3>Biophysical Crop Simulation</h3>
                <p>
                  Integrates authoritative FAO crop growth models to compute daily transpiration, green canopy
                  cover expansion, and physiological biomass development.
                </p>
              </div>

              <div className="pillar-card">
                <span className="pillar-num">03</span>
                <h3>Soil-Water Dynamics</h3>
                <p>
                  Models physical soil strata, infiltration conductivities, root-zone moisture holding capacities,
                  and permanent wilting point boundaries.
                </p>
              </div>

              <div className="pillar-card">
                <span className="pillar-num">04</span>
                <h3>Scenario-Based Decision Support</h3>
                <p>
                  Enables agricultural practitioners to test alternative management decisions side by side before
                  committing resources in the field.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================
            3. LIVING FIELD
            ======================================================== */}
        <section id="living-field" className="landing-section">
          <div className="section-container">
            <div className="section-header-compact">
              <span className="section-eyebrow">Spatial Exploration</span>
              <h2 className="section-title">Living Field: Interactive 3D Farm Environment</h2>
              <p className="section-subtitle">
                A virtual field environment providing spatial and subsurface visibility into crop development,
                soil horizons, and irrigation infrastructure.
              </p>
            </div>

            <div className="deep-dive-card">
              <div className="deep-dive-grid">
                <div className="deep-dive-text">
                  <h3>Virtual Farm Environment & Subsurface Cutaways</h3>
                  <p>
                    Living Field visualizes the agricultural terrain in full 3D, allowing users to orbit, zoom,
                    and inspect individual crop environments and their underlying soil horizons.
                  </p>
                  <ul className="capability-bullet-list">
                    <li>
                      <strong>Interactive 3D Farm Visualization:</strong> Spatial exploration of field plots,
                      crop canopies, and surrounding natural topography.
                    </li>
                    <li>
                      <strong>Multi-Crop Environments:</strong> Modeling diverse crop types including cereals,
                      legumes, and specialty rhizome crops across varying management zones.
                    </li>
                    <li>
                      <strong>Dynamic Crop Growth Visualization:</strong> Visual representations of vegetative
                      expansion, leaf area development, and phenological milestones.
                    </li>
                    <li>
                      <strong>Irrigation System Indicators:</strong> Visualization of active irrigation networks,
                      including drip lines, furrow channels, and border strip flooding.
                    </li>
                    <li>
                      <strong>2D Farm Mapping:</strong> Top-down spatial orientation, boundary demarcation, and
                      plot-by-plot management layouts.
                    </li>
                    <li>
                      <strong>Soil-Section & Root Depth Cutaway:</strong> Subsurface visibility revealing root
                      penetration depth, soil horizon textures, field capacity, and wilting points.
                    </li>
                  </ul>
                </div>

                <div className="deep-dive-preview-box">
                  <div className="preview-box-header">
                    <span className="preview-dot" />
                    <span className="preview-dot" />
                    <span className="preview-dot" />
                    <span className="preview-title">Living Field Architecture</span>
                  </div>
                  <div className="preview-box-body">
                    <div className="diagram-layer">
                      <span className="d-label">Surface Layer</span>
                      <strong>Crop Canopy & Surface Mulch</strong>
                      <small>Light interception, vegetative cover, and surface evaporation</small>
                    </div>
                    <div className="diagram-connector">↓</div>
                    <div className="diagram-layer active">
                      <span className="d-label">Rhizosphere</span>
                      <strong>Active Expanding Root Zone</strong>
                      <small>Water uptake, nutrient absorption, and moisture tension</small>
                    </div>
                    <div className="diagram-connector">↓</div>
                    <div className="diagram-layer">
                      <span className="d-label">Subsoil Horizon</span>
                      <strong>Deep Soil Moisture Reservoir</strong>
                      <small>Drainage conductivities, deep percolation, and storage</small>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================
            4. WEATHER INTELLIGENCE
            ======================================================== */}
        <section id="weather" className="landing-section">
          <div className="section-container">
            <div className="section-header-compact">
              <span className="section-eyebrow">Atmospheric Telemetry</span>
              <h2 className="section-title">Weather Intelligence & Environmental Ensembles</h2>
              <p className="section-subtitle">
                Understanding how dynamic atmospheric conditions drive crop water demand, evaporative losses,
                and optimal timing for field operations.
              </p>
            </div>

            <div className="feature-cards-grid">
              <div className="capability-card">
                <div className="card-glyph">📡</div>
                <h3>Real-Time Weather Integration</h3>
                <p>
                  Continuously monitors local weather variables including precipitation, temperature extremes,
                  solar radiation, relative humidity, and wind speed.
                </p>
              </div>

              <div className="capability-card">
                <div className="card-glyph">📆</div>
                <h3>Multi-Day Forecast Ensembles</h3>
                <p>
                  Utilizes deterministic and ensemble forecasts to anticipate upcoming weather patterns,
                  identifying rain windows, dry spells, and potential frost or heat events.
                </p>
              </div>

              <div className="capability-card">
                <div className="card-glyph">💨</div>
                <h3>Atmospheric Evaporative Demand</h3>
                <p>
                  Computes reference evapotranspiration (ET₀) and vapor pressure deficit (VPD) to determine
                  the atmospheric suction driving plant transpiration and soil evaporation.
                </p>
              </div>

              <div className="capability-card">
                <div className="card-glyph">🛡</div>
                <h3>Weather-Driven Action Guidance</h3>
                <p>
                  Translates weather forecasts into operational advice, such as postponing scheduled irrigation
                  before heavy rainfall or shielding crops ahead of high evaporative demand.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================
            5. CROP PLANNING & CROP LENS
            ======================================================== */}
        <section id="crop-planning" className="landing-section">
          <div className="section-container">
            <div className="section-header-compact">
              <span className="section-eyebrow">Botanical Intelligence</span>
              <h2 className="section-title">Crop Planning & Crop Lens</h2>
              <p className="section-subtitle">
                Understand crop growth stages, botanical characteristics, and evidence-grounded recommendations
                tailored to specific agricultural environments.
              </p>
            </div>

            <div className="deep-dive-card">
              <div className="deep-dive-grid">
                <div className="deep-dive-text">
                  <h3>Evidence-Grounded Crop Modeling</h3>
                  <p>
                    Crop Lens resolves botanical identities and automatically provisions scientific parameters
                    to model crop development, water sensitivity, and seasonal milestones.
                  </p>
                  <ul className="capability-bullet-list">
                    <li>
                      <strong>Crop Growth Stages:</strong> Tracks developmental progression from emergence and
                      vegetative canopy expansion to flowering, grain fill, and maturity.
                    </li>
                    <li>
                      <strong>Crop-Specific Insights:</strong> Models species-specific crop coefficients, rooting
                      depth curves, and water stress response factors.
                    </li>
                    <li>
                      <strong>Seasonal Crop Planning:</strong> Assists in selecting suitable crop varieties and
                      sowing windows based on regional agro-climatic conditions.
                    </li>
                    <li>
                      <strong>Agricultural Recommendations:</strong> Provides agronomic guidance regarding spacing,
                      nutrient timing, and moisture thresholds.
                    </li>
                    <li>
                      <strong>Multilingual Accessibility:</strong> Supports local languages such as English,
                      Hindi, and Kannada for inclusive, accessible agricultural knowledge.
                    </li>
                  </ul>
                </div>

                <div className="deep-dive-preview-box">
                  <div className="preview-box-header">
                    <span className="preview-dot" />
                    <span className="preview-dot" />
                    <span className="preview-dot" />
                    <span className="preview-title">Phenological Progression</span>
                  </div>
                  <div className="preview-box-body">
                    <div className="timeline-step-item">
                      <div className="step-circle">1</div>
                      <div className="step-content">
                        <strong>Establishment & Emergence</strong>
                        <small>Initial root development and seedling emergence</small>
                      </div>
                    </div>
                    <div className="timeline-step-item">
                      <div className="step-circle active">2</div>
                      <div className="step-content">
                        <strong>Vegetative Canopy Expansion</strong>
                        <small>Rapid leaf area expansion and root-zone deepening</small>
                      </div>
                    </div>
                    <div className="timeline-step-item">
                      <div className="step-circle">3</div>
                      <div className="step-content">
                        <strong>Flowering & Reproductive Phase</strong>
                        <small>Critical moisture-sensitive pollination window</small>
                      </div>
                    </div>
                    <div className="timeline-step-item">
                      <div className="step-circle">4</div>
                      <div className="step-content">
                        <strong>Yield Formation & Ripening</strong>
                        <small>Biomass partitioning and dry-down toward harvest</small>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================
            6. WATER LEDGER
            ======================================================== */}
        <section id="water-ledger" className="landing-section">
          <div className="section-container">
            <div className="section-header-compact">
              <span className="section-eyebrow">Resource Management</span>
              <h2 className="section-title">Water Ledger: Shared Resource Accounting</h2>
              <p className="section-subtitle">
                Track farm-wide water availability, application efficiency, and root-zone moisture balance
                to support sustainable irrigation management.
              </p>
            </div>

            <div className="feature-cards-grid">
              <div className="capability-card">
                <div className="card-glyph">💧</div>
                <h3>Water Resource Monitoring</h3>
                <p>
                  Monitors storage reserves in farm reservoirs, irrigation tanks, and distribution channels,
                  providing clear visibility into available water volume.
                </p>
              </div>

              <div className="capability-card">
                <div className="card-glyph">⚖️</div>
                <h3>Soil-Water Balance Accounting</h3>
                <p>
                  Calculates daily root-zone water balance, accounting for rainfall infiltration, crop
                  transpiration, soil evaporation, and deep percolation losses.
                </p>
              </div>

              <div className="capability-card">
                <div className="card-glyph">🚰</div>
                <h3>Irrigation Planning & Allocation</h3>
                <p>
                  Coordinates water distribution across multiple competing plots to ensure moisture is
                  delivered when and where it produces the greatest crop benefit.
                </p>
              </div>

              <div className="capability-card">
                <div className="card-glyph">🌿</div>
                <h3>Water Conservation</h3>
                <p>
                  Identifies conveyance and application losses, compares irrigation method efficiencies (such as
                  drip vs. furrow), and protects safe storage reserves.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================
            7. AGRICULTURAL CALENDAR
            ======================================================== */}
        <section id="calendar" className="landing-section">
          <div className="section-container">
            <div className="section-header-compact">
              <span className="section-eyebrow">Seasonal Planning</span>
              <h2 className="section-title">Agricultural Calendar: Seasonal Planning</h2>
              <p className="section-subtitle">
                Synchronize farm operations with seasonal cultivation cycles, crop scheduling, and important
                agricultural milestones.
              </p>
            </div>

            <div className="calendar-cards-grid">
              <div className="season-card">
                <span className="season-badge kharif">Monsoon Season</span>
                <h3>Kharif Cultivation</h3>
                <p>
                  Focuses on monsoon-sown crops, matching planting dates to monsoon onset, managing field
                  drainage, and scheduling supplementary irrigation during dry intervals.
                </p>
                <div className="season-meta">
                  <span>Key Activities:</span>
                  <strong>Monsoon sowing, drainage checks, vegetative monitoring</strong>
                </div>
              </div>

              <div className="season-card">
                <span className="season-badge rabi">Winter Season</span>
                <h3>Rabi Cultivation</h3>
                <p>
                  Focuses on post-monsoon and winter cultivation, monitoring cooler temperatures, tracking
                  residual soil moisture, and managing critical irrigation stages.
                </p>
                <div className="season-meta">
                  <span>Key Activities:</span>
                  <strong>Winter sowing, Crown Root Initiation, grain fill irrigation</strong>
                </div>
              </div>

              <div className="season-card">
                <span className="season-badge zaid">Summer Season</span>
                <h3>Zaid Cultivation</h3>
                <p>
                  Focuses on short-duration summer pulses and vegetables, managing high evaporative demand,
                  micro-irrigation scheduling, and soil moisture conservation.
                </p>
                <div className="season-meta">
                  <span>Key Activities:</span>
                  <strong>Short-duration crops, heat management, micro-irrigation</strong>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================
            8. FUTURE FOLD: Scenario Simulation
            ======================================================== */}
        <section id="future-fold" className="landing-section">
          <div className="section-container">
            <div className="section-header-compact">
              <span className="section-eyebrow">Scenario Comparison</span>
              <h2 className="section-title">Future Fold: Scenario Simulation</h2>
              <p className="section-subtitle">
                Compare alternative agricultural decisions under identical weather trajectories before making
                commitments in the field.
              </p>
            </div>

            <div className="deep-dive-card">
              <div className="deep-dive-grid">
                <div className="deep-dive-text">
                  <h3>Decision Intelligence Through Comparative Modeling</h3>
                  <p>
                    Future Fold enables growers to simulate competing management pathways side by side, quantifying
                    trade-offs between crop protection, water savings, and reservoir reserves.
                  </p>
                  <ul className="capability-bullet-list">
                    <li>
                      <strong>Alternative Agricultural Scenarios:</strong> Evaluates the difference between
                      standard practice, delayed watering, and proactive scheduled irrigation.
                    </li>
                    <li>
                      <strong>Comparing Irrigation Strategies:</strong> Simulates how varying application depths,
                      delivery timing, or irrigation methods impacts crop moisture stress.
                    </li>
                    <li>
                      <strong>Understanding Rainfall Variations:</strong> Analyzes crop and soil response if
                      upcoming rainfall is lower than projected or delayed by several days.
                    </li>
                    <li>
                      <strong>Exploring Growth Outcomes:</strong> Projects how alternative choices influence
                      canopy expansion, stomatal conductance, and final yield potential.
                    </li>
                    <li>
                      <strong>Informed Agricultural Decisions:</strong> Delivers quantitative decision scores that
                      balance crop protection against resource conservation.
                    </li>
                  </ul>
                </div>

                <div className="deep-dive-preview-box">
                  <div className="preview-box-header">
                    <span className="preview-dot" />
                    <span className="preview-dot" />
                    <span className="preview-dot" />
                    <span className="preview-title">Scenario Comparison Framework</span>
                  </div>
                  <div className="preview-box-body">
                    <div className="scenario-comparison-row">
                      <div className="scenario-box branch-a">
                        <span className="sc-badge">Branch A</span>
                        <strong>Standard / Delayed Practice</strong>
                        <p>Rainfed baseline with delayed irrigation. Evaluates crop stress risk under high evaporative demand.</p>
                      </div>
                      <div className="scenario-vs">VS</div>
                      <div className="scenario-box branch-b">
                        <span className="sc-badge highlight">Branch B</span>
                        <strong>Proactive Management</strong>
                        <p>Optimized scheduled irrigation ahead of weather stress. Measures water savings and stress relief.</p>
                      </div>
                    </div>
                    <div className="scenario-score-pill">
                      <span>Quantitative Decision Scoring:</span>
                      <strong>Balances Crop Protection & Resource Conservation</strong>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================
            9. REAL-TIME ALERTS & FARM TIMELINE
            ======================================================== */}
        <section id="alerts-timeline" className="landing-section">
          <div className="section-container">
            <div className="section-header-compact">
              <span className="section-eyebrow">Alerts & Milestones</span>
              <h2 className="section-title">Real-Time Alerts & Farm Timeline</h2>
              <p className="section-subtitle">
                Stay informed of emerging field conditions and track the historical and projected progression
                of the farm across the cultivation cycle.
              </p>
            </div>

            <div className="alerts-timeline-grid">
              <div className="capability-card">
                <div className="card-glyph">🔔</div>
                <h3>Agricultural Condition Alerts</h3>
                <p>
                  Automated notifications triggered when soil moisture approaches critical thresholds, extreme
                  weather events are forecast, or milestone actions are recommended.
                </p>
                <div className="feature-sub-points">
                  <span>✓ Moisture stress threshold warnings</span>
                  <span>✓ Forecast rainfall review notifications</span>
                  <span>✓ Milestone scheduling reminders</span>
                </div>
              </div>

              <div className="capability-card">
                <div className="card-glyph">📱</div>
                <h3>Multi-Channel Notification</h3>
                <p>
                  Delivers timely intelligence directly through in-app notification trays and mobile messaging
                  channels like Telegram, ensuring alerts are received before field damage occurs.
                </p>
                <div className="feature-sub-points">
                  <span>✓ In-app real-time notification tray</span>
                  <span>✓ Telegram push messaging integration</span>
                  <span>✓ Deduplication & quiet-hours policy</span>
                </div>
              </div>

              <div className="capability-card">
                <div className="card-glyph">⏱</div>
                <h3>Farm Progression Timeline</h3>
                <p>
                  An immutable chronological record documenting field activities, irrigation events, soil
                  measurements, and developmental milestones from sowing to harvest.
                </p>
                <div className="feature-sub-points">
                  <span>✓ Complete operational audit trail</span>
                  <span>✓ Historical milestone documentation</span>
                  <span>✓ Future developmental projections</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================
            10. CLOSING VISION CTA
            ======================================================== */}
        <section id="vision" className="landing-section final-vision-section">
          <div className="section-container text-center">
            <div className="vision-badge">{tUI(locale, "heroEyebrow")}</div>
            <h2 className="vision-title">
              {tUI(locale, "readyHeading")}
            </h2>
            <p className="vision-desc">
              {tUI(locale, "readySub")}
            </p>

            <div className="vision-cta-group">
              <button
                type="button"
                className="vision-btn-primary"
                onClick={() => (navigate ? navigate("/register") : scrollToSection("hero"))}
              >
                {tUI(locale, "getStarted")}
              </button>
              <button
                type="button"
                className="vision-btn-secondary"
                onClick={() => (navigate ? navigate("/dashboard") : scrollToSection("solution"))}
              >
                {tUI(locale, "openDecisionLab")}
              </button>
              <button
                type="button"
                className="vision-btn-secondary"
                onClick={() => navigate ? navigate("/dashboard?tab=future-fold") : scrollToSection("future-fold")}
              >
                Discover Future Fold <span>↗</span>
              </button>
              <button
                type="button"
                className="vision-btn-secondary"
                onClick={() => scrollToSection("hero")}
              >
                Return to Top <span>↑</span>
              </button>
            </div>
          </div>
        </section>

        {/* ========================================================
            FOOTER: Scientific Footing Citations
            ======================================================== */}
        <footer className="landing-footer">
          <div className="footer-content">
            <div className="footer-brand">
              <span className="brand-gem">◈</span> TerraPulse Decision Laboratory
              <p>Intelligent Agricultural Decision Support · Colossus 3.0</p>
            </div>
            <div className="footer-engines">
              <span>Scientific Foundation:</span>
              <strong>AquaCrop-OSPy</strong> ·
              <strong>FAO-56 Dual Kc</strong> ·
              <strong>ISRIC SoilGrids</strong> ·
              <strong>Open-Meteo Ensembles</strong> ·
              <strong>FAO AGROVOC</strong>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
