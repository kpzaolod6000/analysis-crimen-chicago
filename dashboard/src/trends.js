/**
 * Monthly trends line chart (Sprint 7 Â· Paso 2).
 *
 * Consumes /api/crimes/trends (vw_monthly_crimes). Features:
 *   - SVG line + area with axes (month labels)
 *   - hover tooltip (circle marker + week details)
 *   - x-axis zoom via d3.zoom (useful with 2+ months; no-op with 1)
 *   - graceful degradation with < 2 months of data (explanatory message)
 */

import * as d3 from "d3";
import { getTrends } from "./api.js";

const MARGIN = { top: 16, right: 24, bottom: 34, left: 56 };

function fmtNumber(v) {
  return d3.format(",")(v);
}

function renderEmpty(container, message) {
  container.html("");
  container
    .append("div")
    .attr("class", "chart-note")
    .text(message);
}

export async function renderTrends(filters = {}) {
  const container = d3.select("#trends-chart");
  let trends;
  try {
    trends = await getTrends(filters);
  } catch (err) {
    renderEmpty(container, `API down: ${err.message}`);
    return;
  }

  if (trends.length < 2) {
    renderEmpty(
      container,
      trends.length === 1
        ? `Only 1 month loaded (${trends[0].month_name} ${trends[0].year}, ${fmtNumber(trends[0].crime_count)} crimes). Load the 1-year window (Sprint 2 Â· Paso 3) to draw the trend line.`
        : "No data in the warehouse."
    );
    return;
  }

  drawChart(container, trends);
}

function drawChart(container, trends) {
  container.html("");

  const node = container.node();
  const width = node.clientWidth || 900;
  const height = 320;
  const innerW = width - MARGIN.left - MARGIN.right;
  const innerH = height - MARGIN.top - MARGIN.bottom;

  const svg = container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("width", "100%")
    .attr("height", height);

  const g = svg
    .append("g")
    .attr("transform", `translate(${MARGIN.left},${MARGIN.top})`);

  const x = d3
    .scaleTime()
    .domain(d3.extent(trends, (d) => new Date(d.month_date)))
    .range([0, innerW]);
  const y = d3
    .scaleLinear()
    .domain([0, d3.max(trends, (d) => d.crime_count) * 1.05])
    .range([innerH, 0])
    .nice();

  // ejes
  g.append("g")
    .attr("transform", `translate(0,${innerH})`)
    .attr("class", "axis-x")
    .call(d3.axisBottom(x).tickFormat(d3.timeFormat("%b %Y")));
  g.append("g").attr("class", "axis-y").call(d3.axisLeft(y).ticks(6));

  const lineGen = d3
    .line()
    .x((d) => x(new Date(d.month_date)))
    .y((d) => y(d.crime_count))
    .curve(d3.curveMonotoneX);
  const areaGen = d3
    .area()
    .x((d) => x(new Date(d.month_date)))
    .y0(innerH)
    .y1((d) => y(d.crime_count))
    .curve(d3.curveMonotoneX);

  g.append("path")
    .datum(trends)
    .attr("class", "trend-area")
    .attr("d", areaGen);
  g.append("path")
    .datum(trends)
    .attr("class", "trend-line")
    .attr("d", lineGen);

  // tooltip (div flotante + marcador)
  const tooltip = container
    .append("div")
    .attr("class", "chart-tooltip")
    .style("opacity", 0);
  const marker = g.append("circle").attr("r", 5).attr("class", "trend-marker")
    .style("opacity", 0);

  svg
    .on("pointermove", (event) => {
      const [mx] = d3.pointer(event, g.node());
      const month = d3.bisector((d) => new Date(d.month_date)).center(
        trends,
        x.invert(mx)
      );
      const d = trends[month];
      if (!d) return;
      const cx = x(new Date(d.month_date));
      const cy = y(d.crime_count);
      marker.attr("cx", cx).attr("cy", cy).style("opacity", 1);
      tooltip
        .style("opacity", 1)
        .style("left", `${cx + MARGIN.left}px`)
        .style("top", `${cy}px`)
        .html(
          `<strong>${d.month_name} ${d.year}</strong><br>` +
            `${fmtNumber(d.crime_count)} crimes Â· ${d.arrest_count} arrests` +
            `<br>Arrest rate: ${d.arrest_rate_pct}%`
        );
    })
    .on("pointerleave", () => {
      tooltip.style("opacity", 0);
      marker.style("opacity", 0);
    });

  // zoom en el eje X (con 1 punto no-op; con 12 meses permite inspecciÃ³n)
  const zoom = d3
    .zoom()
    .scaleExtent([1, 8])
    .translateExtent([[0, 0], [innerW, innerH]])
    .extent([[0, 0], [innerW, innerH]])
    .on("zoom", (event) => {
      const xz = event.transform.rescaleX(x);
      g.select(".axis-x").call(d3.axisBottom(xz).tickFormat(d3.timeFormat("%b %Y")));
      g.select(".trend-line").attr("d",
        d3.line().x((d) => xz(new Date(d.month_date))).y((d) => y(d.crime_count)).curve(d3.curveMonotoneX)(trends));
      g.select(".trend-area").attr("d",
        d3.area().x((d) => xz(new Date(d.month_date))).y0(innerH).y1((d) => y(d.crime_count)).curve(d3.curveMonotoneX)(trends));
    });
  svg.call(zoom);
}
