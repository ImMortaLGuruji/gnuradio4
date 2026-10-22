# GNU Radio 4 MCP Server (`gr4-mcp`)

Model Context Protocol (MCP) server providing AI-assisted development tools, resources, and flowgraph simulations for GNU Radio 4 (GR4).

## Overview

`gr4-mcp` connects AI assistants (Antigravity IDE, VS Code, Cursor, Claude Desktop) with GNU Radio 4, supporting:

- **Environment & SDK Introspection**: Discovers installed prefixes, runtime libraries, plugin catalogs, C++23 flags, and CMake presets.
- **C++23 Code Synthesis**: Scaffolds modern `gr::BlockLike` blocks, port definitions, `processBulk` routines, unit tests, and CMakeLists.txt.
- **Autonomous TDD Build Loop**: Configures and compiles OOT projects with automatic C++23 template concept failure diagnostics.
- **Flowgraph Topology Validation & Simulation**: Statically validates port types, dangling inputs, and cycles; deploys to `gr4cp_server` or provides dry-run metrics when offline.

---

## Prerequisites

| Capability                         | Prerequisite                                             | Notes                                                                                                                                                                             |
| :--------------------------------- | :------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **MCP Server Base**                | Python 3.11+                                             | Installed in virtual environment `tools/gr4-mcp/.venv`                                                                                                                            |
| **Topology Validation & Code Gen** | None (pure Python)                                       | Works immediately offline with built-in or live block catalogs                                                                                                                    |
| **Autonomous OOT Compilation**     | CMake 3.27+, Ninja, C++23 Compiler (GCC 14+ / Clang 20+) | Required for `gr4_build_oot` and `gr4_test_oot`                                                                                                                                   |
| **Live Flowgraph Simulation**      | `gr4cp_server` (GNU Radio 4 Control Plane)               | Built with preset `full`, or running in container: `docker run -p 8080:8080 ghcr.io/gnuradio/gnuradio4-studio:latest`. If offline, dry-run simulation mode is used automatically. |

---

## Tools Reference

| Tool                          | Phase | Description                                                                                 |
| :---------------------------- | :---- | :------------------------------------------------------------------------------------------ |
| `gr4_get_sdk_info`            | 1 & 2 | Returns active GNU Radio 4 workspace info, prefix, libraries, plugins, and presets          |
| `gr4_check_health`            | 1     | Probes `gr4cp_server` health endpoint (`/healthz`)                                          |
| `gr4_list_blocks`             | 2     | Lists blocks from live control plane or built-in standard catalog                           |
| `gr4_get_block_details`       | 2     | Returns port signatures, parameters, and metadata for a block                               |
| `gr4_get_block_concept`       | 2     | Returns C++23 `gr::BlockLike` architectural guidance and concept requirements               |
| `gr4_scaffold_block`          | 3     | Generates C++23 block header and test files (optional `target_dir` writes directly to disk) |
| `gr4_scaffold_oot_module`     | 3     | Scaffolds CMake project for an out-of-tree module (optional `target_dir` writes to disk)    |
| `gr4_build_oot`               | 4     | Configures and builds an OOT project, automatically diagnosing errors on failure            |
| `gr4_test_oot`                | 4     | Runs CTest with timeout handling and returns test statistics                                |
| `gr4_diagnose_compiler_error` | 4     | Analyzes C++23 compiler/build errors and suggests exact code fixes                          |
| `gr4_validate_flowgraph`      | 5     | Validates flowgraph topology, block uniqueness, port type compatibility, and cycles         |
| `gr4_deploy_flowgraph`        | 5     | Deploys flowgraph to `gr4cp_server` or executes dry-run simulation if offline               |
| `gr4_inspect_flowgraph_state` | 5     | Inspects real-time telemetry, buffer states, and throughput                                 |

---

## Resources & Prompts

### Resources

- `gr4://sdk/info`: Active SDK configuration and search paths.
- `gr4://sdk/block-concept`: Modern C++23 `gr::BlockLike` specification.
- `gr4://catalog/blocks`: Default catalog of standard blocks.
- `gr4://templates/oot-project`: CMakeLists.txt template for out-of-tree projects.
- `gr4://blocks/{block_id}`: Port schemas and parameters for a specific block.
- `gr4://flowgraph/sample`: Canonical valid flowgraph JSON schema.

### Prompts

- `scaffold_dsp_block`: Interactive prompt for designing C++23 DSP blocks.
- `port_gr3_to_gr4`: Guidance for converting legacy GNU Radio 3.x blocks to modern GR4.
- `troubleshoot_dsp_pipeline`: Troubleshooting checklist for sample rate mismatches, buffer overflows, and deadlocks.

---

## Running the Server

Using the virtual environment:

```sh
cd tools/gr4-mcp
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

pip install -e .
python -m gr4_mcp.server
```

Or via console entrypoint:

```sh
gr4-mcp
```

## Running Tests

```sh
pytest tests/ -v
```
