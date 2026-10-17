"""Diagnostic analysis for C++23 compiler and CMake errors in GNU Radio 4."""

from __future__ import annotations

import re
from typing import Any, Dict, List


class CompilerDiagnostics:
    """Parses and diagnoses GCC/Clang C++23 compiler and CMake errors for GNU Radio 4."""

    DIAGNOSTIC_RULES = [
        {
            "id": "GR4_BLOCKLIKE_CONCEPT_FAILURE",
            "pattern": r"(constraints not satisfied for.*BlockLike|concept.*gr::BlockLike.*was not satisfied|static_assert failed.*BlockLike)",
            "title": "C++23 Concept Failure: gr::BlockLike Constraints Not Satisfied",
            "explanation": (
                "The block does not satisfy the `gr::BlockLike` concept required by GNU Radio 4. "
                "In GR4, blocks are value-like or structural types that must have publicly accessible "
                "input/output ports (`gr::PortIn<T>`, `gr::PortOut<T>`) and a valid processing function "
                "such as `processBulk`."
            ),
            "remedy": (
                "Ensure your block satisfies:\n"
                "1. Has public ports: `gr::PortIn<TIn> in;` and `gr::PortOut<TOut> out;`\n"
                "2. Implements `gr::work::Status processBulk(const gr::ConsumableSpan<TIn>& in_span, gr::PublishableSpan<TOut>& out_span)`\n"
                "3. Is default-constructible and copy/move constructible\n"
                "4. Check that all template parameters have default types or are properly instantiated in `static_assert(gr::BlockLike<MyBlock<>>);`"
            ),
        },
        {
            "id": "GR4_PROCESS_BULK_SIGNATURE_MISMATCH",
            "pattern": r"(processBulk.*does not match|no matching function for call to.*processBulk|ConsumableSpan|PublishableSpan)",
            "title": "Invalid processBulk Signature",
            "explanation": (
                "The `processBulk` member function signature does not match GNU Radio 4 requirements. "
                "GR4 uses `gr::ConsumableSpan<T>` for inputs and `gr::PublishableSpan<T>` for outputs."
            ),
            "remedy": (
                "Define processBulk as follows:\n"
                "```cpp\n"
                "gr::work::Status processBulk(const gr::ConsumableSpan<TIn>& in_span,\n"
                "                             gr::PublishableSpan<TOut>& out_span) {\n"
                "    const size_t n = std::min(in_span.size(), out_span.size());\n"
                "    for (size_t i = 0; i < n; ++i) { out_span[i] = ...; }\n"
                "    return gr::work::Status::OK;\n"
                "}\n"
                "```"
            ),
        },
        {
            "id": "GR4_MISSING_HEADER",
            "pattern": r"(gnuradio-4\.0/Block\.hpp.*No such file|fatal error:.*Block\.hpp|'PortIn' was not declared in this scope)",
            "title": "Missing GNU Radio 4 SDK Headers",
            "explanation": (
                "The compiler cannot find `<gnuradio-4.0/Block.hpp>` or its related headers. "
                "Either the include path is missing or GNU Radio 4 is not installed at the expected prefix."
            ),
            "remedy": (
                "1. Add `#include <gnuradio-4.0/Block.hpp>` to your header.\n"
                "2. In CMakeLists.txt, ensure you link against `gnuradio4::gnuradio-core`.\n"
                "3. Ensure `CMAKE_PREFIX_PATH` points to your GR4 install prefix (e.g. `${CMAKE_SOURCE_DIR}/install`)."
            ),
        },
        {
            "id": "GR4_MISSING_COMPLEX_HEADER",
            "pattern": r"('complex' in namespace 'std' does not name a template type|no member named 'polar' in namespace 'std')",
            "title": "Missing <complex> Header",
            "explanation": (
                "Standard complex number types (`std::complex<float>`, `std::polar`) were referenced "
                "without including `<complex>`."
            ),
            "remedy": "Add `#include <complex>` at the top of your header or implementation file.",
        },
        {
            "id": "CMAKE_FIND_PACKAGE_GNURADIO4_FAILED",
            "pattern": r"(Could not find a package configuration file provided by \"gnuradio4\"|find_package\(gnuradio4\))",
            "title": "CMake Cannot Find GNU Radio 4 Package",
            "explanation": (
                "CMake's `find_package(gnuradio4 CONFIG REQUIRED)` failed because `gnuradio4Config.cmake` "
                "was not found on `CMAKE_PREFIX_PATH`."
            ),
            "remedy": (
                "Pass `-DCMAKE_PREFIX_PATH=<path_to_install>` when running cmake, or source "
                "`build/dev/activate.sh` before configuring."
            ),
        },
        {
            "id": "CXX_STANDARD_LESS_THAN_23",
            "pattern": r"(requires C\+\+23|std=c\+\+23|expected C\+\+23 or later)",
            "title": "C++ Standard Below C++23",
            "explanation": (
                "GNU Radio 4 strictly requires C++23. Compilation failed because an older C++ standard "
                "was selected."
            ),
            "remedy": (
                "In CMakeLists.txt set:\n"
                "```cmake\n"
                "set(CMAKE_CXX_STANDARD 23)\n"
                "set(CMAKE_CXX_STANDARD_REQUIRED ON)\n"
                "```\n"
                "And ensure GCC 14+ or Clang 20+ is used."
            ),
        },
    ]

    @classmethod
    def diagnose(cls, error_log: str) -> Dict[str, Any]:
        """Analyze an error log and return structured diagnosis and remedies."""
        if not error_log or not error_log.strip():
            return {
                "matched_issues": [],
                "summary": "No compiler or build error logs provided.",
                "has_recognized_patterns": False,
            }

        matched: List[Dict[str, str]] = []
        for rule in cls.DIAGNOSTIC_RULES:
            if re.search(rule["pattern"], error_log, re.IGNORECASE):
                matched.append(
                    {
                        "id": rule["id"],
                        "title": rule["title"],
                        "explanation": rule["explanation"],
                        "remedy": rule["remedy"],
                    }
                )

        # Extract file locations and line numbers if present
        locations = []
        for match in re.finditer(
            r"([a-zA-Z0-9_\-\./\\:]+):(\d+):(\d+):\s+(error|fatal error):\s+(.*)",
            error_log,
        ):
            locations.append(
                {
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "column": int(match.group(3)),
                    "severity": match.group(4),
                    "message": match.group(5).strip(),
                }
            )

        return {
            "has_recognized_patterns": len(matched) > 0,
            "matched_issues_count": len(matched),
            "matched_issues": matched,
            "error_locations": locations[:10],  # cap at 10 most relevant
            "summary": (
                f"Identified {len(matched)} known GR4 error patterns and {len(locations)} error locations."
                if matched
                else "No known GR4-specific error patterns identified. Review raw output."
            ),
        }
