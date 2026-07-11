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
    """Configuration settings for test file placement and structure.

    Attributes:
        strategy (str): The placement strategy (e.g., 'adjacent', 'external').
        structure (str): The folder structure type (e.g., 'flat', 'nested').
        test_root (str): The directory name where tests are located if using external strategy.
    """

    strategy: str = "external"
    structure: str = "nested"
    test_root: str = "tests"


@dataclass
class DiscoveryConfig:
    """Configuration settings for source file discovery and filtering.

    Attributes:
        respect_dunder_all (bool): Whether to filter discovered files based on __all__ definitions.
        exclude_patterns (List[str]): Glob patterns to exclude during file discovery.
        exclude_functions (List[str]): List of specific function names to ignore during analysis.
    """

    respect_dunder_all: bool = True
    exclude_patterns: List[str] = field(
        default_factory=lambda: ["*__init__.py", "build", "tests", "*test_*.py"]
    )
    exclude_functions: List[str] = field(default_factory=list)


@dataclass
class LLMConfig:
    """Configuration settings for LLM service integration.

    Attributes:
        provider (str): The API provider name (e.g., 'ollama', 'openai').
        model (str): The specific model identifier to use.
        host (str): The endpoint URL for the LLM service.
        structured (bool): Whether to enforce structured output parsing.
    """

    provider: str = "ollama"
    model: str = "qwen2.5-coder:7b-instruct-q8_0"
    host: str = "http://localhost:11434"
    structured: bool = False


@dataclass
class ProjectConfig:
    """Root configuration object containing all project-level settings.

    Attributes:
        source_root (str): The base directory for source code.
        import_prefix (str): Prefix used for relative imports in generated tests.
        global_context (List[str]): Additional context paths or items for the LLM.
        custom_instructions (str): Specific user instructions for test generation.
        layout (LayoutConfig): Nested layout configuration.
        discovery (DiscoveryConfig): Nested discovery configuration.
        llm (LLMConfig): Nested LLM configuration.
    """

    source_root: str = "src"
    import_prefix: str = ""
    global_context: List[str] = field(default_factory=list)
    custom_instructions: str = ""
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)


def load_config(config_path: Path | str = "autotest.toml") -> ProjectConfig:
    """Parses a TOML configuration file into a ProjectConfig object.

    This function attempts to load settings from a specified TOML file. It supports:
    1. A standalone config file (default: 'autotest.toml').
    2. A 'pyproject.toml' file, automatically looking for the [tool.modular_pytest_gen] section.

    Args:
        config_path (Path | str): The path to the configuration file.

    Returns:
        ProjectConfig: A populated configuration object with defaults applied if the file
            is missing or if specific fields are absent.

    Raises:
        ImportError: If the 'tomli' library is missing on Python < 3.11.
        ValueError: If the TOML file is malformed or cannot be parsed.
    """
    if tomllib is None:
        raise ImportError(
            "The 'tomli' library is required to parse TOML files on Python < 3.11."
        )
    path = Path(config_path)
    if not path.exists():
        return ProjectConfig()
    with open(path, "rb") as f:
        try:
            data = tomllib.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse TOML file at {path}: {e}")
    if path.name == "pyproject.toml":
        tool_data = data.get("tool", {}).get("modular_pytest_gen", {})
    else:
        nested = data.get("tool", {}).get("modular_pytest_gen", {})
        tool_data = nested if nested else data
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
        exclude_patterns=discovery_data.get(
            "exclude_patterns", ["*__init__.py", "*test_*.py"]
        ),
        exclude_functions=discovery_data.get("exclude_functions", []),
    )
    llm_data = tool_data.get("llm", {})
    llm = LLMConfig(
        provider=llm_data.get("provider", "ollama"),
        model=llm_data.get("model", "qwen2.5-coder:7b-instruct-q8_0"),
        host=llm_data.get("host", "http://localhost:11434"),
        structured=llm_data.get("structured", False),
    )
    return ProjectConfig(
        source_root=tool_data.get("source_root", "src"),
        import_prefix=tool_data.get("import_prefix", ""),
        global_context=tool_data.get("global_context", []),
        custom_instructions=tool_data.get("custom_instructions", ""),
        layout=layout,
        discovery=discovery,
        llm=llm,
    )
