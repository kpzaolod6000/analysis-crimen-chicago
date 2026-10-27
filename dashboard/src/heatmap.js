/**
 * Day x hour heatmap (Sprint 7 Â· Paso 3).
 *
 * Consumes /api/crimes/by-hour (vw_day_hour). 7x24 cell grid (ISO days
 * Monday..Sunday, hours 0..23), sequential color scale, hover tooltip
 * per cell. Zero-filled: cells without data render at the scale's floor
 * (real zeros, same as the SQL view semantics).
 */

import * as d3 from "d3";
import { getByHour } from "./api.js";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const CELL = 26;

function renderEmpty(container, message) {
  container.html("");
  container.append("div").attr("class", "chart-note").text(message);
}

// token de secuencia: si un render más nuevo arrancó, el resultado viejo
// (más lento) NO debe pisar al nuevo (race de orden de fetches)
let renderSeq = 0;

export async function renderHeatmap(filters = {}) {
  const seq = ++renderSeq;
  const container = d3.select("#heatmap-chart");
  let cells;
  try {
    cells = await getByHour(filters);
  } catch (err) {
    if (seq === renderSeq) renderEmpty(container, `API down: ${err.message}`);
    return;
  }
  if (seq !== renderSeq) return;  // resultado desactualizado: ignorar
  if (!cells.length) {
    renderEmpty(container, "No data in the warehouse.");
    return;
  }

  // matriz completa 7x24 (0 donde no hay datos)
  const matrix = d3.range(7).map(() => d3.range(24).map(() => 0));
  for (const c of cells) {
    console.log("heatmap cell:", c);
    matrix[c.day_of_week - 1][c.hour] = c.crime_count;
  }
  console.log("heatmap matrix:", matrix);
  const dayNames = new Map(cells.map((c) => [c.day_of_week - 1, c.day_name]));

  const marginLeft = 48;
  const legendW = 70;
  const width = marginLeft + 24 * CELL + legendW;
  const height = 7 * CELL + 30;

  container.html("");
  const svg = container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("width", "100%");

  const maxCount = d3.max(cells, (c) => c.crime_count);
  const color = d3
    .scaleSequential(d3.interpolateMagma)
    .domain([0, maxCount]);

  const row = svg
    .selectAll("g.row")
    .data(matrix)
    .join("g")
    .attr("class", "row")
    .attr("transform", (_d, i) => `translate(${marginLeft},${i * CELL})`);

  const tooltip = container
    .append("div")
    .attr("class", "chart-tooltip")
    .style("opacity", 0);

  // datos planos por rect: {day, hour, count} â€” el datum de la fila es el
  // ARRAY de conteos (no su Ã­ndice): binding plano evita el "undefined"
  row
    .selectAll("rect")
    .data((rowCounts, dayIdx) =>
      rowCounts.map((count, hour) => ({ day: dayIdx, hour, count }))
    )
    .join("rect")
    .attr("x", (d) => d.hour * CELL)
    .attr("width", CELL - 2)
    .attr("height", CELL - 2)
    .attr("rx", 3)
    .attr("fill", (d) => color(d.count))
    .on("pointermove", (event, d) => {
      const dayName = dayNames.get(d.day) || DAYS[d.day];
      tooltip
        .style("opacity", 1)
        .style("left", `${event.offsetX}px`)
        .style("top", `${event.offsetY - 10}px`)
        .html(
          `<strong>${dayName} ${d.hour}h</strong><br>` +
            `${d.count} crime${d.count === 1 ? "" : "s"}`
        );
    })
    .on("pointerleave", () => tooltip.style("opacity", 0));

  // labels: dÃ­as a la izquierda, horas debajo
  svg
    .selectAll("text.day-label")
    .data(DAYS)
    .join("text")
    .attr("class", "day-label")
    .attr("x", marginLeft - 8)
    .attr("y", (_d, i) => i * CELL + CELL / 2 + 4)
    .attr("text-anchor", "end")
    .text((d) => d);

  svg
    .selectAll("text.hour-label")
    .data(d3.range(24))
    .join("text")
    .attr("class", "hour-label")
    .attr("x", (h) => marginLeft + h * CELL + (CELL - 2) / 2)
    .attr("y", 7 * CELL + 16)
    .attr("text-anchor", "middle")
    .text((h) => (h % 3 === 0 ? h : ""));

  // leyenda de intensidad (colorbar vertical a la derecha del grid)
  const legendX = marginLeft + 24 * CELL + 20;
  const legendH = 7 * CELL;
  const legendY = 0;
  const gradient = svg
    .append("defs")
    .append("linearGradient")
    .attr("id", "heatmap-legend-gradient")
    .attr("x1", "0")
    .attr("x2", "0")
    .attr("y1", "1")
    .attr("y2", "0");
  gradient
    .selectAll("stop")
    .data(d3.range(11))
    .join("stop")
    .attr("offset", (_d, i) => `${i * 10}%`)
    .attr("stop-color", (_d, i) => color((i / 10) * maxCount));

  svg
    .append("rect")
    .attr("x", legendX)
    .attr("y", legendY)
    .attr("width", 14)
    .attr("height", legendH)
    .attr("rx", 3)
    .attr("fill", "url(#heatmap-legend-gradient)");

  const legendScale = d3
    .scaleLinear()
    .domain([0, maxCount])
    .range([legendY + legendH, legendY]);
  svg
    .append("g")
    .attr("transform", `translate(${legendX + 16},0)`)
    .attr("class", "axis-y")
    .call(d3.axisRight(legendScale).ticks(4).tickFormat(d3.format(",")));
}
