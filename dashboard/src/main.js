/**
 * Dashboard entry point (Sprint 7).
 *
 * Paso 1: KPI cards (/api/crimes/summary).
 * Paso 2: monthly trends line chart (/api/crimes/trends).
 * Paso 3: day x hour heatmap (/api/crimes/by-hour).
 */

import { renderKpis } from "./kpis.js";
import { renderTrends } from "./trends.js";
import { renderHeatmap } from "./heatmap.js";
import { renderMap } from "./map.js";

document.addEventListener("DOMContentLoaded", () => {
  renderKpis();
  renderTrends();
  renderHeatmap();
  renderMap();
});
