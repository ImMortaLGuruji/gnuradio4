import pytest
from gr4_mcp.flowgraph import FlowgraphSimulator, FlowgraphValidator

SAMPLE_CATALOG = [
    {
        "id": "gr::blocks::sources::NullSource",
        "name": "NullSource",
        "inputs": [],
        "outputs": [{"name": "out", "type": "std::complex<float>"}],
    },
    {
        "id": "gr::blocks::math::Rotator",
        "name": "Rotator",
        "inputs": [{"name": "in", "type": "std::complex<float>"}],
        "outputs": [{"name": "out", "type": "std::complex<float>"}],
    },
    {
        "id": "gr::blocks::sinks::NullSink",
        "name": "NullSink",
        "inputs": [{"name": "in", "type": "std::complex<float>"}],
        "outputs": [],
    },
    {
        "id": "gr::blocks::filter::FirFilterFloat",
        "name": "FirFilterFloat",
        "inputs": [{"name": "in", "type": "float"}],
        "outputs": [{"name": "out", "type": "float"}],
    },
]


def test_valid_flowgraph():
    fg = {
        "id": "test_pipeline",
        "blocks": [
            {"id": "src", "type": "gr::blocks::sources::NullSource"},
            {"id": "rot", "type": "gr::blocks::math::Rotator"},
            {"id": "snk", "type": "gr::blocks::sinks::NullSink"},
        ],
        "connections": [
            {
                "source": "src",
                "source_port": "out",
                "target": "rot",
                "target_port": "in",
            },
            {
                "source": "rot",
                "source_port": "out",
                "target": "snk",
                "target_port": "in",
            },
        ],
    }
    res = FlowgraphValidator.validate(fg, known_blocks=SAMPLE_CATALOG)
    assert res["valid"] is True
    assert res["block_count"] == 3
    assert res["connection_count"] == 2
    assert len(res["errors"]) == 0


def test_duplicate_block_id():
    fg = {
        "blocks": [
            {"id": "node1", "type": "NullSource"},
            {"id": "node1", "type": "NullSink"},
        ],
        "connections": [],
    }
    res = FlowgraphValidator.validate(fg)
    assert res["valid"] is False
    assert any("Duplicate block ID" in e for e in res["errors"])


def test_nonexistent_block_in_connection():
    fg = {
        "blocks": [
            {"id": "src", "type": "NullSource"},
        ],
        "connections": [
            {
                "source": "src",
                "source_port": "out",
                "target": "missing_node",
                "target_port": "in",
            },
        ],
    }
    res = FlowgraphValidator.validate(fg)
    assert res["valid"] is False
    assert any("non-existent target block 'missing_node'" in e for e in res["errors"])


def test_port_type_mismatch():
    fg = {
        "blocks": [
            {
                "id": "src",
                "type": "gr::blocks::sources::NullSource",
            },  # outputs std::complex<float>
            {"id": "flt", "type": "gr::blocks::filter::FirFilterFloat"},  # inputs float
        ],
        "connections": [
            {
                "source": "src",
                "source_port": "out",
                "target": "flt",
                "target_port": "in",
            },
        ],
    }
    res = FlowgraphValidator.validate(fg, known_blocks=SAMPLE_CATALOG)
    assert res["valid"] is False
    assert any("Port type mismatch" in e for e in res["errors"])


def test_cycle_detection():
    fg = {
        "blocks": [
            {"id": "a", "type": "BlockA"},
            {"id": "b", "type": "BlockB"},
        ],
        "connections": [
            {"source": "a", "source_port": "out", "target": "b", "target_port": "in"},
            {"source": "b", "source_port": "out", "target": "a", "target_port": "in"},
        ],
    }
    res = FlowgraphValidator.validate(fg)
    assert res["cycles_detected"] is True
    assert any("Cycle(s) detected" in w for w in res["warnings"])


@pytest.mark.asyncio
async def test_simulator_offline_dry_run():
    sim = FlowgraphSimulator()
    fg = {
        "id": "offline_test",
        "blocks": [
            {"id": "src", "type": "gr::blocks::sources::NullSource"},
            {"id": "snk", "type": "gr::blocks::sinks::NullSink"},
        ],
        "connections": [
            {
                "source": "src",
                "source_port": "out",
                "target": "snk",
                "target_port": "in",
            },
        ],
    }
    res = await sim.deploy_and_simulate(
        fg, duration_seconds=3.0, known_blocks=SAMPLE_CATALOG
    )
    assert res["success"] is True
    assert res["stage"] == "dry_run_simulation"
    assert res["server_online"] is False
    assert "prerequisites" in res
    assert "gr4cp_server" in res["prerequisites"]["required_service"]
    assert res["dry_run_metrics"]["blocks_initialized"] == 2


@pytest.mark.asyncio
async def test_inspect_state_offline():
    sim = FlowgraphSimulator()
    res = await sim.inspect_state()
    assert res["online"] is False
    assert "offline" in res["error"]
