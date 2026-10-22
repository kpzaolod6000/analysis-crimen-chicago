"""E2E smoke test â€” Sprint 8 Â· Paso 1 (ejercicio dÃ­a-1 de testing.md Â§3.1).

Valida el ciclo completo de Playwright: abrir el dashboard servido por
Vite y encontrar el tÃ­tulo. Requiere el stack local corriendo:
  1. DB de pruebas (opcional para este smoke: la API responde /health
     igual; los datos reales hacen falta en los demÃ¡s specs)
  2. API:      .\.venv\Scripts\python.exe -m uvicorn api.app.main:app --port 8000
  3. Dashboard (dashboard/): npm run dev

Run:  pytest dashboard/e2e -v          (headless, default)
      pytest dashboard/e2e -v --headed (viendo el navegador)

Contra otra base URL: set E2E_BASE_URL=http://... (ej. vite preview).
"""

import os
from playwright.sync_api import Page, expect

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:5173")


def test_dashboard_title_visible(page: Page):
    page.goto(BASE_URL)
    expect(
        page.get_by_role("heading", name="Chicago Crimes Analytics")
    ).to_be_visible()

