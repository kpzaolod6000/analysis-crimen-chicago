"""Unit tests for the pure logic of ingestion.quality (fake cursor, no DB)."""

import pytest
from ingestion import quality


class FakeCursor:
    def __init__(self, row):
        self.row = row
        self.queries = []

    def execute(self, query):
        self.queries.append(str(query))

    def fetchone(self):
        return self.row


class TestNullRate:
    def test_computes_fraction(self):
        cur = FakeCursor((5, 20))
        assert quality.null_rate(cur, "date") == 0.25
        assert "date" in cur.queries[0]

    def test_zero_total_returns_zero_instead_of_dividing(self):
        assert quality.null_rate(FakeCursor((0, 0)), "date") == 0.0

    def test_rejects_column_outside_whitelist(self):
        cur = FakeCursor((0, 0))
        with pytest.raises(ValueError, match="column not measurable"):
            quality.null_rate(cur, "loaded_at; DROP TABLE raw.crimes")
        assert cur.queries == []  # rejected before hitting the DB
