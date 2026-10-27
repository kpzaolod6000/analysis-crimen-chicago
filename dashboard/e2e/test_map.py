"""E2E: community area map (Sprint 7 Paso 4 + Paso 7 toggle).

Choropleth mode renders the 77 area paths; the toolbar switches to
bubble (hotspots-only) and back; hover shows a tooltip.
"""

from playwright.sync_api import Page, expect

from e2e_config import BASE_URL


def test_map_renders_77_areas(page: Page):
    page.goto(BASE_URL)
    expect(
        page.get_by_test_id("map-chart").locator("path.area-shape")
    ).to_have_count(77)


def test_map_toolbar_switches_to_bubble(page: Page):
    page.goto(BASE_URL)
    page.get_by_role("button", name="Bubble map").click()
    # en bubble: el esqueleto sigue (77 outlines) y los hotspots aparecen
    # (el eje de la leyenda agrega UN path extra: scope a .area-outline)
    expect(
        page.get_by_test_id("map-chart").locator("path.area-outline")
    ).to_have_count(77)
    hotspots = page.get_by_test_id("map-chart").locator(".hotspot-marker")
    expect(hotspots.first).to_be_visible()


def test_map_hover_shows_tooltip(page: Page):
    page.goto(BASE_URL)
    page.get_by_test_id("map-chart").locator("path").first.hover()
    expect(page.get_by_test_id("map-chart").locator(".chart-tooltip")).to_be_visible()
