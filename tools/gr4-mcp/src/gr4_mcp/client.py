"""Client for GNU Radio 4 Control Plane (gr4cp_server)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx


class GR4ControlPlaneClient:
    """Asynchronous HTTP client for interacting with gr4cp_server."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0) -> None:
        self._explicit_url = base_url
        self._timeout = timeout

    def resolve_base_url(self) -> str:
        """Resolve the control plane base URL."""
        if self._explicit_url:
            return self._explicit_url.rstrip("/")

        # Check environment variable
        env_url = os.environ.get("GR4CP_URL") or os.environ.get("GR4_REMOTE_URL")
        if env_url:
            return env_url.rstrip("/")

        # Check if a port file exists (set by GR4CP_PORT_FILE)
        port_file = os.environ.get("GR4CP_PORT_FILE")
        if port_file and Path(port_file).exists():
            try:
                port = Path(port_file).read_text(encoding="utf-8").strip()
                if port.isdigit():
                    return f"http://127.0.0.1:{port}"
            except Exception:
                pass

        # Default standard port
        return "http://127.0.0.1:8080"

    async def check_health(self) -> Dict[str, Any]:
        """Check if gr4cp_server is running and responsive."""
        base_url = self.resolve_base_url()
        url = f"{base_url}/healthz"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                return {"online": True, "url": base_url, "data": data}
        except httpx.HTTPError as err:
            return {"online": False, "url": base_url, "error": str(err)}
        except Exception as err:
            return {"online": False, "url": base_url, "error": str(err)}

    async def list_blocks(self) -> Dict[str, Any]:
        """Fetch the list of discovered blocks from gr4cp_server."""
        base_url = self.resolve_base_url()
        url = f"{base_url}/blocks"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                blocks = data if isinstance(data, list) else data.get("blocks", [])
                return {"success": True, "count": len(blocks), "blocks": blocks}
        except Exception as err:
            return {"success": False, "error": str(err), "blocks": []}

    async def get_block_details(self, block_id: str) -> Dict[str, Any]:
        """Get details for a specific block by its id or name."""
        all_blocks = await self.list_blocks()
        if not all_blocks.get("success"):
            return {"found": False, "error": all_blocks.get("error")}

        for b in all_blocks.get("blocks", []):
            if b.get("id") == block_id or b.get("name") == block_id:
                return {"found": True, "block": b}

        return {
            "found": False,
            "error": f"Block '{block_id}' not found in runtime catalog",
        }

    async def validate_flowgraph(self, flowgraph: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a flowgraph to gr4cp_server for validation."""
        base_url = self.resolve_base_url()
        url = f"{base_url}/flowgraph/validate"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, json=flowgraph)
                return {
                    "success": resp.status_code == 200,
                    "status_code": resp.status_code,
                    "response": resp.json(),
                }
        except Exception as err:
            return {"success": False, "error": str(err)}

    async def deploy_flowgraph(
        self, flowgraph: Dict[str, Any], duration_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """Deploy and start a flowgraph on gr4cp_server."""
        base_url = self.resolve_base_url()
        url = f"{base_url}/flowgraph"
        payload = {"flowgraph": flowgraph}
        if duration_seconds is not None:
            payload["duration_seconds"] = duration_seconds

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, json=payload)
                return {
                    "success": resp.status_code in (200, 201),
                    "status_code": resp.status_code,
                    "response": resp.json() if resp.content else {},
                }
        except Exception as err:
            return {"success": False, "error": str(err)}

    async def inspect_flowgraph_state(self) -> Dict[str, Any]:
        """Inspect the runtime state, telemetry, and block execution statistics from gr4cp_server."""
        base_url = self.resolve_base_url()
        url = f"{base_url}/flowgraph/status"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return {"success": True, "state": resp.json()}
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": resp.text,
                }
        except Exception as err:
            return {"success": False, "error": str(err)}

    async def stop_flowgraph(self) -> Dict[str, Any]:
        """Stop running flowgraph on gr4cp_server."""
        base_url = self.resolve_base_url()
        url = f"{base_url}/flowgraph/stop"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url)
                return {
                    "success": resp.status_code == 200,
                    "status_code": resp.status_code,
                }
        except Exception as err:
            return {"success": False, "error": str(err)}
