"""GNU Radio 4 Model Context Protocol (MCP) Server."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.mcpserver import MCPServer

from gr4_mcp.client import GR4ControlPlaneClient
from gr4_mcp.env import GR4Environment

server = MCPServer(
    name="gr4-mcp",
    version="0.1.0",
    description="Model Context Protocol server for GNU Radio 4 AI-driven development",
)

env = GR4Environment()
client = GR4ControlPlaneClient()

CPP23_BLOCK_CONCEPT_DOCS = """
# GNU Radio 4 C++23 Block Architecture

In GNU Radio 4, blocks are modern C++23 types that satisfy the `gr::BlockLike` concept.
Unlike GNU Radio 3.x, blocks in GR4:
1. Do not require inheriting from virtual base classes (`gr::block` or `gr::sync_block`).
2. Can be value-types or structs adhering to structural concepts.
3. Use modern C++23 concepts and templates for port definitions (`gr::PortIn<T>`, `gr::PortOut<T>`).
4. Support zero-copy buffer handoffs and bulk processing functions (`processBulk`).

### Canonical Block Pattern:
```cpp
#include <gnuradio-4.0/Block.hpp>
#include <complex>

namespace my_org::blocks {

template <typename T = std::complex<float>>
struct ComplexRotator {
    // Port declarations
    gr::PortIn<T> in;
    gr::PortOut<T> out;

    // Block properties / parameters
    float phase_increment = 0.0f;
    float current_phase = 0.0f;

    // Core bulk processing function
    gr::work::Status processBulk(const gr::ConsumableSpan<T>& in_span,
                                 gr::PublishableSpan<T>& out_span) {
        const size_t n_samples = std::min(in_span.size(), out_span.size());
        for (size_t i = 0; i < n_samples; ++i) {
            out_span[i] = in_span[i] * std::polar(1.0f, current_phase);
            current_phase += phase_increment;
        }
        return gr::work::Status::OK;
    }
};

static_assert(gr::BlockLike<ComplexRotator<>>);

} // namespace my_org::blocks
```
"""

BUILTIN_BLOCKS_CATALOG = [
    {
        "id": "gr::blocks::math::Rotator",
        "name": "Rotator",
        "category": "Math",
        "description": "Multiplies complex input samples by a rotating complex phase vector.",
        "inputs": [{"name": "in", "type": "std::complex<T>"}],
        "outputs": [{"name": "out", "type": "std::complex<T>"}],
        "parameters": [{"name": "phase_increment", "type": "float", "default": "0.0"}],
    },
    {
        "id": "gr::blocks::math::Add",
        "name": "Add",
        "category": "Math",
        "description": "Computes element-wise sum of two input sample streams.",
        "inputs": [
            {"name": "in0", "type": "T"},
            {"name": "in1", "type": "T"},
        ],
        "outputs": [{"name": "out", "type": "T"}],
        "parameters": [],
    },
    {
        "id": "gr::blocks::filter::FirFilter",
        "name": "FirFilter",
        "category": "Filter",
        "description": "Finite Impulse Response filter processing input samples with given taps.",
        "inputs": [{"name": "in", "type": "T"}],
        "outputs": [{"name": "out", "type": "T"}],
        "parameters": [{"name": "taps", "type": "std::vector<float>", "default": "[]"}],
    },
    {
        "id": "gr::blocks::sources::NullSource",
        "name": "NullSource",
        "category": "Sources",
        "description": "Generates constant zero or null samples.",
        "inputs": [],
        "outputs": [{"name": "out", "type": "T"}],
        "parameters": [],
    },
    {
        "id": "gr::blocks::sinks::NullSink",
        "name": "NullSink",
        "category": "Sinks",
        "description": "Discards all incoming samples without processing.",
        "inputs": [{"name": "in", "type": "T"}],
        "outputs": [],
        "parameters": [],
    },
]


@server.tool()
def gr4_get_sdk_info() -> str:
    """Return active GNU Radio 4 workspace info, install prefix, libraries, plugins, and CMake presets."""
    info = env.get_info()
    return json.dumps(info, indent=2)


@server.tool()
async def gr4_check_health() -> str:
    """Check if the GNU Radio 4 control plane (gr4cp_server) is running and healthy."""
    result = await client.check_health()
    return json.dumps(result, indent=2)


@server.tool()
async def gr4_list_blocks(category: Optional[str] = None) -> str:
    """List available GNU Radio 4 blocks from the live control-plane or the core catalog."""
    live_result = await client.list_blocks()
    blocks = live_result.get("blocks", []) if live_result.get("success") else BUILTIN_BLOCKS_CATALOG

    if category:
        cat_lower = category.lower()
        blocks = [b for b in blocks if b.get("category", "").lower() == cat_lower]

    return json.dumps({"source": "live_control_plane" if live_result.get("success") else "builtin_catalog", "count": len(blocks), "blocks": blocks}, indent=2)


@server.tool()
async def gr4_get_block_details(block_id: str) -> str:
    """Retrieve port signatures, parameters, and metadata for a specific GNU Radio 4 block."""
    live_result = await client.get_block_details(block_id)
    if live_result.get("found"):
        return json.dumps(live_result["block"], indent=2)

    for b in BUILTIN_BLOCKS_CATALOG:
        if b["id"] == block_id or b["name"] == block_id:
            return json.dumps(b, indent=2)

    return json.dumps({"error": f"Block '{block_id}' not found in active catalog"}, indent=2)


@server.tool()
def gr4_get_block_concept() -> str:
    """Return documentation and code examples explaining the C++23 gr::BlockLike concept and port architecture."""
    return CPP23_BLOCK_CONCEPT_DOCS


@server.tool()
def gr4_scaffold_block(
    block_name: str,
    namespace: str = "my_oot::blocks",
    input_type: str = "std::complex<float>",
    output_type: str = "std::complex<float>",
    description: str = "Custom GNU Radio 4 DSP block",
) -> str:
    """Scaffold a modern C++23 GNU Radio 4 block header and test template satisfying gr::BlockLike."""
    header_code = f"""#pragma once

