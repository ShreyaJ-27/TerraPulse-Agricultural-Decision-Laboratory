import { useState, useRef, useEffect, Suspense, lazy } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import "../landing.css";

// 3D Scene components
function AnimatedField() {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const count = 300;
  const dummy = useRef(new THREE.Object3D());

  const positions = useRef(
    Array.from({ length: count }, (_, i) => {
      const row = Math.floor(i / 15);
      const col = i % 15;
      return {
        x: (col - 7.5) * 2.2 + (Math.sin(i) * 0.3),
        z: (row - 10) * 2.5 + (Math.cos(i) * 0.3),
        scale: 0.8 + Math.random() * 0.4,
        rot: Math.random() * Math.PI,
        color: i % 3 === 0 ? "#7fa356" : i % 3 === 1 ? "#cca042" : "#5d8a43",
      };
    })
  );

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const t = clock.getElapsedTime();
    positions.current.forEach((pos, i) => {
      const sway = Math.sin(t * 1.8 + pos.x * 0.5 + pos.z * 0.3) * 0.12;
      dummy.current.position.set(pos.x, 0.9 * pos.scale, pos.z);
      dummy.current.rotation.set(sway, pos.rot + sway * 0.5, sway * 0.5);
      dummy.current.scale.set(pos.scale, pos.scale * (1 + Math.sin(t * 0.5 + i) * 0.05), pos.scale);
      dummy.current.updateMatrix();
      meshRef.current!.setMatrixAt(i, dummy.current.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <group>
      {/* Ground Terrain */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]} receiveShadow>
        <planeGeometry args={[120, 120, 32, 32]} />
        <meshStandardMaterial color="#2d3d27" roughness={0.9} metalness={0.1} />
      </mesh>

      {/* Plots distinction strips */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[-10, 0, 0]} receiveShadow>
        <planeGeometry args={[18, 45]} />
        <meshStandardMaterial color="#3f4e32" roughness={0.8} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[10, 0, 0]} receiveShadow>
        <planeGeometry args={[18, 45]} />
        <meshStandardMaterial color="#444129" roughness={0.8} />
      </mesh>

      {/* Instanced Crops */}
      <instancedMesh ref={meshRef} args={[undefined, undefined, count]} castShadow receiveShadow>
        <cylinderGeometry args={[0.08, 0.14, 2.2, 5]} />
        <meshStandardMaterial color="#739744" roughness={0.6} />
      </instancedMesh>
    </group>
  );
}

function SkyAtmosphere() {
  return (
    <>
      <ambientLight intensity={0.65} color="#e6f2dc" />
      <directionalLight
        position={[25, 35, 15]}
        intensity={1.4}
        color="#fff5db"
        castShadow
        shadow-mapSize={[1024, 1024]}
      />
      <directionalLight position={[-20, 15, -20]} intensity={0.3} color="#9ec2a8" />
      <fog attach="fog" args={["#1b2d22", 20, 65]} />
    </>
  );
}

type Props = {
  navigate: (path: string) => void;
};

