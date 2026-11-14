import type { Farm } from "../services/apiClient";

export function farmOptionLabel(farm: Farm, includeName = true) {
  const crops = [...new Set(farm.plots.map((plot) => plot.cropCanonicalName))].join(", ");
  return [
    includeName ? farm.name : "",
    crops || "No plots",
    `${farm.location.latitude.toFixed(3)}, ${farm.location.longitude.toFixed(3)}`,
    includeName ? farm.farmId.slice(0, 6) : "",
  ].filter(Boolean).join(" · ");
}
