/**
 * API client for the FastAPI backend (Sprint 6 endpoints).
 *
 * The dashboard NEVER connects to PostgreSQL directly (plan rule):
 * everything goes through this client against /api/*.
 *
 * Base URL: VITE_API_URL (defaults to the local dev server :8000).
 */

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function fetchJson(path) {
  const resp = await fetch(`${BASE_URL}${path}`);
  if (!resp.ok) {
    throw new Error(`API ${resp.status} en ${path}`);
  }
  return resp.json();
}

export const getCrimesSummary = () => fetchJson("/api/crimes/summary");
export const getTrends = () => fetchJson("/api/crimes/trends");
export const getByType = (limit = 20) =>
  fetchJson(`/api/crimes/by-type?limit=${limit}`);
export const getByCommunityArea = (limit = 100) =>
  fetchJson(`/api/crimes/by-community-area?limit=${limit}`);
export const getHotspots = (runKey = null) =>
  fetchJson(runKey ? `/api/crimes/hotspots?run_key=${runKey}` : "/api/crimes/hotspots");
export const getByHour = () => fetchJson("/api/crimes/by-hour");
export const getWeeklyReport = () => fetchJson("/api/reports/weekly");