export function LandingPage({ navigate }: Props) {
  const [activeTab, setActiveTab] = useState<number>(0);
  const [webglSupported, setWebglSupported] = useState(true);

  useEffect(() => {
    try {
      const c = document.createElement("canvas");
      setWebglSupported(!!(window.WebGLRenderingContext && (c.getContext("webgl") || c.getContext("experimental-webgl"))));
    } catch {
      setWebglSupported(false);
    }
  }, []);

  const experiences = [
    {
      id: "living-field",
      title: "Living Field",
      badge: "Cinematic 3D Landscape",
      desc: "Immerse yourself in a living, navigable 3D agricultural terrain. Inspect multi-layered soil profiles (sand, silt, clay, bulk density, wilting point), dynamic canopy coverage, and root-zone water balance calculated directly from verified models.",
      points: ["Full 3D orbit, tilt and zoom camera", "Soil cross-section cutaway with depth strata", "Plot-by-plot canopy development visualization", "Direct integration with ISRIC SoilGrids WCS data"],
      action: "Explore 3D Field",
      path: "/dashboard?tab=living-field",
      icon: "🌱"
    },
    {
      id: "future-fold",
      title: "Future Fold",
      badge: "Alternative Decision Comparator",
      desc: "Simulate and compare two independently computed farming futures under identical weather trajectories. Quantify water stress reduction, irrigation volume savings, and crop protection trade-offs before executing decisions in the field.",
      points: ["Side-by-side synchronized temporal comparison", "Controlled weather realizations for fair testing", "Water Decision Scoring: 60% Protection, 25% Efficiency, 15% Reserve", "Multi-branch decision trees without mutating history"],
      action: "Test Alternative Futures",
      path: "/dashboard?tab=future-fold",
      icon: "↗"
    },
    {
      id: "calendar",
      title: "Agricultural Calendar 2.0",
      badge: "Season-Wise Dynamic Intelligence",
      desc: "Comprehensive crop scheduling across Kharif, Rabi, and Zaid seasons. Integrates Punjab Agricultural University (PAU) and UAS Bengaluru packages of practices with sowing windows, Crown Root Initiation, silking, and harvest deadlines.",
      points: ["Season-specific crop scheduling (Kharif, Rabi, Zaid)", "Regional variations with verified university sources", "Growth stage milestones with scientific explanations", "Weather-dependent sowing and irrigation activity alerts"],
      action: "View Agricultural Calendar",
      path: "/dashboard?tab=calendar",
      icon: "📅"
    },
    {
      id: "alerts",
      title: "Real-Time Notifications & Telegram",
      badge: "Autonomous Alert Engine",
      desc: "Proactive farm intelligence delivered directly into your Telegram chat and dashboard notification tray. Extreme weather warnings, forecast rain reviews, and AquaCrop water-stress alerts keep farmers informed before damage occurs.",
      points: ["Instant Telegram push alerts with deep-link linking", "In-app real-time notification feed", "Deduplication and quiet-hours policy enforcement", "Modelled water-stress and precipitation warnings"],
      action: "Inspect Live Notifications",
      path: "/dashboard?tab=notifications",
      icon: "🔔"
    },
    {
      id: "crop-lens",
      title: "Crop Lens",
      badge: "Authoritative Botanical Resolution",
      desc: "Enter any crop in English, Hindi, or Kannada. Crop Lens dynamically resolves botanical identities against FAO AGROVOC, GBIF, and ECOCROP—automatically binding the verified scientific simulation pathway (AquaCrop or FAO-56).",
      points: ["Multilingual query support (English, Hindi, Kannada)", "No restrictive hardcoded whitelists", "Curated parameter provenance tracking", "Off-catalogue crop registration with research references"],
      action: "Launch Crop Lens",
      path: "/dashboard?tab=crop-lens",
      icon: "🔍"
    },
    {
      id: "water-ledger",
      title: "Shared Water Management",
      badge: "Branch-Scoped Ledger",
      desc: "Manage farm-wide irrigation reservoirs across multiple competing plots. Track gross withdrawals, root-zone effective irrigation, and remaining storage reserves with strict conservation accounting.",
      points: ["750,000L reservoir capacity accounting", "Plot-by-plot allocation authorizations", "Conveyance efficiency & drainage loss metrics", "Immutable audit trail across simulation branches"],
      action: "Manage Farm Water",
      path: "/dashboard?tab=water",
      icon: "💧"
    }
  ];

  return (
    <div className="landing-root">
      {/* Top Navbar */}
      <header className="landing-header">
        <div className="landing-nav-container">
          <div className="landing-brand" onClick={() => navigate("/")}>
            <span className="brand-gem">◈</span>
            <span className="brand-text">TerraPulse</span>
            <span className="brand-tag">Decision Lab</span>
          </div>
          <nav className="landing-links">
            <button onClick={() => navigate("/dashboard?tab=overview")}>Overview</button>
            <button onClick={() => navigate("/dashboard?tab=living-field")}>Living Field</button>
            <button onClick={() => navigate("/dashboard?tab=calendar")}>Agri Calendar</button>
            <button onClick={() => navigate("/dashboard?tab=future-fold")}>Future Fold</button>
            <button onClick={() => navigate("/dashboard?tab=notifications")}>Notifications</button>
          </nav>
          <div className="landing-nav-actions">
            <button
              className="demo-btn-top"
              onClick={() => navigate("/dashboard?farmId=00000000-0000-0000-0000-000000000001")}
            >
              Enter Demo Farm <span>✨</span>
            </button>
            <button className="primary-btn-top" onClick={() => navigate("/dashboard")}>
              Launch Dashboard <span>→</span>
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section with 3D Canvas */}
      <section className="landing-hero">
        <div className="hero-canvas-wrap">
          {webglSupported ? (
            <Canvas camera={{ position: [0, 8, 22], fov: 42 }}>
              <SkyAtmosphere />
              <AnimatedField />
            </Canvas>
          ) : (
            <div className="fallback-canvas">
              <div className="fallback-grid" />
            </div>
          )}
          <div className="hero-gradient-overlay" />
        </div>

        <div className="hero-content">
          <div className="hero-badge">
            <span className="pulse-dot" /> Live Agricultural Intelligence Laboratory · Colossus 3.0
          </div>
          <h1 className="hero-headline">
            Explore the farm.<br />
            <span className="highlight-text">Change the future.</span><br />
            Test your decisions.
          </h1>
          <p className="hero-subtitle">
            An immersive decision laboratory combining 3D spatial exploration,
            authoritative crop simulation (AquaCrop-OSPy & FAO-56), and seasonal environmental ensembles.
          </p>

          <div className="hero-cta-group">
            <button
              className="hero-btn-primary"
              onClick={() => navigate("/dashboard?farmId=00000000-0000-0000-0000-000000000001")}
            >
              Enter Demo Farm (Punjab & Karnataka Model) <span>🚀</span>
            </button>
            <button
              className="hero-btn-secondary"
              onClick={() => navigate("/dashboard")}
            >
              Open Full Dashboard <span>▤</span>
            </button>
            <button
              className="hero-btn-outline"
              onClick={() => navigate("/dashboard?tab=living-field")}
            >
              Interactive 3D Field <span>🌱</span>
            </button>
          </div>

          {/* Quick Metrics Bar */}
          <div className="hero-metrics-bar">
            <div className="metric-chip">
              <strong>10 Sourced Species</strong>
              <span>AGROVOC & ECOCROP</span>
            </div>
            <div className="metric-chip">
              <strong>Kharif · Rabi · Zaid</strong>
              <span>Season-wise Intelligence</span>
            </div>
            <div className="metric-chip">
              <strong>42.5% Stress Relief</strong>
              <span>Future Fold Validation</span>
            </div>
            <div className="metric-chip">
              <strong>Telegram & In-App</strong>
              <span>Real-Time Alert Engine</span>
            </div>
          </div>
        </div>
      </section>

      {/* Core Experiences Section */}
      <section className="landing-features">
        <div className="section-header">
          <span className="eyebrow">Scientific Capabilities</span>
          <h2>The TerraPulse Decision Architecture</h2>
          <p>Explore our integrated decision modules designed for farmers, agronomists, and researchers.</p>
        </div>

        <div className="experience-tabs-nav">
          {experiences.map((exp, idx) => (
            <button
              key={exp.id}
              className={`exp-tab-btn ${activeTab === idx ? "active" : ""}`}
              onClick={() => setActiveTab(idx)}
            >
              <span className="tab-icon">{exp.icon}</span>
              <span className="tab-text">{exp.title}</span>
            </button>
          ))}
        </div>

        <div className="experience-card">
          <div className="card-left">
            <div className="exp-badge">{experiences[activeTab].badge}</div>
            <h3>{experiences[activeTab].title}</h3>
            <p className="exp-desc">{experiences[activeTab].desc}</p>
            <ul className="exp-points">
              {experiences[activeTab].points.map((pt, i) => (
                <li key={i}>
                  <span className="check-icon">✓</span> {pt}
                </li>
              ))}
            </ul>
            <button
              className="exp-action-btn"
              onClick={() => navigate(experiences[activeTab].path)}
            >
              {experiences[activeTab].action} <span>→</span>
            </button>
          </div>
          <div className="card-right">
            <div className="interactive-preview-box">
              <div className="preview-header">
                <span className="dot red" />
                <span className="dot yellow" />
                <span className="dot green" />
                <span className="preview-title">Live Engine · {experiences[activeTab].title}</span>
              </div>
              <div className="preview-body">
                {activeTab === 0 && (
                  <div className="preview-scene-mock">
                    <div className="mock-stat">
                      <span>Soil Texture:</span> <strong>Sandy Loam (0-120cm)</strong>
                    </div>
                    <div className="mock-stat">
                      <span>Root Zone Depth:</span> <strong>0.85 m (Expanding)</strong>
                    </div>
                    <div className="mock-stat">
                      <span>Canopy Coverage:</span> <strong>68.5%</strong>
                    </div>
                    <div className="mock-bar-wrap">
                      <div className="bar-label">Available Soil Water</div>
                      <div className="bar-track"><div className="bar-fill" style={{ width: "64%" }} /></div>
                    </div>
                  </div>
                )}
                {activeTab === 1 && (
                  <div className="preview-scene-mock">
                    <div className="diff-tag positive">Water Stress Reduction: -42.5%</div>
                    <div className="mock-stat">
                      <span>Baseline Rainfed Ks:</span> <strong className="text-warn">0.58 (Moderate Stress)</strong>
                    </div>
                    <div className="mock-stat">
                      <span>Alternative Irrigated Ks:</span> <strong className="text-good">0.88 (Protected)</strong>
                    </div>
                    <div className="mock-stat">
                      <span>Decision Score:</span> <strong>86.7 / 100</strong>
                    </div>
                  </div>
                )}
                {activeTab === 2 && (
                  <div className="preview-scene-mock">
                    <div className="mock-stat">
                      <span>Current Active Season:</span> <strong>Rabi 2026-27</strong>
                    </div>
                    <div className="mock-stat">
                      <span>Next Critical Milestone:</span> <strong>Crown Root Initiation (Day 21)</strong>
                    </div>
                    <div className="mock-stat">
                      <span>Regional Guidance:</span> <strong>PAU Package of Practices p. 12</strong>
                    </div>
                  </div>
                )}
                {activeTab === 3 && (
                  <div className="preview-scene-mock">
                    <div className="diff-tag info">Telegram Push Connected (@TerraPulseFarmerBot)</div>
                    <div className="mock-stat">
                      <span>Upcoming Alert:</span> <strong>Forecast Rain Review (28.4mm tomorrow)</strong>
                    </div>
                    <div className="mock-stat">
                      <span>Recommendation:</span> <strong>Postpone scheduled furrow irrigation by 48h</strong>
                    </div>
                  </div>
                )}
                {activeTab === 4 && (
                  <div className="preview-scene-mock">
                    <div className="mock-stat">
                      <span>Query:</span> <strong>"ಅರಿಶಿನ" / "हल्दी" / "Turmeric"</strong>
                    </div>
                    <div className="mock-stat">
                      <span>Resolved Species:</span> <strong>Curcuma longa (Zingiberaceae)</strong>
                    </div>
                    <div className="mock-stat">
                      <span>Scientific Model:</span> <strong>FAO-56 Expanding Root Accounting</strong>
                    </div>
                  </div>
                )}
                {activeTab === 5 && (
                  <div className="preview-scene-mock">
                    <div className="mock-stat">
                      <span>Reservoir Opening Volume:</span> <strong>750,000 Litres (750 m³)</strong>
                    </div>
                    <div className="mock-stat">
                      <span>Allocations (3 Plots):</span> <strong>340,000 L Withdrawn</strong>
                    </div>
                    <div className="mock-stat">
                      <span>Remaining Safe Reserve:</span> <strong className="text-good">410,000 L (54.7%)</strong>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Demo Farm Callout for Judges */}
      <section className="landing-demo-callout">
        <div className="callout-card">
          <div className="callout-text">
            <span className="callout-pill">Judge Walkthrough Mode</span>
            <h2>Experience TerraPulse End-to-End</h2>
            <p>
              Launch the official demonstration farm seeded with Punjab Agricultural University (PAU)
              and Karnataka Research Station parameters. Test multicrop coordination, 3D soil cutaways,
              irrigation ledger withdrawals, Telegram alerts, and seasonal calendar intelligence.
            </p>
          </div>
          <div className="callout-actions">
            <button
              className="callout-btn"
              onClick={() => navigate("/dashboard?farmId=00000000-0000-0000-0000-000000000001")}
            >
              Launch Demo Farm Now <span>✨</span>
            </button>
          </div>
        </div>
      </section>

      {/* Scientific Footing Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <span className="brand-gem">◈</span> TerraPulse Decision Laboratory
            <p>Built for Colossus 3.0 · Team Kalakand · Approved Specification v1.0</p>
          </div>
          <div className="footer-engines">
            <span>Powered by:</span>
            <strong>AquaCrop-OSPy 3.1.0</strong> ·
            <strong>FAO-56 Dual Kc</strong> ·
            <strong>ISRIC SoilGrids WCS</strong> ·
            <strong>Open-Meteo Ensemble</strong> ·
            <strong>FAO AGROVOC</strong>
          </div>
        </div>
      </footer>
    </div>
  );
}
