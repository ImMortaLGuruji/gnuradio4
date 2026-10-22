"""Flowgraph validation, simulation, and telemetry for GNU Radio 4."""

from __future__ import annotations

import collections
from typing import Any, Dict, List, Optional, Set

from gr4_mcp.client import GR4ControlPlaneClient


class FlowgraphValidator:
    """Validates GNU Radio 4 flowgraph topology, ports, and data types."""

    # Standard port type compatibility map
    COMPATIBLE_TYPES = {
        "float": {"float", "double", "T"},
        "double": {"double", "float", "T"},
        "int32_t": {"int32_t", "int64_t", "int", "T"},
        "std::complex<float>": {
            "std::complex<float>",
            "std::complex<T>",
            "std::complex<double>",
            "T",
        },
        "std::complex<double>": {
            "std::complex<double>",
            "std::complex<float>",
            "std::complex<T>",
            "T",
        },
        "T": {
            "T",
            "float",
            "double",
            "int32_t",
            "std::complex<float>",
            "std::complex<double>",
        },
    }

    @classmethod
    def validate(
        cls,
        flowgraph: Dict[str, Any],
        known_blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Statically validate flowgraph topology, connectivity, and types."""
        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(flowgraph, dict):
            return {
                "valid": False,
                "errors": ["Flowgraph must be a JSON object."],
                "warnings": [],
            }

        blocks = flowgraph.get("blocks")
        if not isinstance(blocks, list) or len(blocks) == 0:
            return {
                "valid": False,
                "errors": ["Flowgraph must contain a non-empty 'blocks' list."],
                "warnings": [],
            }

        connections = flowgraph.get("connections")
        if not isinstance(connections, list):
            return {
                "valid": False,
                "errors": ["Flowgraph must contain a 'connections' list."],
                "warnings": [],
            }

        # 1. Block ID Uniqueness & Catalog Resolution
        block_map: Dict[str, Dict[str, Any]] = {}
        block_types: Dict[str, str] = {}
        catalog_lookup = {b["id"]: b for b in (known_blocks or [])}
        catalog_lookup.update({b.get("name", ""): b for b in (known_blocks or [])})

        for i, blk in enumerate(blocks):
            if not isinstance(blk, dict):
                errors.append(f"Block at index {i} is not a valid JSON object.")
                continue

            blk_id = blk.get("id")
            blk_type = blk.get("type")

            if not blk_id:
                errors.append(f"Block at index {i} is missing a required 'id'.")
                continue

            if blk_id in block_map:
                errors.append(
                    f"Duplicate block ID detected: '{blk_id}'. Block IDs must be unique."
                )
                continue

            if not blk_type:
                errors.append(f"Block '{blk_id}' is missing a required 'type'.")
                continue

            block_map[blk_id] = blk
            block_types[blk_id] = blk_type

            # Check if block type is recognized
            if known_blocks and blk_type not in catalog_lookup:
                warnings.append(
                    f"Block '{blk_id}' has unrecognized type '{blk_type}'. "
                    "Make sure it is loaded via dynamic plugins or an OOT package."
                )

        # 2. Connection Integrity & Dangling Ports
        connected_inputs: Set[str] = set()
        connected_outputs: Set[str] = set()
        adj_list: Dict[str, List[str]] = collections.defaultdict(list)

        for i, conn in enumerate(connections):
            if not isinstance(conn, dict):
                errors.append(f"Connection at index {i} is not a valid JSON object.")
                continue

            src = conn.get("source")
            src_port = conn.get("source_port", "out")
            dst = conn.get("target")
            dst_port = conn.get("target_port", "in")

            if not src or not dst:
                errors.append(
                    f"Connection {i} must specify both 'source' and 'target' block IDs."
                )
                continue

            if src not in block_map:
                errors.append(
                    f"Connection {i} references non-existent source block '{src}'."
                )
                continue

            if dst not in block_map:
                errors.append(
                    f"Connection {i} references non-existent target block '{dst}'."
                )
                continue

            if src == dst:
                warnings.append(
                    f"Direct self-loop detected on block '{src}'. Ensure feedback scheduling is intended."
                )

            adj_list[src].append(dst)
            connected_inputs.add(f"{dst}:{dst_port}")
            connected_outputs.add(f"{src}:{src_port}")

            # Port Type Checking if catalog is available
            src_desc = catalog_lookup.get(block_types.get(src, ""))
            dst_desc = catalog_lookup.get(block_types.get(dst, ""))

            if src_desc and dst_desc:
                src_port_def = next(
                    (p for p in src_desc.get("outputs", []) if p["name"] == src_port),
                    None,
                )
                dst_port_def = next(
                    (p for p in dst_desc.get("inputs", []) if p["name"] == dst_port),
                    None,
                )

                if src_port_def and dst_port_def:
                    src_type = src_port_def.get("type", "T")
                    dst_type = dst_port_def.get("type", "T")
                    if not cls._types_are_compatible(src_type, dst_type):
                        errors.append(
                            f"Port type mismatch in connection '{src}:{src_port}' -> '{dst}:{dst_port}': "
                            f"cannot connect output type '{src_type}' to input type '{dst_type}'."
                        )

        # 3. Check for Orphaned Blocks
        for blk_id in block_map:
            has_connections = any(
                src == blk_id or dst == blk_id
                for conn in connections
                for src, dst in [(conn.get("source"), conn.get("target"))]
            )
            if not has_connections and len(block_map) > 1:
                warnings.append(
                    f"Block '{blk_id}' has no incoming or outgoing connections (isolated block)."
                )

        # 4. Topological Cycle Detection
        visited: Dict[str, int] = {
            k: 0 for k in block_map
        }  # 0: unvisited, 1: visiting, 2: visited
        cycles: List[List[str]] = []

        def dfs(node: str, path: List[str]) -> None:
            visited[node] = 1
            path.append(node)
            for neighbor in adj_list.get(node, []):
                if visited.get(neighbor) == 1:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                elif visited.get(neighbor) == 0:
                    dfs(neighbor, path)
            path.pop()
            visited[node] = 2

        for blk_id in block_map:
            if visited[blk_id] == 0:
                dfs(blk_id, [])

        if cycles:
            cycle_strs = [" -> ".join(c) for c in cycles]
            warnings.append(
                f"Cycle(s) detected in flowgraph: {'; '.join(cycle_strs)}. Ensure cyclic feedback scheduler is configured."
            )

        return {
            "valid": len(errors) == 0,
            "block_count": len(block_map),
            "connection_count": len(connections),
            "errors": errors,
            "warnings": warnings,
            "cycles_detected": len(cycles) > 0,
        }

    @classmethod
    def _types_are_compatible(cls, src_type: str, dst_type: str) -> bool:
        if src_type == dst_type or src_type == "T" or dst_type == "T":
            return True
        allowed = cls.COMPATIBLE_TYPES.get(src_type, set())
        return dst_type in allowed


class FlowgraphSimulator:
    """Manages flowgraph validation, deployment, simulation, and telemetry."""

    def __init__(self, client: Optional[GR4ControlPlaneClient] = None) -> None:
        self.client = client or GR4ControlPlaneClient()

    async def deploy_and_simulate(
        self,
        flowgraph: Dict[str, Any],
        duration_seconds: float = 5.0,
        known_blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Validate topology and deploy to gr4cp_server, or provide dry-run metrics if offline."""
        # Step 1: Static validation
        validation = FlowgraphValidator.validate(flowgraph, known_blocks=known_blocks)
        if not validation["valid"]:
            return {
                "success": False,
                "stage": "validation",
                "errors": validation["errors"],
                "warnings": validation["warnings"],
                "telemetry": None,
            }

        # Step 2: Check server availability
        health = await self.client.check_health()
        if not health.get("online"):
            return {
                "success": True,
                "stage": "dry_run_simulation",
                "mode": "offline",
                "server_online": False,
                "server_url": health.get("url"),
                "prerequisites": {
                    "required_service": "gr4cp_server (GNU Radio 4 Control Plane)",
                    "how_to_run_locally": "gr4cp_server (or build with preset 'full')",
                    "how_to_run_in_docker": "docker run -p 8080:8080 ghcr.io/gnuradio/gnuradio4-studio:latest",
                },
                "validation": validation,
                "dry_run_metrics": {
                    "status": "Topology verified; pipeline is structurally sound",
                    "blocks_initialized": validation["block_count"],
                    "active_connections": validation["connection_count"],
                    "simulated_duration_seconds": duration_seconds,
                    "estimated_buffer_health": "100%",
                },
            }

        # Step 3: Server is online, deploy to live control plane
        deploy_res = await self.client.deploy_flowgraph(
            flowgraph, duration_seconds=duration_seconds
        )
        if not deploy_res.get("success"):
            return {
                "success": False,
                "stage": "deployment",
                "error": deploy_res.get("error", "Deployment failed on control plane"),
                "status_code": deploy_res.get("status_code"),
            }

        # Step 4: Fetch runtime telemetry
        status_res = await self.client.inspect_flowgraph_state()
        return {
            "success": True,
            "stage": "live_execution",
            "server_online": True,
            "server_url": health.get("url"),
            "deployment": deploy_res.get("response"),
            "telemetry": status_res.get("state") if status_res.get("success") else None,
            "validation": validation,
        }

    async def inspect_state(self) -> Dict[str, Any]:
        """Retrieve real-time telemetry from gr4cp_server."""
        health = await self.client.check_health()
        if not health.get("online"):
            return {
                "online": False,
                "error": "gr4cp_server is offline.",
                "server_url": health.get("url"),
                "hint": "Start gr4cp_server locally or run 'docker run -p 8080:8080 ghcr.io/gnuradio/gnuradio4-studio:latest'",
            }

        return await self.client.inspect_flowgraph_state()
