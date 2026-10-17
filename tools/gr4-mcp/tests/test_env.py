from pathlib import Path
from gr4_mcp.env import GR4Environment


def test_env_detection():
    env = GR4Environment()
    info = env.get_info()

    assert info["cpp_standard"] == "C++23"
    assert info["workspace_root"] is not None
    assert Path(info["workspace_root"]).exists()

    # Presets from CMakePresets.json should be discovered
    presets = info["available_presets"]
    assert "dev" in presets
    assert "full" in presets


def test_runtime_env_keys():
    env = GR4Environment()
    runtime_vars = env.get_runtime_env()
    assert isinstance(runtime_vars, dict)
    assert "PATH" in runtime_vars
