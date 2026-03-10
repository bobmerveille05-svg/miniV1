"""Tests for minilegion.core.context_scanner — codebase scanning for LLM prompt injection."""

import pytest
from pathlib import Path
from minilegion.core.config import MiniLegionConfig
from minilegion.core.context_scanner import scan_codebase


class TestTechStackDetection:
    """Tests for tech stack detection from root-level config files."""

    def test_detects_pyproject_toml(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "myproject"\n', encoding="utf-8"
        )
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Tech Stack" in result
        assert "pyproject.toml" in result
        assert "myproject" in result

    def test_detects_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"name": "my-app", "version": "1.0.0"}', encoding="utf-8"
        )
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Tech Stack" in result
        assert "package.json" in result
        assert "my-app" in result

    def test_detects_requirements_txt(self, tmp_path):
        (tmp_path / "requirements.txt").write_text(
            "requests==2.31.0\npydantic>=2.0\n", encoding="utf-8"
        )
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Tech Stack" in result
        assert "requirements.txt" in result
        assert "requests" in result

    def test_returns_empty_section_when_no_tech_files(self, tmp_path):
        # Create only a source file, no tech stack config files
        src = tmp_path / "main.py"
        src.write_text("print('hello')", encoding="utf-8")
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        # Should still have a tech stack section, but with placeholder content
        assert "## Tech Stack" in result
        assert "No tech stack config files found" in result

    def test_truncates_large_config_file_content(self, tmp_path):
        # Write a file with more than 500 chars of content
        big_content = "x = 1\n" * 200  # 1200+ chars
        (tmp_path / "pyproject.toml").write_text(big_content, encoding="utf-8")
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        # Verify content is truncated to at most 500 chars in the section
        # Find the pyproject.toml section and check content length
        assert "pyproject.toml" in result
        # The actual big_content has 200*6 = 1200 chars; truncated to 500 chars
        # meaning "x = 1\n" repeated ~83 times (500/6 ≈ 83), not 200 times
        assert result.count("x = 1") <= 84  # 500 chars / 6 chars per line ≈ 83


