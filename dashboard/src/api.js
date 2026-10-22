/**
 * API client for the FastAPI backend (Sprint 6 endpoints).
 *
 * The dashboard NEVER connects to PostgreSQL directly (plan rule):
 * everything goes through this client against /api/*.
 *
 * Base URL: VITE_API_URL (defaults to the local dev server :8000).
 * Filters (Sprint 7 Paso 5): {primary_type, year, month, community_area}
 * with null/undefined values omitted from the query string.
 */

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function buildQuery(filters = {}) {
  const pairs = Object.entries(filters).filter(([, v]) => v != null && v !== "");
  if (!pairs.length) return "";
  const qs = new URLSearchParams(Object.fromEntries(pairs.map(([k, v]) => [k, v])));
  return `?${qs.toString()}`;
}

async function fetchJson(path) {
  const resp = await fetch(`${BASE_URL}${path}`);
  if (!resp.ok) {
    throw new Error(`API ${resp.status} en ${path}`);
  }
  return resp.json();
}

export const getCrimesSummary = (filters = {}) =>
  fetchJson(`/api/crimes/summary${buildQuery(filters)}`);
export const getTrends = (filters = {}) =>
  fetchJson(`/api/crimes/trends${buildQuery(filters)}`);
export const getByType = (limit = 20, filters = {}) =>
  fetchJson(`/api/crimes/by-type?limit=${limit}${buildQuery(filters).replace("?", "&")}`);
export const getByCommunityArea = (limit = 100, filters = {}) =>
  fetchJson(`/api/crimes/by-community-area?limit=${limit}${buildQuery(filters).replace("?", "&")}`);
export const getHotspots = (runKey = null) =>
  fetchJson(runKey ? `/api/crimes/hotspots?run_key=${runKey}` : "/api/crimes/hotspots");
export const getByHour = (filters = {}) =>
  fetchJson(`/api/crimes/by-hour${buildQuery(filters)}`);
export const getWeeklyReport = () => fetchJson("/api/reports/weekly");
