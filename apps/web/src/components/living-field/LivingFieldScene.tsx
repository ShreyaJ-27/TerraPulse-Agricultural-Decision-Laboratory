import { Component, CSSProperties, lazy, ReactNode, Suspense, useCallback, useMemo, useState } from "react";
import { FieldLayout, FieldPlot, FieldSide, fieldLayout, sideColors } from "./fieldLayout";
import "./living-field.css";

const FarmCanvas = lazy(() => import("./FarmCanvas"));

type Metric = { label: string; value: string };
export type FieldScenario = {
  side: FieldSide;
  label: string;
  description?: string;
  metrics?: Metric[];
};

type Props = {
  plots: FieldPlot[];
  plotId: string;
  onSelectPlot: (id: string) => void;
  date: string;
  original: FieldScenario;
  alternative?: FieldScenario;
  side?: FieldSide;
  onChangeSide?: (side: FieldSide) => void;
  reduced?: boolean;
};

class SceneBoundary extends Component<{ children: ReactNode; onUnavailable: () => void }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch() { this.props.onUnavailable(); }
  render() { return this.state.failed ? null : this.props.children; }
}

function supportsWebGL() {
  if (typeof document === "undefined") return false;
  try {
    const context = document.createElement("canvas").getContext("webgl2");
    if (!context) return false;
    context.getExtension("WEBGL_lose_context")?.loseContext();
    return true;
  } catch {
    return false;
  }
}

function MapView({ layout, selected, tint, onSelect }: {
  layout: FieldLayout[]; selected: string; tint: string; onSelect: Props["onSelectPlot"];
}) {
  return <div className="lf-map" aria-label="Two-dimensional plot map">
    {layout.map((plot) =>
      <button key={plot.id} type="button" className="lf-map-plot" aria-pressed={plot.id === selected}
        onClick={() => onSelect(plot.id)} style={{ "--lf-accent": tint } as CSSProperties}>
        <span>{String(plot.index + 1).padStart(2, "0")}</span>{plot.label}
      </button>)}
  </div>;
}

function SoilSection({ plot, scenario }: { plot: FieldLayout; scenario: FieldScenario }) {
  return <div className="lf-soil">
    <svg viewBox="0 0 620 278" role="img" aria-label="Illustrative soil cross-section with a surface, roots and deeper soil">
      <rect width="620" height="278" fill="#becfc3" />
      <path d="M0 95 Q90 70 196 91 T390 91 T620 88 V140 H0Z" fill="#697b49" />
      <path d="M0 113 Q100 105 193 117 T393 114 T620 111 V170 Q500 162 390 173 T200 170 T0 174Z" fill="#77593e" />
      <path d="M0 174 Q95 162 200 170 T390 173 T620 170 V229 Q493 216 380 226 T190 220 T0 231Z" fill="#a57d51" />
      <path d="M0 231 Q99 213 190 220 T380 226 T620 229 V278 H0Z" fill="#bd9c70" />
      {Array.from({ length: 110 }, (_, i) => <ellipse key={i} cx={(i * 71 + 19) % 620} cy={122 + (i * 29 % 150)}
        rx={1 + i % 5} ry={0.65 + i % 3} fill={i % 3 === 0 ? "#efd1a3" : "#3d2f24"} opacity={0.27} />)}
      {[75, 161, 250, 350, 453, 548].map((x) => <g key={x} transform={"translate(" + x + " 112)"}>
        <path d="M0 7 Q-1 -16 2 -38 M1 -19 Q-13 -33 -24 -32 Q-22 -19 0 -14 M2 -27 Q18 -43 28 -40 Q21 -23 2 -23"
          fill="#47663a" stroke="#415e35" strokeWidth="3" strokeLinecap="round" />
        <path d="M0 0 Q-12 27 -4 55 M0 0 Q10 30 4 73 M-5 16 Q-25 29 -25 43 M4 20 Q28 39 18 55 M4 42 Q-5 50 -12 65"
          fill="none" stroke="#e4c094" strokeWidth="1.7" strokeLinecap="round" />
      </g>)}
      <path d="M603 119 H589 V194 H603" fill="none" stroke={sideColors[scenario.side]} strokeWidth="2" />
    </svg>
    <div className="lf-soil-copy">
      <strong>{plot.label}</strong>
      <ul><li><i /> Surface and plant cover</li><li><i /> Illustrative root zone</li><li><i /> Deeper soil</li></ul>
      <p>Layer thickness and root depth are schematic. Model quantities appear separately when available.</p>
    </div>
  </div>;
}

