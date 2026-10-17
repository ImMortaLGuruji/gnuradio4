"""Build and test orchestration for Out-Of-Tree (OOT) GNU Radio 4 modules."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from gr4_mcp.diagnostics import CompilerDiagnostics
from gr4_mcp.env import GR4Environment


class GR4Builder:
    """Manages configuring, compiling, and testing GNU Radio 4 OOT projects."""

    def __init__(self, env: Optional[GR4Environment] = None) -> None:
        self.env = env or GR4Environment()
        self.cmake_bin = self._find_executable(
            "cmake",
            [
                "C:\\Program Files\\CMake\\bin\\cmake.exe",
                "/usr/bin/cmake",
                "/usr/local/bin/cmake",
            ],
        )
        self.ctest_bin = self._find_executable(
            "ctest",
            [
                "C:\\Program Files\\CMake\\bin\\ctest.exe",
                "/usr/bin/ctest",
                "/usr/local/bin/ctest",
            ],
        )
        self.ninja_bin = self._find_executable(
            "ninja", ["/usr/bin/ninja", "/usr/local/bin/ninja"]
        )

    def _find_executable(self, name: str, candidate_paths: List[str]) -> Optional[str]:
        # 1. Environment override
        env_var = f"{name.upper()}_COMMAND"
        if os.environ.get(env_var):
            return os.environ[env_var]

        # 2. System PATH
        which_path = shutil.which(name)
        if which_path:
            return which_path

        # 3. Known paths
        for path_str in candidate_paths:
            p = Path(path_str)
            if p.exists() and p.is_file():
                return str(p)

        return None

    def build_oot(
        self,
        project_path: str,
        build_type: str = "RelWithAssert",
        clean: bool = False,
        extra_cmake_args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Configure and compile an OOT CMake project against the installed GNU Radio 4 SDK."""
        proj = Path(project_path).resolve()
        if not proj.exists() or not (proj / "CMakeLists.txt").exists():
            return {
                "success": False,
                "error": f"Directory '{project_path}' does not contain a CMakeLists.txt file.",
            }

        if not self.cmake_bin:
            return {
                "success": False,
                "error": "CMake executable not found. Please install CMake 3.27+ or set CMAKE_COMMAND in your environment.",
                "hint": "On Linux/Docker use 'apt install cmake ninja-build', or ensure cmake is on system PATH.",
            }

        build_dir = proj / "build"
        if clean and build_dir.exists():
            shutil.rmtree(build_dir, ignore_errors=True)

        build_dir.mkdir(parents=True, exist_ok=True)
        runtime_env = self.env.get_runtime_env()

        # Build CMake configure arguments
        cmake_args = [
            self.cmake_bin,
            "-S",
            str(proj),
            "-B",
            str(build_dir),
            f"-DCMAKE_BUILD_TYPE={build_type}",
        ]

        if self.env.prefix:
            cmake_args.append(f"-DCMAKE_PREFIX_PATH={self.env.prefix}")

        if self.ninja_bin:
            cmake_args.extend(["-G", "Ninja"])

        if extra_cmake_args:
            cmake_args.extend(extra_cmake_args)

        start_time = time.time()

        # 1. Configure Step
        config_proc = subprocess.run(
            cmake_args,
            cwd=str(proj),
            env=runtime_env,
            capture_output=True,
            text=True,
        )

        if config_proc.returncode != 0:
            duration = time.time() - start_time
            diagnosis = CompilerDiagnostics.diagnose(
                config_proc.stderr + "\n" + config_proc.stdout
            )
            return {
                "success": False,
                "stage": "configure",
                "exit_code": config_proc.returncode,
                "duration_seconds": round(duration, 2),
                "stdout": config_proc.stdout,
                "stderr": config_proc.stderr,
                "diagnosis": diagnosis,
            }

        # 2. Build Step
        build_args = [self.cmake_bin, "--build", str(build_dir)]
        build_proc = subprocess.run(
            build_args,
            cwd=str(proj),
            env=runtime_env,
            capture_output=True,
            text=True,
        )

        duration = time.time() - start_time
        all_output = build_proc.stderr + "\n" + build_proc.stdout

        if build_proc.returncode != 0:
            diagnosis = CompilerDiagnostics.diagnose(all_output)
            return {
                "success": False,
                "stage": "build",
                "exit_code": build_proc.returncode,
                "duration_seconds": round(duration, 2),
                "stdout": build_proc.stdout,
                "stderr": build_proc.stderr,
                "diagnosis": diagnosis,
            }

        return {
            "success": True,
            "stage": "completed",
            "build_dir": str(build_dir),
            "duration_seconds": round(duration, 2),
            "stdout": build_proc.stdout,
        }

    def test_oot(
        self,
        project_path: str,
        test_name: Optional[str] = None,
        timeout_seconds: int = 60,
    ) -> Dict[str, Any]:
        """Run CTest on an existing OOT project build directory."""
        proj = Path(project_path).resolve()
        build_dir = proj / "build"
        if not build_dir.exists():
            return {
                "success": False,
                "error": f"Build directory '{build_dir}' does not exist. Run build_oot first.",
            }

        if not self.ctest_bin:
            return {
                "success": False,
                "error": "CTest executable not found. Please ensure ctest is installed and accessible.",
            }

        ctest_args = [
            self.ctest_bin,
            "--test-dir",
            str(build_dir),
            "--output-on-failure",
        ]

        if test_name:
            ctest_args.extend(["-R", test_name])

        runtime_env = self.env.get_runtime_env()
        start_time = time.time()

        try:
            proc = subprocess.run(
                ctest_args,
                cwd=str(build_dir),
                env=runtime_env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            duration = time.time() - start_time
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"CTest execution timed out after {timeout_seconds} seconds.",
            }

        output = proc.stdout + "\n" + proc.stderr

        # Extract passed / failed counts
        total_tests = 0
        passed_tests = 0
        failed_tests = 0

        match = re.search(
            r"(\d+)% tests passed,\s+(\d+)\s+tests failed out of\s+(\d+)", output
        )
        if match:
            failed_tests = int(match.group(2))
            total_tests = int(match.group(3))
            passed_tests = total_tests - failed_tests
        else:
            match_all_pass = re.search(
                r"100% tests passed,\s+0 tests failed out of\s+(\d+)", output
            )
            if match_all_pass:
                total_tests = int(match_all_pass.group(1))
                passed_tests = total_tests

        diagnosis = None
        if proc.returncode != 0:
            diagnosis = CompilerDiagnostics.diagnose(output)

        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "duration_seconds": round(duration, 2),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "diagnosis": diagnosis,
        }
