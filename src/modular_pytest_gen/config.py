import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


@dataclass
class LayoutConfig:
    strategy: str = "external"
    structure: str = "nested"
    test_root: str = "tests"


@dataclass
class DiscoveryConfig:
    respect_dunder_all: bool = True
    exclude_patterns: List[str] = field(default_factory=lambda: ["*__init__.py", "*test_*.py"])
    exclude_functions: List[str] = field(default_factory=list)


@dataclass
class ProjectConfig:
    source_root: str = "src"
    import_prefix: str = ""
    global_context: List[str] = field(default_factory=list)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)


def load_config(config_path: Path | str = "pyproject.toml") -> ProjectConfig:
    """
    Parses a TOML file and returns a populated ProjectConfig object.
    Can parse both a standard pyproject.toml or a dedicated config file,
    provided the variables are nested under [tool.modular_pytest_gen].
    """
    if tomllib is None:
        raise ImportError(
            "The 'tomli' library is required to parse TOML files on Python < 3.11. "
            "Please install it or upgrade your environment."
        )

    path = Path(config_path)
    if not path.exists():
        # Fall back to defaults if no config file is found
        return ProjectConfig()

    with open(path, "rb") as f:
        try:
            data = tomllib.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse TOML file at {path}: {e}")

    # Standardize extraction: Always look under [tool.modular_pytest_gen]
    tool_data = data.get("tool", {}).get("modular_pytest_gen", {})
    if not tool_data:
        return ProjectConfig()

    layout_data = tool_data.get("layout", {})
    discovery_data = tool_data.get("discovery", {})

    layout = LayoutConfig(
        strategy=layout_data.get("strategy", "external"),
        structure=layout_data.get("structure", "nested"),
        test_root=layout_data.get("test_root", "tests"),
    )

    discovery = DiscoveryConfig(
        respect_dunder_all=discovery_data.get("respect_dunder_all", True),
        exclude_patterns=discovery_data.get("exclude_patterns", ["*__init__.py", "*test_*.py"]),
        exclude_functions=discovery_data.get("exclude_functions", []),
    )

    return ProjectConfig(
        source_root=tool_data.get("source_root", "src"),
        import_prefix=tool_data.get("import_prefix", ""),
        global_context=tool_data.get("global_context", []),
        layout=layout,
        discovery=discovery
    )