#include <gnuradio-4.0/Block.hpp>
#include <complex>
#include <algorithm>

namespace {namespace} {{

/**
 * @brief {description}
 */
template <typename TIn = {input_type}, typename TOut = {output_type}>
struct {block_name} {{
    // Ports
    gr::PortIn<TIn> in;
    gr::PortOut<TOut> out;

    // Process bulk samples
    gr::work::Status processBulk(const gr::ConsumableSpan<TIn>& in_span,
                                 gr::PublishableSpan<TOut>& out_span) {{
        const size_t count = std::min(in_span.size(), out_span.size());
        for (size_t i = 0; i < count; ++i) {{
            out_span[i] = static_cast<TOut>(in_span[i]);
        }}
        return gr::work::Status::OK;
    }}
}};

// Verify at compile time that the block conforms to the GNU Radio 4 concept
static_assert(gr::BlockLike<{block_name}<>>);

}} // namespace {namespace}
"""

    test_code = f"""#include "{block_name}.hpp"
#include <cassert>
#include <vector>

int main() {{
    using BlockType = {namespace}::{block_name}<>;
    static_assert(gr::BlockLike<BlockType>);

    BlockType block;
    (void)block;

    return 0;
}}
"""

    return json.dumps(
        {
            "block_name": block_name,
            "header_file": f"{block_name}.hpp",
            "header_content": header_code,
            "test_file": f"{block_name}_test.cpp",
            "test_content": test_code,
        },
        indent=2,
    )


@server.tool()
def gr4_scaffold_oot_module(module_name: str) -> str:
    """Scaffold a clean Out-Of-Tree (OOT) CMakeLists.txt that links against the installed GNU Radio 4 SDK."""
    cmake_content = f"""cmake_minimum_required(VERSION 3.27)

project({module_name} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(gnuradio4 CONFIG REQUIRED)
find_package(gnuradio4Library CONFIG REQUIRED)
find_package(gnuradio4Blocks CONFIG REQUIRED)

add_library({module_name} INTERFACE)
target_include_directories({module_name} INTERFACE include)
target_link_libraries({module_name} INTERFACE
    gnuradio4::gnuradio-core
    gnuradio4::gnuradio-algorithm
    gnuradio4::gr-math
)

enable_testing()
add_subdirectory(tests)
"""
    return json.dumps(
        {
            "module_name": module_name,
            "cmake_file": "CMakeLists.txt",
            "cmake_content": cmake_content,
            "integration_hint": "To register this module with gnuradio4 superbuild, add it to projects.local.cmake using gr4_register_module.",
        },
        indent=2,
    )


# MCP Resources
@server.resource("gr4://sdk/info")
def get_sdk_info_resource() -> str:
    """Resource returning active SDK configuration and search paths."""
    return json.dumps(env.get_info(), indent=2)


@server.resource("gr4://sdk/block-concept")
def get_block_concept_resource() -> str:
    """Resource returning C++23 gr::BlockLike concept specifications."""
    return CPP23_BLOCK_CONCEPT_DOCS


@server.resource("gr4://catalog/blocks")
def get_catalog_blocks_resource() -> str:
    """Resource returning default block catalog."""
    return json.dumps(BUILTIN_BLOCKS_CATALOG, indent=2)


# MCP Prompts
@server.prompt()
def scaffold_dsp_block(block_name: str, purpose: str) -> str:
    """Prompt template guiding the AI to design a C++23 DSP block."""
    return f"""You are designing a GNU Radio 4 signal processing block named '{block_name}' for purpose: '{purpose}'.
GNU Radio 4 uses C++23 and concept-based design.
Guidelines:
1. Ensure the struct satisfies `gr::BlockLike`.
2. Declare input ports with `gr::PortIn<T>` and output ports with `gr::PortOut<T>`.
3. Implement `gr::work::Status processBulk(...)` using `gr::ConsumableSpan` and `gr::PublishableSpan`.
4. Add a `static_assert(gr::BlockLike<{block_name}<...>>);` verification.
5. Provide a corresponding C++23 unit test verifying sample processing correctness.
"""


def main() -> None:
    """Run the GNU Radio 4 MCP server with stdio transport."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        server.run(transport="stdio")
    elif transport in ("sse", "streamable-http"):
        server.run(transport=transport)
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
