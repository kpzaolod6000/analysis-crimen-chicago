/**
 * Dashboard entry point (Sprint 7).
 *
 * Paso 1: KPI cards. Paso 2: trends. Paso 3: heatmap. Paso 4: map.
 * Paso 5: filter bar — every change re-renders the whole dashboard
 * with the active filters.
 */

import { renderKpis } from "./kpis.js";
import { renderTrends } from "./trends.js";
import { renderHeatmap } from "./heatmap.js";
import { renderMap } from "./map.js";
import { renderFilters } from "./filters.js";

document.addEventListener("DOMContentLoaded", () => {
  const refresh = (filters) => {
    renderKpis(filters);
    renderTrends(filters);
    renderHeatmap(filters);
    renderMap(filters);
  };

  renderFilters(refresh);
  refresh({});
});