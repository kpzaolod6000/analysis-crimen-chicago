"""E2E: day x hour heatmap (Sprint 7 Paso 3).

Full 7x24 grid = 168 rects (zero-filled semantics); with an empty month
filter the cells disappear and the note shows. Data-dependent.
"""

from playwright.sync_api import Page, expect

from e2e_config import BASE_URL


def test_heatmap_full_grid(page: Page):
    page.goto(BASE_URL)
    # celdas dentro de g.row (excluye el rect de la LEYENDA: 169 total)
    expect(
        page.get_by_test_id("heatmap-chart").locator("g.row rect")
    ).to_have_count(168)


def test_heatmap_reacts_to_month_filter(page: Page):
    page.goto(BASE_URL)
    page.get_by_test_id("filter-month").select_option("8")  # agosto: sin datos
    expect(page.get_by_test_id("heatmap-chart")).to_contain_text(
        "No data in the warehouse."
    )
