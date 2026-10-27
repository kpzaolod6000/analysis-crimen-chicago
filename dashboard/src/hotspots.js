/**
 * Hotspots panel (Sprint 7 · Paso 6): the OBSERVED hotspots view.
 *
 * Reads /api/crimes/hotspots (latest DBSCAN run) and renders:
 *   1. run provenance header (eps / min_samples / clusters / noise)
 *   2. top-10 clusters table by volume
 *   3. ring markers over the map (renderHotspotMarkers from map.js)
 *
 * Without stored runs it shows a helpful message pointing to notebook 04
 * (Sprint 5) — the panel is data-driven, not mocked.
 */

import * as d3 from "d3";
import { getHotspots } from "./api.js";
import { renderHotspotMarkers } from "./map.js";

// token de secuencia (race de orden: un fetch lento no pisa al nuevo)
let renderSeq = 0;

export async function renderHotspots() {
  const seq = ++renderSeq;
  const panel = d3.select("#hotspots-panel");
  let data;
  try {
    data = await getHotspots();
  } catch (err) {
    if (seq !== renderSeq) return;
    const notFound = String(err.message).includes("404");
    panel
      .html("")
      .append("div")
      .attr("class", "chart-note")
      .text(
        notFound
          ? "No DBSCAN runs stored yet — run notebook 04 (Sprint 5 · Paso 5) to generate and persist one."
          : `API down: ${err.message}`
      );
    return;
  }
  if (seq !== renderSeq) return;  // resultado desactualizado: ignorar

  const { run, clusters } = data;
  panel.html("");

  panel
    .append("p")
    .attr("class", "run-info")
    .html(
      `Run <strong>#${run.run_key}</strong> · eps <strong>${run.eps} m</strong> · ` +
        `min_samples <strong>${run.min_samples}</strong> · ` +
        `${run.n_clusters} clusters · ` +
        `<span class="muted">${d3.format(",")(run.n_noise)} noise points</span>`
    );

  const top = clusters.slice(0, 10);
  const stats = panel
    .append("table")
    .attr("class", "hotspots-table");
  stats
    .append("thead")
    .append("tr")
    .selectAll("th")
    .data(["Cluster", "Points", "Centroid (lat, lon)"])
    .join("th")
    .text((d) => d);

  stats
    .append("tbody")
    .selectAll("tr")
    .data(top)
    .join("tr")
    .selectAll("td")
    .data((c) => [
      `#${c.cluster_label}`,
      d3.format(",")(c.n_points),
      `${c.centroid_lat.toFixed(4)}, ${c.centroid_lon.toFixed(4)}`,
    ])
    .join("td")
    .text((d) => d);

  // anillos sobre el mapa (si el mapa ya está renderizado)
  renderHotspotMarkers(clusters);
}
