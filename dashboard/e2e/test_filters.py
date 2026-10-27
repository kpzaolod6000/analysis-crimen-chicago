"""E2E: filter bar drives the whole dashboard (Sprint 7 Paso 5).

Flow: select Type=THEFT -> KPI crimes changes to the THEFT count; Clear
filters -> back to the full window. Data-dependent (dev stack).
Assertions scoped to kpi-grid: the trends note ALSO prints the filtered
count ("Only 1 month loaded (... 4,191 crimes)") and bare get_by_text
would hit strict mode with 2 matches.
"""

from playwright.sync_api import Page, expect

from e2e_config import BASE_URL


def crimes_value(page: Page):
    return page.get_by_test_id("kpi-card").first.locator(".kpi-value")


def test_filter_by_type_updates_kpis(page: Page):
    page.goto(BASE_URL)
    expect(crimes_value(page)).to_be_visible()

    page.get_by_test_id("filter-type").select_option("THEFT")
    expect(page.get_by_test_id("kpi-grid").get_by_text("4,191")).to_be_visible()

    page.get_by_role("button", name="Clear filters").click()
    expect(page.get_by_test_id("kpi-grid").get_by_text("19,642")).to_be_visible()
