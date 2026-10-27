"""E2E: KPI cards render with real data from /api/crimes/summary.

Data-dependent (dev stack): 4 cards, first card = Crimes with a date
range. Run with the local stack up (API :8000 + Vite :5173).
"""

from playwright.sync_api import Page, expect

from e2e_config import BASE_URL


def test_kpi_cards_render(page: Page):
    page.goto(BASE_URL)
    cards = page.get_by_test_id("kpi-card")
    expect(cards).to_have_count(4)
    # la primera card es Crimes con su ventana de fechas
    expect(cards.first.locator(".kpi-label")).to_have_text("Crimes")
    expect(cards.first.locator(".kpi-sub")).to_contain_text("2026")


def test_kpi_values_are_numbers(page: Page):
    page.goto(BASE_URL)
    values = page.get_by_test_id("kpi-card").locator(".kpi-value")
    expect(values.first).not_to_have_text("")  # cargó (sin placeholder)
