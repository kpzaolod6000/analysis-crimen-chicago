/**
 * KPI cards over /api/crimes/summary (Sprint 7 · Paso 1).
 */

import * as d3 from "d3";
import { getCrimesSummary } from "./api.js";

export async function renderKpis() {
  try {
    const summary = await getCrimesSummary();
    const cards = [
      { value: d3.format(",")(summary.crime_count), label: "Crimes", sub: `${summary.first_crime_date} → ${summary.last_crime_date}` },
      { value: `${summary.arrest_rate_pct}%`, label: "Arrest rate", sub: `${d3.format(",")(summary.arrest_count)} arrests` },
      { value: d3.format(",")(summary.distinct_crime_types), label: "Crime types", sub: "distinct primary types" },
      { value: d3.format(",")(summary.distinct_community_areas), label: "Community areas", sub: "with reported crime" },
    ];

    const container = d3.select("#kpis").html("");
    const sel = container
      .selectAll(".kpi-card")
      .data(cards)
      .join("div")
      .attr("class", "kpi-card");
    sel.append("div").attr("class", "kpi-value").text((d) => d.value);
    sel.append("div").attr("class", "kpi-label").text((d) => d.label);
    sel.append("div").attr("class", "kpi-sub").text((d) => d.sub || "");
  } catch (err) {
    d3.select("#kpis")
      .html(`<div class="api-error">API down: ${err.message}</div>`);
  }
}
