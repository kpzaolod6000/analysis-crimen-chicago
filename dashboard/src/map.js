/**
 * Community area maps (Sprint 7 · Paso 4 + Paso 7 bubble a pedido del
 * usuario): DOS vistas del mismo dato, con toggle.
 *
 * - "choropleth": el polígono de cada área coloreado por volumen (√) —
 *   lectura territorial/densa.
 * - "bubble": círculos en los centroides (d3.geoCentroid, runtime) con
 *   radio √ y relleno magma — lectura puntual del volumen; los anillos de
 *   hotspots viven AQUÍ (capa puntual con capa puntual), no en el
 *   coroplético.
 *
 * Geometry: the 77 official community areas (GeoJSON from the Chicago
 * Data Portal, dataset igwz-8jzy — committed in public/). Counts:
 * /api/crimes/by-community-area (filtrados).
 *
 * The dashboard never talks to PostgreSQL: geometry is a static asset,
 * counts come from the API.
 */

import * as d3 from "d3";
import { getByCommunityArea } from "./api.js";
import areasUrl from "/community_areas.geojson?url";

const NO_CRIME_FILL = "#262a35";

function renderEmpty(container, message) {
  container.html("");
  container.append("div").attr("class", "chart-note").text(message);
}

// ── estado del módulo ────────────────────────────────────────────────────
let projection = null;
let mapSvg = null;
let mapTooltip = null;
let mapWidth = 0;
let mapMode = "choropleth";       // "choropleth" | "bubble"
let lastFilters = {};             // para re-render desde el toggle
let lastByArea = null;            // Map área → row (para el overlay)
let onModeChange = null;          // main.js lo setea (dibuja los anillos)

export function setOnModeChange(fn) {
  onModeChange = fn;
}

/**
 * Overlay de hotspots OBSERVADOS (Sprint 7 · Paso 6, ajuste Paso 7): con
 * la técnica bubble map — círculos RELLENOS en los centroides (radio √
 * del volumen, fill rojo translúcido que comunica el área del cluster) +
 * tooltip nativo <title>. Sin anillos punteados (feedback del usuario:
 * sin relleno no se lee el volumen). Solo en modo bubble; sin mapa
 * renderizado, no-op.
 */
export function renderHotspotMarkers(clusters) {
  if (!mapSvg || !projection || !clusters?.length) return;
  if (mapMode !== "bubble") return;
  const maxPoints = d3.max(clusters, (c) => c.n_points);
  const rScale = d3.scaleSqrt().domain([1, maxPoints]).range([4, 14]);
  const color = d3
    .scaleSequential(d3.interpolateReds)
    .domain([1, maxPoints]);

  mapSvg
    .selectAll("g.hotspots")
    .data([clusters])
    .join("g")
    .attr("class", "hotspots")
    .selectAll("circle.hotspot-marker")
    .data((d) => d)
    .join("circle")
    .attr("class", "hotspot-marker")
    .attr("transform", (c) => {
      const [x, y] = projection([c.centroid_lon, c.centroid_lat]);
      return `translate(${x},${y})`;
    })
    .attr("r", (c) => rScale(c.n_points))
    .attr("fill", (c) => color(c.n_points))
    .attr("fill-opacity", 0.45)
    .attr("stroke", "#1a1d27")
    .attr("stroke-width", 1)
    // tooltip custom INSTANTÁNEO (mismo mecanismo que las demás charts);
    // el <title> nativo queda como fallback
    .on("pointerenter", (event, c) =>
      mapTooltip
        .style("opacity", 1)
        .style("left", `${event.offsetX}px`)
        .style("top", `${event.offsetY - 10}px`)
        .html(
          `<strong>Hotspot #${c.cluster_label}</strong><br>` +
            `${d3.format(",")(c.n_points)} points<br>` +
            `centroid: ${c.centroid_lat.toFixed(4)}, ${c.centroid_lon.toFixed(4)}`
        )
    )
    .on("pointermove", (event, c) =>
      mapTooltip
        .style("opacity", 1)
        .style("left", `${event.offsetX}px`)
        .style("top", `${event.offsetY - 10}px`)
        .html(
          `<strong>Hotspot #${c.cluster_label}</strong><br>` +
            `${d3.format(",")(c.n_points)} points<br>` +
            `centroid: ${c.centroid_lat.toFixed(4)}, ${c.centroid_lon.toFixed(4)}`
        )
    )
    .on("pointerleave", () => mapTooltip.style("opacity", 0))
    .append("title")
    .text(
      (c) =>
        `Hotspot #${c.cluster_label} · ${c.n_points} points\n` +
        `centroid: ${c.centroid_lat.toFixed(4)}, ${c.centroid_lon.toFixed(4)}`
    );

  drawHotspotLegend(maxPoints);
}

