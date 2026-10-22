/**
 * Dashboard entry point (Sprint 7).
 *
 * Paso 1: KPI cards. Paso 2: trends. Paso 3: heatmap. Paso 4: map.
 * Paso 5: filter bar — every change re-renders the whole dashboard
 * with the active filters. Paso 6: hotspots panel (table + map rings).
 */

import { renderKpis } from "./kpis.js";
import { renderTrends } from "./trends.js";
import { renderHeatmap } from "./heatmap.js";
import { renderMap, setOnModeChange } from "./map.js";
import { renderFilters } from "./filters.js";
import { renderHotspots } from "./hotspots.js";

document.addEventListener("DOMContentLoaded", () => {
  const refresh = (filters) => {
    renderKpis(filters);
    renderTrends(filters);
    renderHeatmap(filters);
    // el mapa dibuja el svg que el panel usa para sus anillos: cadena
    renderMap(filters).then(() => renderHotspots()).catch(() => {});
  };

  // toggle choropleth/bubble: re-dibuja los anillos tras el re-render
  setOnModeChange(() => renderHotspots());

  renderFilters(refresh);
  refresh({});
});