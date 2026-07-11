import sys
from pathlib import Path

import pytest

from modular_pytest_gen.config import ProjectConfig, load_config

try:
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
    HAS_TOML_PARSER = True
except ImportError:
    HAS_TOML_PARSER = False
pytestmark = pytest.mark.skipif(
    not HAS_TOML_PARSER,
    reason="A TOML parser (tomllib or tomli) is required for these tests",
)


def test_load_config_defaults(tmp_path):
    non_existent_file = tmp_path / "does_not_exist.toml"
    config = load_config(non_existent_file)
    assert isinstance(config, ProjectConfig)
    assert config.source_root == "src"
    assert config.layout.strategy == "external"
    assert config.discovery.respect_dunder_all is True
    assert config.discovery.exclude_patterns == ["*__init__.py", "*test_*.py"]


def test_load_config_with_empty_tool_section(tmp_path):
    toml_content = '\n    [tool.some_other_tool]\n    setting = "value"\n    '
    file_path = tmp_path / "pyproject.toml"
    file_path.write_text(toml_content, encoding="utf-8")
    config = load_config(file_path)
    assert config.source_root == "src"


def test_load_config_full_parsing(tmp_path):
    toml_content = '\n    [tool.modular_pytest_gen]\n    source_root = "app"\n    import_prefix = "my_package"\n    global_context = [\n        "app/my_package/constants.py"\n    ]\n\n    [tool.modular_pytest_gen.layout]\n    strategy = "adjacent"\n    structure = "flat"\n    test_root = "test_dir"\n\n    [tool.modular_pytest_gen.discovery]\n    respect_dunder_all = false\n    exclude_patterns = ["*__init__.py"]\n    exclude_functions = ["heavy_calc"]\n    '
    file_path = tmp_path / "pyproject.toml"
    file_path.write_text(toml_content, encoding="utf-8")
    config = load_config(file_path)
    assert config.source_root == "app"
    assert config.import_prefix == "my_package"
    assert config.global_context == ["app/my_package/constants.py"]
    assert config.layout.strategy == "adjacent"
    assert config.layout.structure == "flat"
    assert config.layout.test_root == "test_dir"
    assert config.discovery.respect_dunder_all is False
    assert config.discovery.exclude_patterns == ["*__init__.py"]
    assert config.discovery.exclude_functions == ["heavy_calc"]


def test_load_config_invalid_toml(tmp_path):
    toml_content = "\n    [bad_toml\n    missing_bracket = true\n    "
    file_path = tmp_path / "autotest.toml"
    file_path.write_text(toml_content, encoding="utf-8")
    with pytest.raises(ValueError, match="Failed to parse TOML file"):
        load_config(file_path)


def test_load_config_dedicated_file_root_namespace(tmp_path):
    toml_content = '\n    source_root = "custom_src"\n    import_prefix = "custom_pkg"\n\n    [layout]\n    strategy = "adjacent"\n    structure = "flat"\n    '
    file_path = tmp_path / "autotest.toml"
    file_path.write_text(toml_content, encoding="utf-8")
    config = load_config(file_path)
    assert config.source_root == "custom_src"
    assert config.import_prefix == "custom_pkg"
    assert config.layout.strategy == "adjacent"
