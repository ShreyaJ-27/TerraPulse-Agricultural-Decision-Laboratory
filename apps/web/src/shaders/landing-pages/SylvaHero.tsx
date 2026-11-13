import { useMemo } from "react";

import {
  splitTypographyProps,
  usePageTypography,
  type PageTypographyProps,
} from "./pageTypography";
import { SYLVA_TYPOGRAPHY } from "./pageRecipes";
import { LandingPageFrame, type LandingPageProps } from "./LandingPageFrame";
export { LandingPageFrame, applyBackgroundPresentation } from "./LandingPageFrame";
export type { LandingPageFrameProps, LandingPageProps } from "./LandingPageFrame";
import innerGreenSource from "../sylva-living-world/sources/inner-green-3d.html?raw";
import {
  SAKURA_SUNSET_STYLE,
  MAPLE_AUTUMN_STYLE,
  SEQUOIA_MIST_STYLE,
  applySakuraSunsetVariant,
  applyMapleAutumnVariant,
  applySequoiaMistVariant,
} from "../sylva-living-world/SylvaLivingWorldScene";

export const SYLVA_HERO_VARIANTS = ["living-green", "sakura-sunset", "maple-autumn", "sequoia-mist"] as const;
export type SylvaHeroVariant = (typeof SYLVA_HERO_VARIANTS)[number];

export type SylvaHeroProps = LandingPageProps & PageTypographyProps & { variant?: SylvaHeroVariant };

const SYLVA_HERO_BASE_URL = "/landing-pages/inner-green-3d.html";

/**
 * The authored page is served byte-for-byte for Living Green. Sakura Sunset is derived:
 * the same authored document with the owner's authored Sakura Sunset scene transformation
 * applied — reused from SylvaLivingWorldScene rather than reimplemented here, so the two
 * entries can never drift apart. A <base> is injected because a srcdoc frame would otherwise
 * resolve the authored relative asset paths against the app origin instead of /landing-pages/.
 */
const SYLVA_HERO_ASSET_DIR = "inner-green-assets/";
const SYLVA_HERO_ASSET_BASE = `${SYLVA_HERO_BASE_URL.replace(/[^/]+$/, "")}${SYLVA_HERO_ASSET_DIR}`;

/**
 * Page chrome for the derived variants. Each one puts a different field behind
 * the page — dusk plum under Sakura, cold slate under Maple — so the dock is
 * retoned to sit in that light, and the two native controls get the frosted
 * backdrop a flat field no longer gives them for free.
 *
 * The authored page documents why its dock carries no backdrop-filter: over a
 * canvas that repaints every frame the backdrop is re-sampled and re-blurred
 * every frame, which measured ~20 fps off the whole page. That reasoning still
 * holds for a bar the width of the nav, so the dock keeps its translucent panel
 * and only its colour changes. The buttons are small and already clipped to
 * their own silhouette, so the blur is bounded to those two shapes.
 */
type SylvaHeroChromeTone = {
  edge: string;
  lift: string;
  panel: string;
  drop: string;
  nearPanel: string;
  mark: string;
  markInk: string;
  plate: string;
};

const SYLVA_HERO_CHROME_TONES: Record<Exclude<SylvaHeroVariant, "living-green">, SylvaHeroChromeTone> = {
  "sakura-sunset": {
    edge: "255, 236, 243",
    lift: "255, 240, 246",
    panel: "48, 33, 43",
    drop: "20, 10, 18",
    nearPanel: "53, 35, 46",
    mark: "#f3e9ee",
    markInk: "#33222c",
    plate: "58, 40, 51",
  },
  "maple-autumn": {
    edge: "228, 240, 246",
    lift: "232, 244, 250",
    panel: "33, 41, 47",
    drop: "8, 14, 18",
    nearPanel: "37, 46, 53",
    mark: "#e8eff2",
    markInk: "#23303a",
    plate: "34, 46, 54",
  },
  /* The fog field is the one pale ground of the four, so this dock is the one
     that has to hold its own against light rather than sit in the dark. */
  "sequoia-mist": {
    edge: "236, 244, 232",
    lift: "238, 246, 232",
    panel: "38, 48, 40",
    drop: "16, 24, 18",
    nearPanel: "43, 54, 44",
    mark: "#eef3e8",
    markInk: "#26302a",
    plate: "48, 60, 50",
  },
};

