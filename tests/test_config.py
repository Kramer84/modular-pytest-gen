import pytest
import sys
from pathlib import Path
from modular_pytest_gen.config import load_config, ProjectConfig

# Skip tests if running on < 3.11 and tomli isn't installed in the test environment
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
    reason="A TOML parser (tomllib or tomli) is required for these tests"
)

def test_load_config_defaults(tmp_path):
    # Pass a path that doesn't exist to ensure defaults are returned cleanly
    non_existent_file = tmp_path / "does_not_exist.toml"
    config = load_config(non_existent_file)
    
    assert isinstance(config, ProjectConfig)
    assert config.source_root == "src"
    assert config.layout.strategy == "external"
    assert config.discovery.respect_dunder_all is True
    # Updated to match the new defaults established in config.py
    assert config.discovery.exclude_patterns == ["*__init__.py", "*test_*.py"]

def test_load_config_with_empty_tool_section(tmp_path):
    toml_content = """
    [tool.some_other_tool]
    setting = "value"
    """
    file_path = tmp_path / "pyproject.toml"
    file_path.write_text(toml_content, encoding="utf-8")
    
    config = load_config(file_path)
    # Should safely return defaults without crashing on missing nested dicts
    assert config.source_root == "src"

def test_load_config_full_parsing(tmp_path):
    toml_content = """
    [tool.modular_pytest_gen]
    source_root = "app"
    import_prefix = "my_package"
    global_context = [
        "app/my_package/constants.py"
    ]

    [tool.modular_pytest_gen.layout]
    strategy = "adjacent"
    structure = "flat"
    test_root = "test_dir"

    [tool.modular_pytest_gen.discovery]
    respect_dunder_all = false
    exclude_patterns = ["*__init__.py"]
    exclude_functions = ["heavy_calc"]
    """
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
    toml_content = """
    [tool.bad_toml
    missing_bracket = true
    """
    file_path = tmp_path / "pyproject.toml"
    file_path.write_text(toml_content, encoding="utf-8")
    
    with pytest.raises(ValueError, match="Failed to parse TOML file"):
        load_config(file_path)
        
def test_load_config_dedicated_file_root_namespace(tmp_path):
    # Simulates a dedicated modular_pytest_gen.toml file where the config
    # is at the root level, not nested under [tool.modular_pytest_gen]
    toml_content = """
    source_root = "custom_src"
    import_prefix = "custom_pkg"
    
    [layout]
    strategy = "adjacent"
    structure = "flat"
    """
    file_path = tmp_path / "modular_pytest_gen.toml"
    file_path.write_text(toml_content, encoding="utf-8")
    
    from modular_pytest_gen.config import load_config
    config = load_config(file_path)
    
    # If this fails, the parser is incorrectly forcing [tool.modular_pytest_gen]
    assert config.source_root == "custom_src"
    assert config.import_prefix == "custom_pkg"
    assert config.layout.strategy == "adjacent"