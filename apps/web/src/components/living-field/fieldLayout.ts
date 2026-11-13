export type FieldPlot = { id: string; label: string };
export type FieldLayout = FieldPlot & { x: number; z: number; index: number };
export type FieldSide = "original" | "alternative";

export const sideColors = { original: "#ffd080", alternative: "#89eaff" };
export const examplePlots: FieldPlot[] = [
  { id: "terrace", label: "Turmeric terrace" },
  { id: "east", label: "East millet" },
  { id: "orchard", label: "Orchard block" },
  { id: "lower", label: "Lower field" },
];

export const plotWidth = 24;
export const plotDepth = 18;

export function fieldLayout(plots: FieldPlot[]): FieldLayout[] {
  return plots.map((plot, index) => ({
    ...plot,
    index,
    x: (index % 2 ? 1 : -1) * 14,
    z: Math.floor(index / 2) * 23 - 11.5,
  }));
}