function sylvaHeroChromeStyle(tone: SylvaHeroChromeTone) {
  return `<style data-threeui-sylva-hero-chrome>
/* ── nav: the authored glass, retoned to the field behind it ────────────── */
.dock {
  border-color: rgba(${tone.edge}, 0.13) !important;
  background:
    linear-gradient(180deg, rgba(${tone.lift}, 0.06), rgba(${tone.lift}, 0) 42%),
    rgba(${tone.panel}, 0.76) !important;
  box-shadow: 0 calc(8 * var(--u)) calc(22 * var(--u)) rgba(${tone.drop}, 0.34),
              inset 0 1px rgba(${tone.lift}, 0.07) !important;
}

.dock-item[data-near="true"] {
  border-color: rgba(${tone.edge}, 0.20) !important;
  background: rgba(${tone.nearPanel}, 0.94) !important;
  box-shadow: 0 calc(7 * var(--u)) calc(16 * var(--u)) rgba(${tone.drop}, 0.32) !important;
}

.dock-mark {
  background: ${tone.mark} !important;
  border-color: ${tone.mark} !important;
  color: ${tone.markInk} !important;
}

.dock-mark[data-near="true"] {
  background: #fff !important;
  border-color: #fff !important;
  color: ${tone.markInk} !important;
}

.dock-item--enter { background: rgba(${tone.lift}, 0.085) !important; }

/* ── the two native controls ────────────────────────────────────────────
   The frosted plate cannot go on the clip elements themselves: their clip is
   cut to the button's whole bloom, so the blur would read as a slab twice the
   button's size. It cannot go inside them either — clip-path makes a backdrop
   root, so a child's backdrop-filter would have nothing behind it to sample.

   So each plate is its own layer outside the reveal clip, sized one unit past
   the native 202 x 60 Explore control and the 88-unit Play control. The small
   overshoot lets the frost meet the button edge instead of stopping inside it. */
.pill-glass {
  position: absolute;
  z-index: 4;
  left: calc(644 * var(--u));
  top: calc(360 * var(--u));
  width: calc(204 * var(--u));
  height: calc(62 * var(--u));
  margin: calc(-31 * var(--u)) 0 0 calc(-102 * var(--u));
  border-radius: 999px;
  pointer-events: none;
  -webkit-backdrop-filter: blur(calc(13 * var(--u))) saturate(1.16);
  backdrop-filter: blur(calc(13 * var(--u))) saturate(1.16);
  background: rgba(${tone.plate}, 0.22);
}

.play-wrap::before {
  content: "";
  position: absolute;
  z-index: -1;
  left: 50%;
  top: 50%;
  width: calc(90 * var(--u));
  height: calc(90 * var(--u));
  margin: calc(-45 * var(--u)) 0 0 calc(-45 * var(--u));
  border-radius: 50%;
  -webkit-backdrop-filter: blur(calc(13 * var(--u))) saturate(1.16);
  backdrop-filter: blur(calc(13 * var(--u))) saturate(1.16);
  background: rgba(${tone.plate}, 0.22);
}
</style>`;
}

const SYLVA_HERO_SCENES: Record<Exclude<SylvaHeroVariant, "living-green">, {
  style: string;
  apply: (source: string) => string;
}> = {
  "sakura-sunset": { style: SAKURA_SUNSET_STYLE, apply: applySakuraSunsetVariant },
  "maple-autumn": { style: MAPLE_AUTUMN_STYLE, apply: applyMapleAutumnVariant },
  "sequoia-mist": { style: SEQUOIA_MIST_STYLE, apply: applySequoiaMistVariant },
};

export function buildSylvaHeroDocument(variant: Exclude<SylvaHeroVariant, "living-green">) {
  const scene = SYLVA_HERO_SCENES[variant];
  // The authored relative asset paths are rewritten to absolute ones rather than steered with
  // <base>: a srcdoc frame's preload scanner resolves against the parent document and ignores
  // <base>, so it would speculatively 404 on every asset before the real parse corrected it.
  const rooted = innerGreenSource
    .replaceAll(SYLVA_HERO_ASSET_DIR, SYLVA_HERO_ASSET_BASE)
    .replace("</head>", `${scene.style}${sylvaHeroChromeStyle(SYLVA_HERO_CHROME_TONES[variant])}</head>`)
    // The Explore button's frosted plate has to be a sibling of its clip rather
    // than a child, so it is one added element rather than a CSS-only change.
    .replace(
      '<div class="pill-clip">',
      '<span class="pill-glass" aria-hidden="true"></span>\n    <div class="pill-clip">',
    );
  if (!rooted.includes("pill-glass")) throw new Error("Sylva hero chrome no longer matches the authored page.");
  return scene.apply(rooted);
}

const SYLVA_HERO_TITLES: Record<SylvaHeroVariant, string> = {
  "living-green": "Sylva — Into the living world",
  "sakura-sunset": "Sylva — Sakura Sunset",
  "maple-autumn": "Sylva — Maple Autumn",
  "sequoia-mist": "Sylva — Sequoia Mist",
};

export function SylvaHero({ variant = "living-green", ...props }: SylvaHeroProps) {
  const safeVariant = SYLVA_HERO_VARIANTS.includes(variant) ? variant : "living-green";
  const [type, frame] = splitTypographyProps(props);
  const customization = usePageTypography(SYLVA_TYPOGRAPHY, type);
  const srcDoc = useMemo(
    () => (safeVariant === "living-green" ? undefined : buildSylvaHeroDocument(safeVariant)),
    [safeVariant],
  );

  return (
    <LandingPageFrame
      {...frame}
      key={safeVariant}
      customization={customization}
      title={SYLVA_HERO_TITLES[safeVariant]}
      sourceUrl={SYLVA_HERO_BASE_URL}
      srcDoc={srcDoc}
    />
  );
}
