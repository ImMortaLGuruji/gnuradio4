import json
import pytest
from gr4_mcp.server import (
    gr4_get_sdk_info,
    gr4_list_blocks,
    gr4_get_block_details,
    gr4_get_block_concept,
    gr4_scaffold_block,
    gr4_scaffold_oot_module,
    get_block_concept_resource,
    get_catalog_blocks_resource,
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
    # Check that Rotator is present
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
    raw = gr4_scaffold_block(
        block_name="Gain",
        namespace="my_dsp::blocks",
        input_type="float",
        output_type="float",
        description="Scales input samples by a gain factor",
    )
    data = json.loads(raw)
    assert data["header_file"] == "Gain.hpp"
    assert "static_assert(gr::BlockLike<Gain<>>);" in data["header_content"]
    assert "gr::PortIn<TIn> in;" in data["header_content"]
    assert "gr::PortOut<TOut> out;" in data["header_content"]
    assert "Gain_test.cpp" == data["test_file"]


def test_scaffold_oot_module():
    raw = gr4_scaffold_oot_module("my_awesome_oot")
    data = json.loads(raw)
    assert data["cmake_file"] == "CMakeLists.txt"
    assert "project(my_awesome_oot LANGUAGES CXX)" in data["cmake_content"]
    assert "find_package(gnuradio4 CONFIG REQUIRED)" in data["cmake_content"]
    assert "gnuradio4::gnuradio-core" in data["cmake_content"]


def test_resources():
    concept = get_block_concept_resource()
    assert "gr::BlockLike" in concept

    catalog = json.loads(get_catalog_blocks_resource())
    assert isinstance(catalog, list)
    assert len(catalog) > 0
