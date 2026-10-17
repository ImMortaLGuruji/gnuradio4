from gr4_mcp.diagnostics import CompilerDiagnostics


def test_diagnose_concept_failure():
    log = """
In file included from main.cpp:1:
MyBlock.hpp:35:15: error: static assertion failed: constraints not satisfied for 'BlockLike'
   35 | static_assert(gr::BlockLike<MyBlock<>>);
      |               ^~~~~~~~~~~~~~~~~~~~~~~~
    """
    res = CompilerDiagnostics.diagnose(log)
    assert res["has_recognized_patterns"] is True
    assert any(
        issue["id"] == "GR4_BLOCKLIKE_CONCEPT_FAILURE"
        for issue in res["matched_issues"]
    )
    assert len(res["error_locations"]) > 0
    assert res["error_locations"][0]["line"] == 35


def test_diagnose_process_bulk_mismatch():
    log = """
MyBlock.hpp:20:10: error: no matching function for call to 'processBulk'
with ConsumableSpan and PublishableSpan parameter mismatch
    """
    res = CompilerDiagnostics.diagnose(log)
    assert res["has_recognized_patterns"] is True
    assert any(
        issue["id"] == "GR4_PROCESS_BULK_SIGNATURE_MISMATCH"
        for issue in res["matched_issues"]
    )


def test_diagnose_missing_headers():
    log = """
In file included from MyBlock.hpp:2:
fatal error: gnuradio-4.0/Block.hpp: No such file or directory
    """
    res = CompilerDiagnostics.diagnose(log)
    assert res["has_recognized_patterns"] is True
    assert any(issue["id"] == "GR4_MISSING_HEADER" for issue in res["matched_issues"])


def test_diagnose_cmake_find_package_failure():
    log = """
CMake Error at CMakeLists.txt:8 (find_package):
  Could not find a package configuration file provided by "gnuradio4" with
  any of the following names:
    gnuradio4Config.cmake
    """
    res = CompilerDiagnostics.diagnose(log)
    assert res["has_recognized_patterns"] is True
    assert any(
        issue["id"] == "CMAKE_FIND_PACKAGE_GNURADIO4_FAILED"
        for issue in res["matched_issues"]
    )


def test_diagnose_empty_log():
    res = CompilerDiagnostics.diagnose("")
    assert res["has_recognized_patterns"] is False
    assert len(res["matched_issues"]) == 0
