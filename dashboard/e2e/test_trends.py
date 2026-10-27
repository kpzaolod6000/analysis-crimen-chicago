"""E2E: monthly trends chart (Sprint 7 Paso 2).

With the dev window (1 month) the chart degrades with an explanatory
note (no empty SVG); the API is down -> error note. Tooltip hover is
covered once 2+ months are loaded (skipped by design here).
"""

from playwright.sync_api import Page, expect

from e2e_config import BASE_URL


def test_trends_degrades_with_single_month(page: Page):
    page.goto(BASE_URL)
    expect(page.get_by_test_id("trends-chart")).to_contain_text(
        "Only 1 month loaded"
    )


def test_trends_no_empty_svg(page: Page):
    # la nota NO es un svg vacío: no existe <svg> mientras haya <2 meses
    page.goto(BASE_URL)
    expect(page.get_by_test_id("trends-chart").locator("svg")).to_have_count(0)
