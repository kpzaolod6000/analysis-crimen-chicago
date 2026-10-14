"""Structural tests for the exported n8n workflow (Sprint 2).

The workflow JSON is maintained by hand (blind export), so these tests pin
the invariants that make the monthly loop work: loop wiring, per-iteration
counting, the truncation guard and the UPSERT/log contracts with Postgres.
They do not replace the manual run in n8n (docs/verification.md).
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / "n8n" / "workflows" / "sprint2-socrata-raw.json"

FETCH = "Socrata: fetch mes"
PAYLOAD = "Validar + SQL payload (mes)"
LOOP = "Loop Over Items"
UPSERT = "raw.crimes upsert (bulk)"
LOG = "log run en pipeline_runs"


@pytest.fixture(scope="module")
def workflow() -> dict:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def nodes(workflow) -> dict:
    return {node["name"]: node for node in workflow["nodes"]}


def test_expected_nodes_present(nodes):
    assert set(nodes) == {
        "Manual Trigger",
        "Ventana dev (1 año)",
        "Meses de la ventana",
        LOOP,
        FETCH,
        PAYLOAD,
        UPSERT,
        LOG,
    }


def test_split_in_batches_config(nodes):
    loop = nodes[LOOP]
    assert loop["type"] == "n8n-nodes-base.splitInBatches"
    assert loop["typeVersion"] == 3
    assert loop["parameters"]["batchSize"] == 1


def test_loop_output_wiring(workflow):
    outputs = workflow["connections"][LOOP]["main"]
    assert len(outputs) == 2  # output 0 = done, output 1 = loop (n8n source)
    assert outputs[0] == []  # done unused: summary lives in ops.pipeline_runs
    assert [edge["node"] for edge in outputs[1]] == [FETCH]


def test_loop_back_edge(workflow):
    targets = workflow["connections"][LOG]["main"][0]
    assert [edge["node"] for edge in targets] == [LOOP]


def test_months_feed_the_loop(workflow):
    targets = workflow["connections"]["Meses de la ventana"]["main"][0]
    assert [edge["node"] for edge in targets] == [LOOP]


def test_http_query_uses_month_window(nodes):
    params = nodes[FETCH]["parameters"]["queryParameters"]["parameters"]
    by_name = {p["name"]: p["value"] for p in params}
    assert "{{ $json.monthStart }}" in by_name["$where"]
    assert "{{ $json.monthEnd }}" in by_name["$where"]
    assert by_name["$order"] == "id"
    assert "$json.pageSize" in by_name["$limit"]


def test_validation_counts_are_per_iteration(nodes):
    code = nodes[PAYLOAD]["parameters"]["jsCode"]
    assert "$input.all()" in code  # scoped to the current loop iteration
    assert f"$('{FETCH}').all()" not in code  # would aggregate ALL iterations


def test_truncation_guard(nodes):
    code = nodes[PAYLOAD]["parameters"]["jsCode"]
    assert "truncated" in code
    assert "pageSize" in code
    assert "'FAILED'" in code


def test_upsert_contract(nodes):
    query = nodes[UPSERT]["parameters"]["query"]
    assert "jsonb_to_recordset" in query
    assert "ON CONFLICT (id)" in query


def test_log_includes_error_message(nodes):
    query = nodes[LOG]["parameters"]["query"]
    assert "ops.pipeline_runs" in query
    assert "error_message" in query


def test_postgres_credentials_stay_as_placeholder(nodes):
    for name in (UPSERT, LOG):
        assert nodes[name]["credentials"]["postgres"]["id"] == "REEMPLAZAR_CRED_ID"
