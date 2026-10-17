# GNU Radio 4 MCP Server (`gr4-mcp`)

Model Context Protocol (MCP) server providing AI-assisted development tools and resources for GNU Radio 4 (GR4).

## Overview

`gr4-mcp` allows AI coding assistants (such as Antigravity IDE, VS Code, Cursor, and Claude Desktop) to:
- Inspect active GNU Radio 4 installation prefixes, C++23 standards, and CMake build presets.
- Connect to the GNU Radio 4 control plane daemon (`gr4cp_server`) via HTTP to discover installed blocks and validate flowgraphs.
- Scaffold C++23 signal processing blocks conforming to the `gr::BlockLike` concept and modern template design.
- Scaffold and build Out-Of-Tree (OOT) modules linked against the installed SDK.

## Running the Server

Using the virtual environment:
```sh
cd tools/gr4-mcp
.\.venv\Scripts\python -m gr4_mcp.server
```

Or via entrypoint:
```sh
.\.venv\Scripts\gr4-mcp
```

## Running Tests

```sh
.\tools\gr4-mcp\.venv\Scripts\pytest tools/gr4-mcp/tests -v
```
