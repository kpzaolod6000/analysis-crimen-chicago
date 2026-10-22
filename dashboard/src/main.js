/**
 * Dashboard entry point (Sprint 7).
 *
 * Paso 1: KPI cards (/api/crimes/summary).
 * Paso 2: monthly trends line chart (/api/crimes/trends).
 */

import { renderKpis } from "./kpis.js";
import { renderTrends } from "./trends.js";

document.addEventListener("DOMContentLoaded", () => {
  renderKpis();
  renderTrends();
});
