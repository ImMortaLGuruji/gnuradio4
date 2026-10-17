"""Environment discovery and configuration for GNU Radio 4."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class GR4Environment:
    """Encapsulates GNU Radio 4 environment detection, paths, and active toolchains."""

    def __init__(
        self, workspace_root: Optional[Path] = None, prefix: Optional[Path] = None
    ) -> None:
        self.workspace_root = workspace_root or self._find_workspace_root()
        self.prefix = prefix or self._find_install_prefix()

    def _find_workspace_root(self) -> Path:
        """Find the root of the gnuradio4 superbuild repository."""
        # 1. Environment variable
        env_root = os.environ.get("GR4_WORKSPACE_ROOT")
        if env_root and Path(env_root).is_dir():
            return Path(env_root).resolve()

        # 2. Check parents from current file
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "modules.cmake").exists() and (
                parent / "CMakeLists.txt"
            ).exists():
                return parent

        # 3. Fallback to current working directory
        cwd = Path.cwd().resolve()
        if (cwd / "modules.cmake").exists():
            return cwd

        # Fallback to current file's 3rd parent (e.g., tools/gr4-mcp/src/gr4_mcp -> tools/gr4-mcp -> tools -> root)
        return current.parents[3] if len(current.parents) > 3 else cwd

    def _find_install_prefix(self) -> Optional[Path]:
        """Detect the active install prefix."""
        # 1. Explicit environment variable
        env_prefix = os.environ.get("GR4_PREFIX") or os.environ.get("CMAKE_PREFIX_PATH")
        if env_prefix:
            for p in env_prefix.split(os.pathsep):
                candidate = Path(p).resolve()
                if (candidate / "include" / "gnuradio-4.0").exists() or (
                    candidate / "bin" / "gr4cp_server"
                ).exists():
                    return candidate

        # 2. Check known build prefixes in the workspace
        if self.workspace_root:
            candidates = [
                self.workspace_root / "install" / "full",
                self.workspace_root / "install",
                self.workspace_root / "install" / "dev",
                self.workspace_root / "install" / "debug",
                self.workspace_root / "install" / "release",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate

        return None

    def get_info(self) -> Dict[str, Any]:
        """Return a structured summary of the environment."""
        headers_exist = False
        lib_dir = None
        plugins_dir = None
        server_executable = None

        if self.prefix:
            include_dir = self.prefix / "include" / "gnuradio-4.0"
            headers_exist = include_dir.exists()

            for lib_name in ["lib", "lib64"]:
                cand = self.prefix / lib_name
                if cand.exists():
                    lib_dir = str(cand)
                    cand_plugins = cand / "gnuradio-4" / "plugins"
                    if cand_plugins.exists():
                        plugins_dir = str(cand_plugins)
                    break

            for bin_name in ["gr4cp_server", "gr4cp_server.exe"]:
                cand = self.prefix / "bin" / bin_name
                if cand.exists():
                    server_executable = str(cand)
                    break

        presets = self.list_presets()

        return {
            "workspace_root": str(self.workspace_root) if self.workspace_root else None,
            "prefix": str(self.prefix) if self.prefix else None,
            "headers_installed": headers_exist,
            "lib_dir": lib_dir,
            "plugins_dir": plugins_dir,
            "server_executable": server_executable,
            "available_presets": presets,
            "cpp_standard": "C++23",
        }

    def list_presets(self) -> List[str]:
        """List presets from CMakePresets.json."""
        if not self.workspace_root:
            return []
        presets_file = self.workspace_root / "CMakePresets.json"
        if not presets_file.exists():
            return []
        try:
            with open(presets_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            presets = [
                p["name"]
                for p in data.get("configurePresets", [])
                if not p.get("hidden", False)
            ]
            return presets
        except Exception:
            return []

    def get_runtime_env(self) -> Dict[str, str]:
        """Construct the runtime environment variables as defined in activate.sh."""
        env = dict(os.environ)
        if not self.prefix:
            return env

        prefix_str = str(self.prefix)
        env["GR4_PREFIX"] = prefix_str

        # PATH
        bin_dir = str(self.prefix / "bin")
        current_path = env.get("PATH", "")
        env["PATH"] = (
            f"{bin_dir}{os.pathsep}{current_path}" if current_path else bin_dir
        )

        # CMAKE_PREFIX_PATH
        current_cmake = env.get("CMAKE_PREFIX_PATH", "")
        env["CMAKE_PREFIX_PATH"] = (
            f"{prefix_str}{os.pathsep}{current_cmake}" if current_cmake else prefix_str
        )

        # Lib dirs
        lib_dir = self.prefix / "lib"
        if not lib_dir.exists() and (self.prefix / "lib64").exists():
            lib_dir = self.prefix / "lib64"

        if lib_dir.exists():
            lib_str = str(lib_dir)
            # PKG_CONFIG_PATH
            pkg_config = f"{lib_str}/pkgconfig{os.pathsep}{prefix_str}/share/pkgconfig"
            current_pkg = env.get("PKG_CONFIG_PATH", "")
            env["PKG_CONFIG_PATH"] = (
                f"{pkg_config}{os.pathsep}{current_pkg}" if current_pkg else pkg_config
            )

            # LD_LIBRARY_PATH (Linux) / DYLD_LIBRARY_PATH (macOS)
            for var in ["LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"]:
                cur = env.get(var, "")
                env[var] = f"{lib_str}{os.pathsep}{cur}" if cur else lib_str

            # GNURADIO4_PLUGIN_DIRECTORIES
            plugins_path = f"{lib_str}/gnuradio-4/plugins{os.pathsep}{lib_str}"
            cur_plugins = env.get("GNURADIO4_PLUGIN_DIRECTORIES", "")
            env["GNURADIO4_PLUGIN_DIRECTORIES"] = (
                f"{plugins_path}{os.pathsep}{cur_plugins}"
                if cur_plugins
                else plugins_path
            )

        return env
