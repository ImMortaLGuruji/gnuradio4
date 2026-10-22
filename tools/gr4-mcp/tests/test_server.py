import json
import tempfile
from pathlib import Path
import pytest

from gr4_mcp.server import (
    gr4_get_sdk_info,
    gr4_list_blocks,
    gr4_get_block_details,
    gr4_get_block_concept,
    gr4_scaffold_block,
    gr4_scaffold_oot_module,
    gr4_build_oot,
    gr4_test_oot,
    gr4_diagnose_compiler_error,
    gr4_validate_flowgraph,
    gr4_deploy_flowgraph,
    gr4_inspect_flowgraph_state,
    get_block_concept_resource,
    get_catalog_blocks_resource,
    get_oot_template_resource,
    get_block_resource,
    get_sample_flowgraph_resource,
    scaffold_dsp_block,
    port_gr3_to_gr4,
    troubleshoot_dsp_pipeline,
)


def test_sdk_info():
    raw = gr4_get_sdk_info()
    data = json.loads(raw)
    assert data["cpp_standard"] == "C++23"
    assert "available_presets" in data


@pytest.mark.asyncio
async def test_list_blocks():
    raw = await gr4_list_blocks()
    data = json.loads(raw)
    assert "blocks" in data
    assert data["count"] > 0
    ids = [b["id"] for b in data["blocks"]]
    assert any("Rotator" in b_id for b_id in ids)


@pytest.mark.asyncio
async def test_get_block_details():
    raw = await gr4_get_block_details("Rotator")
    data = json.loads(raw)
    assert data.get("name") == "Rotator"
    assert "parameters" in data


def test_block_concept():
    text = gr4_get_block_concept()
    assert "gr::BlockLike" in text
    assert "processBulk" in text


def test_scaffold_block():
    with tempfile.TemporaryDirectory() as tmpdir:
        raw = gr4_scaffold_block(
            block_name="Gain",
            namespace="my_dsp::blocks",
            input_type="float",
            output_type="float",
            description="Scales input samples by a gain factor",
            target_dir=tmpdir,
        )
        data = json.loads(raw)
        assert data["header_file"] == "Gain.hpp"
        assert "static_assert(gr::BlockLike<Gain<>>);" in data["header_content"]
        assert "gr::PortIn<TIn> in;" in data["header_content"]
        assert "gr::PortOut<TOut> out;" in data["header_content"]
        assert "Gain_test.cpp" == data["test_file"]
        assert len(data["written_files"]) == 2
        assert (Path(tmpdir) / "Gain.hpp").exists()
        assert (Path(tmpdir) / "Gain_test.cpp").exists()


def test_scaffold_oot_module():
    with tempfile.TemporaryDirectory() as tmpdir:
        raw = gr4_scaffold_oot_module("my_awesome_oot", target_dir=tmpdir)
        data = json.loads(raw)
        assert data["cmake_file"] == "CMakeLists.txt"
        assert "project(my_awesome_oot LANGUAGES CXX)" in data["cmake_content"]
        assert "find_package(gnuradio4 CONFIG REQUIRED)" in data["cmake_content"]
        assert "gnuradio4::gnuradio-core" in data["cmake_content"]
        assert len(data["written_files"]) == 2
        assert (Path(tmpdir) / "CMakeLists.txt").exists()
        assert (Path(tmpdir) / "tests" / "CMakeLists.txt").exists()


def test_phase4_build_tools():
    raw_build = gr4_build_oot("/nonexistent/test/dir")
    data_build = json.loads(raw_build)
    assert data_build["success"] is False

    raw_test = gr4_test_oot("/nonexistent/test/dir")
    data_test = json.loads(raw_test)
    assert data_test["success"] is False

    error_snippet = (
        "error: static assertion failed: constraints not satisfied for 'BlockLike'"
    )
    raw_diag = gr4_diagnose_compiler_error(error_snippet)
    data_diag = json.loads(raw_diag)
    assert data_diag["has_recognized_patterns"] is True


@pytest.mark.asyncio
async def test_resources():
    concept = get_block_concept_resource()
    assert "gr::BlockLike" in concept

    catalog = json.loads(get_catalog_blocks_resource())
    assert isinstance(catalog, list)
    assert len(catalog) > 0

    oot_template = get_oot_template_resource()
    assert "find_package(gnuradio4 CONFIG REQUIRED)" in oot_template

    block_res = await get_block_resource("Rotator")
    data_block = json.loads(block_res)
    assert data_block.get("name") == "Rotator"


def test_prompts():
    prompt_scaffold = scaffold_dsp_block("FirFilter", "Perform FIR filtering")
    assert "FirFilter" in prompt_scaffold
    assert "gr::BlockLike" in prompt_scaffold

    prompt_port = port_gr3_to_gr4("// Legacy GR3 code")
    assert "gr::sync_block" in prompt_port
    assert "processBulk" in prompt_port

    prompt_trouble = troubleshoot_dsp_pipeline(
        "Buffer overflow at high sample rate", "Log: drop 500 samples"
    )
    assert "Buffer overflow" in prompt_trouble
    assert "drop 500 samples" in prompt_trouble


@pytest.mark.asyncio
async def test_phase5_flowgraph_tools():
    # 1. Validation tool
    valid_fg = {
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
    raw_val = await gr4_validate_flowgraph(json.dumps(valid_fg))
    data_val = json.loads(raw_val)
    assert data_val["valid"] is True
    assert data_val["block_count"] == 2

    # 2. Deploy / simulate tool
    raw_deploy = await gr4_deploy_flowgraph(
        json.dumps(valid_fg), run_duration_seconds=2.0
    )
    data_deploy = json.loads(raw_deploy)
    assert data_deploy["success"] is True

    # 3. Inspect state tool
    raw_inspect = await gr4_inspect_flowgraph_state()
    data_inspect = json.loads(raw_inspect)
    assert "online" in data_inspect or "success" in data_inspect

    # 4. Sample flowgraph resource
    sample_raw = get_sample_flowgraph_resource()
    sample_data = json.loads(sample_raw)
    assert "blocks" in sample_data
    assert "connections" in sample_data
