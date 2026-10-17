import tempfile
from pathlib import Path
from gr4_mcp.builder import GR4Builder
from gr4_mcp.env import GR4Environment


def test_builder_initialization():
    env = GR4Environment()
    builder = GR4Builder(env=env)
    assert builder.env == env


def test_build_oot_missing_project():
    builder = GR4Builder()
    res = builder.build_oot("/nonexistent/path/to/project")
    assert res["success"] is False
    assert "does not contain a CMakeLists.txt" in res["error"]


def test_test_oot_missing_build_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = GR4Builder()
        res = builder.test_oot(tmpdir)
        assert res["success"] is False
        assert "does not exist" in res["error"]