// ── barra vertical de intensidad (lado derecho del mapa) ────────────────
// gradient Reds + ticks (0..maxPoints) + hover sobre la barra con su
// propio tooltip ("≈ N points" a esa altura). Vive en el espacio vacío
// del lago (lado derecho), sin expandir el viewBox.
function drawHotspotLegend(maxPoints) {
  if (!mapSvg || !mapTooltip) return;
  const LEG_W = 14;
  const LEG_H = 180;
  const LEG_X = mapWidth - 64;
  const LEG_Y = 40;

  const valueAt = d3
    .scaleLinear()
    .domain([0, maxPoints])
    .range([LEG_Y + LEG_H, LEG_Y]); // y → points (arriba = más)
  const color = d3
    .scaleSequential(d3.interpolateReds)
    .domain([0, maxPoints]);

  const defs = mapSvg.selectAll("defs.hotspot-legend").data([1]).join("defs")
    .attr("class", "hotspot-legend");
  const gradient = defs.append("linearGradient")
    .attr("id", "hotspot-legend-grad")
    .attr("x1", "0").attr("x2", "0").attr("y1", "1").attr("y2", "0");
  gradient
    .selectAll("stop")
    .data(d3.range(11))
    .join("stop")
    .attr("offset", (_d, i) => `${i * 10}%`)
    .attr("stop-color", (_d, i) => color((i / 10) * maxPoints));

  mapSvg
    .selectAll("rect.hotspot-legend-bar")
    .data([1])
    .join("rect")
    .attr("class", "hotspot-legend-bar")
    .attr("x", LEG_X)
    .attr("y", LEG_Y)
    .attr("width", LEG_W)
    .attr("height", LEG_H)
    .attr("rx", 3)
    .attr("fill", "url(#hotspot-legend-grad)");
    // sin tooltip en la barra (feedback del usuario): los tooltips viven
    // en cada hotspot (nativo <title> del círculo de arriba)

  mapSvg
    .append("g")
    .attr("class", "hotspot-legend-axis")
    .attr("transform", `translate(${LEG_X + LEG_W + 4},0)`)
    .call(d3.axisRight(valueAt).ticks(4).tickFormat(d3.format(",")));
}

async function loadMapData(filters) {
  const [ranking, geo] = await Promise.all([
    getByCommunityArea(100, filters),
    d3.json(areasUrl),
  ]);
  return { ranking, geo };
}

function setupBase(container, geo) {
  const node = container.node();
  const width = node.clientWidth || 1000;
  const height = 640;

  container.html("");
  const svg = container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("width", "100%");
  mapSvg = svg;
  mapWidth = width;

  const proj = d3
    .geoMercator()
    .fitExtent([[10, 10], [width - 10, height - 10]], geo);
  projection = proj; // publicado para el overlay (re-escrito en cada render)

  const tooltip = container
    .append("div")
    .attr("class", "chart-tooltip")
    .style("opacity", 0);
  mapTooltip = tooltip;

  return { svg, proj, tooltip, width, height };
}

