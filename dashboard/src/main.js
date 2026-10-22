/**
 * Dashboard entry point (Sprint 7).
 *
 * Paso 1: KPI cards (consumes /api/crimes/summary).
 * The chart sections render in later pasos (placeholders in index.html).
 */

import { renderKpis } from "./kpis.js";

document.addEventListener("DOMContentLoaded", () => {
  renderKpis();
});
