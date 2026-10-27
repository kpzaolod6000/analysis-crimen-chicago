"""E2E: hotspots panel (Sprint 7 Paso 6).

Data-driven: with stored runs shows the provenance header + top-10
table; without runs shows the "run notebook 04" note. The test accepts
either state (the dev DB has runs after notebook 04).
"""

from playwright.sync_api import Page, expect

from e2e_config import BASE_URL


def test_hotspots_panel_renders_either_state(page: Page):
    page.goto(BASE_URL)
    panel = page.get_by_test_id("hotspots-panel")
    with_runs = panel.locator(".hotspots-table")
    without_runs = panel.locator(".chart-note")
    expect(with_runs.first.or_(without_runs.first)).to_be_visible()


def test_hotspots_table_top10(page: Page):
    page.goto(BASE_URL)
    rows = page.get_by_test_id("hotspots-panel").locator("tbody tr")
    expect(rows).to_have_count(10)