function bindAreaHover(selection, tooltip, infoHtml, featureOf = (d) => d) {
  // classed() y no .attr("class", ...): el attr REEMPLAZA toda la lista
  // de clases; classed() la preserva.
  // featureOf: los wrappers de burbuja llevan el feature EN .feature
  // (leer d.properties directo revienta con TypeError silencioso).
  selection
    .on("pointermove", (event, d) => {
      const feature = featureOf(d);
      const areaNum = Number(feature.properties.area_numbe);
      const row = lastByArea.get(areaNum);
      const name = row?.community_area_name || feature.properties.community;
      tooltip
        .style("opacity", 1)
        .style("left", `${event.offsetX}px`)
        .style("top", `${event.offsetY - 10}px`)
        .html(`<strong>${areaNum} · ${name}</strong><br>${infoHtml(row)}`);
    })
    .on("pointerleave", () => tooltip.style("opacity", 0))
    .on("pointerover", (event) =>
      d3.select(event.currentTarget).classed("area-hover", true)
    )
    .on("pointerout", (event) =>
      d3.select(event.currentTarget).classed("area-hover", false)
    );
}

function drawToolbar(container) {
  const MODES = [
    ["choropleth", "Choropleth"],
    ["bubble", "Bubble map"],
  ];
  container
    .append("div")
    .attr("class", "map-toolbar")
    .selectAll("button")
    .data(MODES)
    .join("button")
    .attr("class", (d) => `map-mode-btn${d[0] === mapMode ? " active" : ""}`)
    .text((d) => d[1])
    .on("click", (_event, [mode]) => {
      if (mode === mapMode) return;
      mapMode = mode;
      // self-contained: mismo filters, modo nuevo; los anillos se
      // redibujan vía el callback (renderHotspots en main.js)
      renderMap(lastFilters).then(() => onModeChange?.());
    });
}

export async function renderMap(filters = {}) {
  lastFilters = filters;
  const container = d3.select("#map-chart");
  let ranking, geo;
  try {
    ({ ranking, geo } = await loadMapData(filters));
  } catch (err) {
    renderEmpty(container, `API down or GeoJSON missing: ${err.message}`);
    return;
  }

  lastByArea = new Map(ranking.map((r) => [r.community_area, r]));
  const maxCount = d3.max(ranking, (r) => r.crime_count) || 1;
  // info HTML de hover COMPARTIDA por outlines y burbujas (bubble mode)
  const bubbleInfoHtml = (row) =>
    row
      ? `${d3.format(",")(row.crime_count)} crimes · ${row.share_pct}% · rank ${row.crime_rank}`
      : "no crimes recorded in this window";

  const { svg, proj, tooltip } = setupBase(container, geo);
  drawToolbar(container);
  if (mapMode === "bubble") {
    // ── bubble map: SOLO hotspots (feedback del usuario: las burbujas
    // por área perdían relevancia; los hotspots son el mensaje) ──
    // 1) esqueleto de referencia (77 áreas) con hover/tooltip de área
    const outlines = svg
      .selectAll("path.area-outline")
      .data(geo.features)
      .join("path")
      .attr("class", "area-outline")
      .attr("d", d3.geoPath(proj));
    bindAreaHover(outlines, tooltip, bubbleInfoHtml);
    // 2) los círculos de hotspots los dibuja renderHotspotMarkers
    //    (llamado desde hotspots.js tras el render del mapa)
  } else {
    // ── choropleth: área entera coloreada por volumen (√) ──
    const colorNorm = d3.scaleSqrt().domain([0, maxCount]).range([0.12, 1]);

    const shapes = svg
      .selectAll("path")
      .data(geo.features)
      .join("path")
      .attr("class", "area-shape")
      .attr("d", d3.geoPath(proj))
      .attr("fill", (feature) => {
        const row = lastByArea.get(Number(feature.properties.area_numbe));
        if (!row) return NO_CRIME_FILL;
        return d3.interpolateMagma(colorNorm(row.crime_count));
      });

    bindAreaHover(shapes, tooltip, (row) =>
      row
        ? `${d3.format(",")(row.crime_count)} crimes · ${row.share_pct}% · rank ${row.crime_rank}`
        : "no crimes recorded in this window"
    );
  }
}