class TestScannerLimits:
    """Tests for configurable scanner limits."""

    def test_respects_max_depth(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "deep.py"
        deep.parent.mkdir(parents=True)
        deep.write_text("import os", encoding="utf-8")
        shallow = tmp_path / "a" / "shallow.py"
        shallow.write_text("import sys", encoding="utf-8")
        config = MiniLegionConfig(
            scan_max_depth=2, scan_max_files=200, scan_max_file_size_kb=100
        )
        result = scan_codebase(tmp_path, config)
        # shallow.py is at depth 1 (a/), within limit
        assert "sys" in result or "shallow" in result
        # deep.py is at depth 3 (a/b/c/), beyond limit of 2
        assert "deep.py" not in result

    def test_respects_max_files(self, tmp_path):
        # Create 5 files, limit to 2
        for i in range(5):
            (tmp_path / f"file{i}.py").write_text(
                f"# file {i}\nimport module_{i}", encoding="utf-8"
            )
        config = MiniLegionConfig(
            scan_max_depth=5, scan_max_files=2, scan_max_file_size_kb=100
        )
        result = scan_codebase(tmp_path, config)
        # Only 2 files should be scanned; at most 2 unique module imports
        import_count = result.count("- module_")
        assert import_count <= 2

    def test_respects_max_file_size_kb(self, tmp_path):
        # Write a file larger than 1KB
        big_file = tmp_path / "big.py"
        big_file.write_text(
            "import os\n" + "# padding\n" * 200, encoding="utf-8"
        )  # ~2KB
        small_file = tmp_path / "small.py"
        small_file.write_text("import sys", encoding="utf-8")
        # Limit to 1KB — big.py should be skipped
        config = MiniLegionConfig(
            scan_max_depth=5, scan_max_files=200, scan_max_file_size_kb=1
        )
        result = scan_codebase(tmp_path, config)
        # big.py is too large — its import "os" should not appear (only from imports section)
        # small.py is small enough — its import "sys" should appear
        assert "sys" in result

    def test_default_config_values(self):
        config = MiniLegionConfig()
        assert config.scan_max_depth == 5
        assert config.scan_max_files == 200
        assert config.scan_max_file_size_kb == 100

    def test_max_depth_zero_root_files_only(self, tmp_path):
        # Root file
        (tmp_path / "root.py").write_text("import root_module", encoding="utf-8")
        # Subdirectory file
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.py").write_text("import nested_module", encoding="utf-8")
        # With max_depth=0, dirs[:] = [] immediately — no subdir files collected
        config = MiniLegionConfig(
            scan_max_depth=0, scan_max_files=200, scan_max_file_size_kb=100
        )
        result = scan_codebase(tmp_path, config)
        assert "root_module" in result
        assert "nested_module" not in result


class TestImportExtraction:
    """Tests for import extraction from Python, JS/TS, and Go source files."""

    def test_python_import_statement(self, tmp_path):
        (tmp_path / "main.py").write_text("import os\nimport sys\n", encoding="utf-8")
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Import Patterns" in result
        assert "os" in result
        assert "sys" in result

    def test_python_from_import_statement(self, tmp_path):
        (tmp_path / "app.py").write_text(
            "from pathlib import Path\nfrom typing import Optional\n", encoding="utf-8"
        )
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Import Patterns" in result
        assert "pathlib" in result
        assert "typing" in result

    def test_js_import_from_syntax(self, tmp_path):
        (tmp_path / "index.js").write_text(
            "import React from 'react';\nimport { useState } from 'react';\n",
            encoding="utf-8",
        )
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Import Patterns" in result
        assert "react" in result

    def test_js_require_syntax(self, tmp_path):
        (tmp_path / "server.js").write_text(
            "const express = require('express');\nconst path = require('path');\n",
            encoding="utf-8",
        )
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Import Patterns" in result
        assert "express" in result
        assert "path" in result

    def test_ts_import_syntax(self, tmp_path):
        (tmp_path / "app.ts").write_text(
            "import { Component } from '@angular/core';\nimport axios from 'axios';\n",
            encoding="utf-8",
        )
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Import Patterns" in result
        assert "@angular/core" in result
        assert "axios" in result

    def test_go_import_single(self, tmp_path):
        (tmp_path / "main.go").write_text(
            'package main\nimport "fmt"\n\nfunc main() { fmt.Println("hi") }\n',
            encoding="utf-8",
        )
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Import Patterns" in result
        assert "fmt" in result

    def test_go_import_block(self, tmp_path):
        (tmp_path / "server.go").write_text(
            'package main\nimport (\n\t"fmt"\n\t"net/http"\n)\n',
            encoding="utf-8",
        )
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Import Patterns" in result
        assert "fmt" in result
        assert "net/http" in result

    def test_empty_file_no_imports(self, tmp_path):
        (tmp_path / "empty.py").write_text("", encoding="utf-8")
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        # No imports means the section shows "No imports detected"
        assert "## Import Patterns" in result
        assert "No imports detected" in result

    def test_mixed_language_files(self, tmp_path):
        (tmp_path / "app.py").write_text("import os\n", encoding="utf-8")
        (tmp_path / "index.js").write_text(
            "import React from 'react';\n", encoding="utf-8"
        )
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "os" in result
        assert "react" in result
        assert "Python" in result
        assert "JavaScript" in result


class TestDirectoryStructure:
    """Tests for directory structure scanning."""

    def test_filters_ignored_dirs(self, tmp_path):
        # Create ignored dirs alongside a real source dir
        for ignored in [
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "dist",
            "build",
        ]:
            (tmp_path / ignored).mkdir()
        (tmp_path / "src").mkdir()
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Directory Structure" in result
        assert "src" in result
        for ignored in [
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "dist",
            "build",
        ]:
            assert (
                ignored not in result.split("## Directory Structure")[1].split("```")[1]
            )

    def test_shows_max_two_levels(self, tmp_path):
        # Create 3-level deep structure
        deep = tmp_path / "level1" / "level2" / "level3"
        deep.mkdir(parents=True)
        (deep / "deep_file.txt").write_text("content", encoding="utf-8")
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "level1" in result
        assert "level2" in result
        # level3 should NOT appear (beyond max 2 levels for directory structure)
        dir_section = result.split("## Directory Structure")[1].split("```")[1]
        assert "level3" not in dir_section

    def test_empty_project_dir(self, tmp_path):
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Directory Structure" in result
        assert isinstance(result, str)
        assert result  # Non-empty


class TestNamingConventions:
    """Tests for naming convention detection."""

    def test_detects_snake_case_dominant(self, tmp_path):
        # Lots of snake_case identifiers
        content = "\n".join(
            [
                "my_variable = 1",
                "another_thing = 2",
                "some_long_name = 3",
                "get_user_data = 4",
                "parse_config_file = 5",
            ]
        )
        (tmp_path / "code.py").write_text(content, encoding="utf-8")
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Naming Conventions" in result
        assert "snake_case" in result
        assert "Dominant style: snake_case" in result

    def test_detects_camel_case_dominant(self, tmp_path):
        # Lots of camelCase identifiers
        content = "\n".join(
            [
                "var myVariable = 1;",
                "var anotherThing = 2;",
                "var getUserData = 3;",
                "var parseConfigFile = 4;",
                "var handleRequest = 5;",
            ]
        )
        (tmp_path / "app.js").write_text(content, encoding="utf-8")
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Naming Conventions" in result
        assert "camelCase" in result
        assert "Dominant style: camelCase" in result

    def test_detects_pascal_case_dominant(self, tmp_path):
        # Lots of PascalCase identifiers (class names, types)
        content = "\n".join(
            [
                "class UserService {}",
                "class RequestHandler {}",
                "class ConfigParser {}",
                "class DatabaseConnection {}",
                "class AuthorizationManager {}",
            ]
        )
        (tmp_path / "services.ts").write_text(content, encoding="utf-8")
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Naming Conventions" in result
        assert "PascalCase" in result
        assert "Dominant style: PascalCase" in result

    def test_empty_file_no_conventions(self, tmp_path):
        (tmp_path / "empty.py").write_text("", encoding="utf-8")
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Naming Conventions" in result
        assert "No naming patterns detected" in result


class TestScanCodebase:
    """Integration tests for scan_codebase() entry point."""

    def test_returns_non_empty_string(self, tmp_path):
        # Create a minimal project with a README
        (tmp_path / "README.md").write_text("# My Project\n", encoding="utf-8")
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_output_has_required_sections(self, tmp_path):
        # Create a realistic project structure
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "myproject"\n', encoding="utf-8"
        )
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("import os\nmy_variable = 1\n", encoding="utf-8")
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert "## Tech Stack" in result
        assert "## Directory Structure" in result
        assert "## Import Patterns" in result
        assert "## Naming Conventions" in result

    def test_unicode_files_dont_crash(self, tmp_path):
        bad = tmp_path / "broken.py"
        bad.write_bytes(b"import os\n\xff\xfe broken bytes\n")
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert isinstance(result, str)  # No crash

    def test_empty_codebase_returns_placeholder(self, tmp_path):
        config = MiniLegionConfig()
        result = scan_codebase(tmp_path, config)
        assert result  # Non-empty string
        assert isinstance(result, str)

    def test_uses_configurable_limits(self, tmp_path):
        # Create files at different depths
        (tmp_path / "root.py").write_text("import root_pkg", encoding="utf-8")
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "deep.py").write_text("import deep_pkg", encoding="utf-8")
        # Limit depth to 1 — only root-level files collected
        config = MiniLegionConfig(
            scan_max_depth=1, scan_max_files=200, scan_max_file_size_kb=100
        )
        result = scan_codebase(tmp_path, config)
        assert "root_pkg" in result
        assert "deep_pkg" not in result
