/**
 * Filter bar (Sprint 7 · Paso 5 parte 2).
 *
 * Four selects (primary_type / year / month / community_area) + Clear.
 * The lists of options come from the API itself (top types, years present
 * in the data, the 77 areas). Every change fires `onChange(filters)` and
 * main.js re-renders the whole dashboard.
 */

import * as d3 from "d3";
import { getByType, getByCommunityArea, getTrends } from "./api.js";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

// estado compartido (lo consume main.js)
export const currentFilters = {};

function fillSelect(sel, values, labelsFn = (v) => v) {
  const rows = [{ value: "", label: "All" }, ...values.map((v) => {
    if (typeof v === "object")
      return { value: v.v, label: labelsFn(v) }
    return { value: v, label: labelsFn(v) }
  })];
  sel.selectAll("option")
    .data(rows)
    .join("option")
    .attr("value", (d) => d.value)
    .text((d) => d.label);
}

export async function renderFilters(onChange) {
  const bar = d3.select("#filters-bar").html("");

  const typeSel = bar.append("label").html("Type ");
  const yearSel = bar.append("label").html("Year ");
  const monthSel = bar.append("label").html("Month ");
  const areaSel = bar.append("label").html("Area ");

  const typeSelect = typeSel.append("select").attr("id", "filter-type");
  const yearSelect = yearSel.append("select").attr("id", "filter-year");
  const monthSelect = monthSel.append("select").attr("id", "filter-month");
  const areaSelect = areaSel.append("select").attr("id", "filter-area");

  // opciones: llenar sin filtros (listas estables); best-effort — si la
  // API cae, la barra queda con "All" y el dashboard muestra su error
  try {
    const [types, areas, trends] = await Promise.all([
      getByType(100),
      getByCommunityArea(100),
      getTrends(),
    ]);
    console.log("areas:", areas);
    fillSelect(typeSelect, types.map((t) => t.primary_type));
    const years = [...new Set(trends.map((t) => t.year))].sort();
    fillSelect(yearSelect, years, (y) => `${y}`);
    fillSelect(monthSelect, d3.range(1, 13), (m) => MONTHS[m - 1]);
    fillSelect(
      areaSelect,
      areas.map((a) => ({ v: a.community_area, l: a.community_area_name })),
      (a) => `${a.v} · ${a.l}`
    );
  } catch {
    /* la barra sigue con All; el error lo muestran las charts */
  }

  const bindings = [
    [typeSelect, "primary_type"],
    [yearSelect, "year"],
    [monthSelect, "month"],
    [areaSelect, "community_area"],
  ];
  const readFilters = () => {
    for (const [sel, key] of bindings) {
      const v = sel.property("value");
      currentFilters[key] = v === "" ? null : v;
    }
    onChange({ ...currentFilters });
  };
  bindings.forEach(([sel]) => sel.on("change", readFilters));

  bar
    .append("button")
    .attr("class", "filter-clear")
    .text("Clear filters")
    .on("click", () => {
      bindings.forEach(([sel]) => sel.property("value", ""));
      readFilters();
    });
}
