/**
 * Choropleth map by community area (Sprint 7 Â· Paso 4).
 *
 * Geometry: the 77 official community areas (GeoJSON from the Chicago
 * Data Portal, dataset igwz-8jzy â€” committed in public/). Counts:
 * /api/crimes/by-community-area. Color: sqrt scale (counts are heavily
 * skewed â€” linear would make most areas look zero).
 *
 * The dashboard never talks to PostgreSQL: geometry is a static asset,
 * counts come from the API.
 */

import * as d3 from "d3";
import { getByCommunityArea } from "./api.js";
import areasUrl from "/community_areas.geojson?url";

function renderEmpty(container, message) {
  container.html("");
  container.append("div").attr("class", "chart-note").text(message);
}

export async function renderMap(filters = {}) {
  const container = d3.select("#map-chart");
  let ranking, geo;
  try {
    [ranking, geo] = await Promise.all([
      getByCommunityArea(100, filters),
      d3.json(areasUrl),
    ]);
  } catch (err) {
    renderEmpty(container, `API down or GeoJSON missing: ${err.message}`);
    return;
  }

  const byArea = new Map(ranking.map((r) => [r.community_area, r]));
  console.log("map ranking:", ranking);
  console.log("map geo:", byArea);
  const maxCount = d3.max(ranking, (r) => r.crime_count) || 1;
  // sqrt: el count va 1..927 â€” lineal dejarÃ­a 70 Ã¡reas como "cero"
  const color = d3.scaleSqrt().domain([0, maxCount]).range([0.12, 1]);

  const node = container.node();
  const width = node.clientWidth || 1000;
  const height = 640;

  const projection = d3
    .geoMercator()
    .fitExtent([[10, 10], [width - 10, height - 10]], geo);
  const pathGen = d3.geoPath(projection);

  container.html("");
  const svg = container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("width", "100%");

  const tooltip = container
    .append("div")
    .attr("class", "chart-tooltip")
    .style("opacity", 0);

  svg
    .selectAll("path")
    .data(geo.features)
    .join("path")
    .attr("class", "area-shape")
    .attr("d", pathGen)
    .on("pointermove", (event, feature) => {
      const areaNum = Number(feature.properties.area_numbe);
      const row = byArea.get(areaNum);
      const name = row?.community_area_name || feature.properties.community;
      tooltip
        .style("opacity", 1)
        .style("left", `${event.offsetX}px`)
        .style("top", `${event.offsetY - 10}px`)
        .html(
          `<strong>${areaNum} Â· ${name}</strong><br>` +
            (row
              ? `${d3.format(",")(row.crime_count)} crimes Â· ${row.share_pct}% Â· rank ${row.crime_rank}`
              : "no crimes recorded in this window")
        );
    })
    .on("pointerleave", () => tooltip.style("opacity", 0))
    .on("pointerover", (event) =>
      d3.select(event.currentTarget).attr("class", "area-shape area-hover")
    )
    .on("pointerout", (event) =>
      d3.select(event.currentTarget).attr("class", "area-shape")
    )
    .attr("fill", (feature) => {
      const row = byArea.get(Number(feature.properties.area_numbe));
      if (!row) return "#262a35"; // Ã¡rea sin crÃ­menes en la ventana
      return d3.interpolateMagma(color(row.crime_count));
    });
}
