"""Unit tests for the Socrata SoQL helper (no network: fake fetch)."""

import json
import urllib.request
from urllib.error import HTTPError

import pytest
from ingestion import socrata


class TestBuildParams:
    def test_includes_where_order_limit_offset(self):
        params = socrata.build_params(where="x = '1'", limit=10, offset=20)
        assert params == {"$where": "x = '1'", "$order": "id", "$limit": "10", "$offset": "20"}

    def test_defaults_to_deterministic_order(self):
        assert socrata.build_params() == {"$order": "id"}

    def test_select_and_app_token(self):
        params = socrata.build_params(select="id,date", app_token="tok123")
        assert params["$select"] == "id,date"
        assert params["$$app_token"] == "tok123"

    @pytest.mark.parametrize("bad", [0, -1, 50001])
    def test_rejects_limit_out_of_range(self, bad):
        with pytest.raises(ValueError):
            socrata.build_params(limit=bad)

    def test_rejects_negative_offset(self):
        with pytest.raises(ValueError):
            socrata.build_params(offset=-5)


class TestDateWindowWhere:
    def test_half_open_range_format(self):
        where = socrata.date_window_where("2026-01-01T00:00:00", "2026-02-01T00:00:00")
        assert where == "date >= '2026-01-01T00:00:00' AND date < '2026-02-01T00:00:00'"

    def test_rejects_start_not_before_end(self):
        with pytest.raises(ValueError):
            socrata.date_window_where("2026-02-01", "2026-01-01")

    def test_rejects_unparseable_date(self):
        with pytest.raises(ValueError):
            socrata.date_window_where("not-a-date", "2026-01-01")


class TestPaginate:
    def _fake_fetch(self, pages):
        calls = []

        def fetch(dataset_id, params):
            calls.append(params)
            target = params["$offset"]
            for page_offsets, records in pages:
                if page_offsets == target and not records["consumed"]:
                    records["consumed"] = True
                    return records["data"]
            return []

        return fetch, calls

    def test_yields_pages_and_stops_on_partial_page(self):
        pages = [
            ("0", {"data": [{"id": str(i)} for i in range(50)], "consumed": False}),
            ("50", {"data": [{"id": str(i)} for i in range(20)], "consumed": False}),
        ]
        fetch, calls = self._fake_fetch(pages)
        got = list(socrata.paginate("dset", fetch, page_size=50))
        assert len(got) == 2
        assert len(got[0]) == 50
        assert len(got[1]) == 20
        # deterministic paging: ORDER BY id with increasing offsets
        assert [c["$offset"] for c in calls] == ["0", "50"]
        assert all(c["$order"] == "id" for c in calls)

    def test_no_deep_offset_without_date_filter_flag_needed(self):
        # pagination always sends $order=id (deterministic) per skill rules
        fetch, calls = self._fake_fetch([("0", {"data": [], "consumed": False})])
        list(socrata.paginate("dset", fetch, page_size=10))
        assert calls[0]["$order"] == "id"

    def test_respects_max_pages(self):
        page = {"data": [{"id": str(i)} for i in range(10)], "consumed": False}
        fetch, _calls = self._fake_fetch([("0", page)])
        got = list(socrata.paginate("dset", fetch, page_size=10, max_pages=1))
        assert len(got) == 1

    def test_rejects_bad_page_size(self):
        with pytest.raises(ValueError):
            list(socrata.paginate("dset", lambda d, p: [], page_size=0))
        with pytest.raises(ValueError):
            list(socrata.paginate("dset", lambda d, p: [], page_size=60000))


class TestFetchPage:
    def test_parses_json_list(self, monkeypatch):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps([{"id": "1"}]).encode("utf-8")

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["headers"] = dict(req.header_items())
            return FakeResponse()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        records = socrata.fetch_page("ijzp-q8t2", {"$limit": "1"})
        assert records == [{"id": "1"}]
        assert "resource/ijzp-q8t2.json" in captured["url"]
        assert "%24limit=1" in captured["url"]  # urlencode escapa "$" como %24
        assert captured["headers"]["User-agent"].startswith("crimen-chicago/")

    def test_raises_on_http_error(self, monkeypatch):
        def fake_urlopen(req, timeout=None):
            raise HTTPError(req.full_url, 403, "Forbidden", None, None)

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(HTTPError):
            socrata.fetch_page("ijzp-q8t2", {})

    def test_raises_on_non_list_response(self, monkeypatch):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps({"error": True}).encode("utf-8")

        monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: FakeResponse())
        with pytest.raises(TypeError, match="unexpected Socrata response"):
            socrata.fetch_page("ijzp-q8t2", {})


class TestMonthWindows:
    def test_single_exact_month(self):
        got = socrata.month_windows("2026-09-01T00:00:00", "2026-10-01T00:00:00")
        assert got == [("2026-09-01T00:00:00", "2026-10-01T00:00:00")]

    def test_full_year_twelve_contiguous_windows(self):
        got = socrata.month_windows("2025-10-01T00:00:00", "2026-10-01T00:00:00")
        assert len(got) == 12
        assert got[0] == ("2025-10-01T00:00:00", "2025-11-01T00:00:00")
        assert got[-1] == ("2026-09-01T00:00:00", "2026-10-01T00:00:00")
        # half-open contiguous coverage: each window starts where the previous ended
        assert all(got[i][1] == got[i + 1][0] for i in range(len(got) - 1))

    def test_clips_partial_first_and_last_month(self):
        got = socrata.month_windows("2026-09-15T00:00:00", "2026-11-20T00:00:00")
        assert got == [
            ("2026-09-15T00:00:00", "2026-10-01T00:00:00"),
            ("2026-10-01T00:00:00", "2026-11-01T00:00:00"),
            ("2026-11-01T00:00:00", "2026-11-20T00:00:00"),
        ]

    def test_december_rolls_over_to_next_year(self):
        got = socrata.month_windows("2026-12-01T00:00:00", "2027-02-01T00:00:00")
        assert got == [
            ("2026-12-01T00:00:00", "2027-01-01T00:00:00"),
            ("2027-01-01T00:00:00", "2027-02-01T00:00:00"),
        ]

    def test_same_month_window(self):
        got = socrata.month_windows("2026-09-10T00:00:00", "2026-09-20T00:00:00")
        assert got == [("2026-09-10T00:00:00", "2026-09-20T00:00:00")]

    def test_rejects_start_not_before_end(self):
        with pytest.raises(ValueError):
            socrata.month_windows("2026-10-01", "2026-09-01")