export function LivingFieldScene({
  plots, plotId, onSelectPlot, date, original, alternative, side, onChangeSide, reduced = false,
}: Props) {
  const layout = useMemo(() => fieldLayout(plots), [plots]);
  const selected = layout.find((plot) => plot.id === plotId) ?? layout[0];
  const [internalSide, setInternalSide] = useState<FieldSide>("original");
  const [mode, setMode] = useState<"farm" | "map" | "soil">("farm");
  const [unavailable, setUnavailable] = useState(() => !supportsWebGL());
  const [cameraCommand, setCamera] = useState<{ view: "overview" | "focus" | "ground"; revision: number }>({ view: "overview", revision: 0 });
  const [showRoots, setShowRoots] = useState(true);
  const [showMoisture, setShowMoisture] = useState(true);
  const [soilDepth, setSoilDepth] = useState(4);
  const markUnavailable = useCallback(() => setUnavailable(true), []);
  const changeCamera = (view: "overview" | "focus" | "ground") => setCamera((current) => ({ view, revision: current.revision + 1 }));
  if (!selected) return <p className="lf-empty">Add a plot to explore your field.</p>;

  const scenario = (side ?? internalSide) === "alternative" && alternative ? alternative : original;
  const tint = sideColors[scenario.side];
  const select = (id: string) => {
    if (id !== selected.id) onSelectPlot(id);
    changeCamera("focus");
  };
  const map = <MapView layout={layout} selected={selected.id} tint={tint} onSelect={select} />;
  const canvas = (mode === "farm" || mode === "soil") && !unavailable;
  const depthLabel = ["Shallow", "Root zone", "Subsoil", "Full column"][soilDepth - 1];

  return <section className="lf-shell" aria-label="Living Field" style={{ "--lf-accent": tint } as CSSProperties}>
    <div className="lf-stage">
      <div className="lf-stage-bar">
        <div><span className="lf-dot" /><strong>{selected.label}</strong><span className="lf-date">{date}</span></div>
        <div role="group" aria-label="Field view">
          {!unavailable && <button type="button" aria-pressed={mode === "farm"} onClick={() => setMode("farm")}>3D farm</button>}
          <button type="button" aria-pressed={mode === "map" || (unavailable && mode === "farm")} onClick={() => setMode("map")}>2D map</button>
          <button type="button" aria-pressed={mode === "soil"} onClick={() => setMode("soil")}>Soil section</button>
        </div>
      </div>
      <div className="lf-viewport">
        {canvas ? <SceneBoundary onUnavailable={markUnavailable}>
          <Suspense fallback={<div className="lf-loading" role="status">Loading 3D farm…{map}</div>}>
            <FarmCanvas layout={layout} selected={selected} side={scenario.side} reduced={reduced}
              mode={mode === "soil" ? "soil" : "farm"} showRoots={showRoots} showMoisture={showMoisture} soilDepth={soilDepth}
              cameraCommand={cameraCommand} onSelect={select} onUnavailable={markUnavailable} />
          </Suspense>
        </SceneBoundary> : mode === "soil" ? <SoilSection plot={selected} scenario={scenario} /> : map}
        {canvas && mode === "soil" && <div className="lf-tools" role="group" aria-label="Soil section controls">
          <label>Depth
            <input aria-label={"Soil depth, " + depthLabel} type="range" min={1} max={4} step={1} value={soilDepth}
              onChange={(event) => setSoilDepth(Number(event.target.value))} />
            <span>{depthLabel}</span>
          </label>
          <button type="button" aria-pressed={showRoots} onClick={() => setShowRoots((value) => !value)}>Roots</button>
          <button type="button" aria-pressed={showMoisture} onClick={() => setShowMoisture((value) => !value)}>Moisture</button>
        </div>}
        {canvas && <div className="lf-camera" role="group" aria-label="Camera controls">
          <button type="button" onClick={() => { setMode("farm"); changeCamera("overview"); }}>Farm overview</button>
          <button type="button" onClick={() => { setMode("farm"); changeCamera("focus"); }}>Focus plot</button>
          <button type="button" onClick={() => { setMode("farm"); changeCamera("ground"); }}>Ground level</button>
        </div>}
      </div>
      <div className="lf-stage-foot">
        <label>Plot<select aria-label="Plot" value={selected.id} onChange={(event) => select(event.target.value)}>
          {layout.map((plot) => <option key={plot.id} value={plot.id}>{plot.label}</option>)}
        </select></label>
        <span>{canvas && mode === "soil"
          ? "Illustrative cutaway of this plot. Depth, roots and moisture shading are schematic."
          : canvas ? "Drag to orbit · scroll or pinch to zoom · two fingers to pan"
          : unavailable && mode !== "soil" ? "3D unavailable · plot selection works in 2D"
          : "Illustrative farm geometry"}</span>
      </div>
    </div>
    <aside className="lf-info">
      <span className="lf-kicker">Decision view</span>
      {alternative && <div className="lf-scenarios" role="group" aria-label="Decision scenario">
        {[original, alternative].map((item) => <button type="button" key={item.side}
          aria-pressed={scenario.side === item.side} style={{ "--lf-chip": sideColors[item.side] } as CSSProperties}
          onClick={() => { setInternalSide(item.side); onChangeSide?.(item.side); }}>
          <i />{item.side === "original" ? "Original" : "Alternative"}
        </button>)}
      </div>}
      <h3>{scenario.label}</h3>
      {scenario.description && <p>{scenario.description}</p>}
      {scenario.metrics?.length ? <dl>{scenario.metrics.map((metric) =>
        <div key={metric.label}><dt>{metric.label}</dt><dd>{metric.value}</dd></div>)}</dl> : null}
      <p className="lf-note">{mode === "soil"
        ? "Soil layers, roots and moisture shading are illustrative geometry. Measured quantities stay in the indicators."
        : "Field layout and vegetation are illustrative. Crop type follows the selected plot."}</p>
    </aside>
  </section>;
}

export { examplePlots } from "./fieldLayout";
export type { FieldPlot, FieldSide } from "./fieldLayout";
