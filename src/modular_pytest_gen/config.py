import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


@dataclass
class TestGenerationLayoutConfig:
    r"""
    Configure test generation layout strategy.
    
    Defines the directory structure and granularity for generated test
    files.
    
    Parameters
    ----------
    strategy : {'external', 'adjacent'}, optional
        The directory layout strategy. Default is 'external'.
    structure : {'nested', 'flat'}, optional
        The nesting strategy for test files. Default is 'nested'.
    test_root : str, optional
        The root directory for test files. Default is 'tests'.
    granularity : {'function', 'class', 'module'}, optional
        The granularity level for test generation. Default is 'function'.
    """

    strategy: Literal["external", "adjacent"] = "external"
    structure: Literal["nested", "flat"] = "nested"
    test_root: str = "tests"
    granularity: Literal["function", "class", "module"] = "function"


@dataclass
class DiscoveryConfig:
    r"""
    Configure test discovery and generation behavior.
    
    The DiscoveryConfig class encapsulates settings that control how the
    AST scanner identifies and processes code elements for test generation.
    It allows fine-grained control over which modules, classes, and
    functions are included or excluded from the test generation process.
    
    Parameters
    ----------
    respect_dunder_all : bool, optional
        Whether to respect the `__all__` attribute in modules when
        determining which names to include. Default is True.
    exclude_patterns : List[str], optional
        Glob patterns for files or directories to exclude from test
        generation. Default is ['*__init__.py', 'build', 'tests',
        '*test_*.py'].
    exclude_nodes : List[str], optional
        Names of functions to exclude from test generation. Default is [].
    include_classes : bool, optional
        Whether to include classes in the test generation process. Default
        is False.
    max_class_lines : int, optional
        Maximum number of lines a class can have to be included in test
        generation. Default is 300.
    
    See Also
    --------
    ast_scanner :
        The module responsible for scanning and parsing the AST of Python
        code.
    test_generator :
        The module responsible for generating unit tests based on the
        discovered code elements.
    """

    respect_dunder_all: bool = True
    exclude_patterns: List[str] = field(
        default_factory=lambda: ["*__init__.py", "build", "tests", "*test_*.py"]
    )
    exclude_nodes: List[str] = field(default_factory=list)
    include_classes: bool = False
    max_class_lines: int = 300


@dataclass
class LLMConfig:
    r"""
    Configure the LLM provider and model.
    
    This class encapsulates the configuration settings for the LLM
    provider, including the model name, host URL, and whether structured
    output is enabled.
    
    Parameters
    ----------
    provider : {'mistral', 'ollama'}, optional
        The LLM provider to use. Default is mistral.
    model : str, optional
        The name of the model to use. Default is codestral-latest.
    host : str, optional
        The host URL for the LLM provider. Default is
        https://api.mistral.ai.
    structured : bool, optional
        Whether to enable structured output. Default is False.
    """

    provider: Literal["mistral", "ollama"] = "mistral"
    model: str = "codestral-latest"
    host: str = "https://api.mistral.ai"
    structured: bool = False


@dataclass
class ProjectConfig:
    r"""
    Configure the project settings for test generation.
    
    The ProjectConfig class encapsulates the configuration settings for the
    test generation process.
    
    Parameters
    ----------
    source_root : str, optional
        The root directory of the source code.
    import_prefix : str, optional
        The prefix for imports.
    global_context : List[str], optional
        A list of global context strings.
    custom_instructions : str, optional
        Custom instructions for the test generation process.
    layout : TestGenerationLayoutConfig, optional
        The layout configuration for test generation.
    discovery : DiscoveryConfig, optional
        The discovery configuration for test generation.
    llm : LLMConfig, optional
        The LLM configuration for test generation.
    
    See Also
    --------
    modular_pytest_gen.DiscoveryConfig :
        Configure test discovery and generation behavior.
    modular_pytest_gen.LLMConfig :
        Configure the LLM provider and model.
    modular_pytest_gen.TestGenerationLayoutConfig :
        Configure test generation layout strategy.
    """

    source_root: str = "src"
    import_prefix: str = ""
    global_context: List[str] = field(default_factory=list)
    custom_instructions: str = ""
    layout: TestGenerationLayoutConfig = field(
        default_factory=TestGenerationLayoutConfig
    )
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)


def load_config(config_path: Path | str = "autotest.toml") -> ProjectConfig:
    r"""
    Load project configuration from a TOML file.
    
    Parameters
    ----------
    config_path : Path | str, optional
        Path to the TOML configuration file. Default is 'autotest.toml'.
    
    Returns
    -------
    ProjectConfig
        The parsed project configuration.
    
        If the file does not exist or is empty, returns a default
        configuration.
    
    Raises
    ------
    ImportError
        The 'tomli' library is required to parse TOML files on Python <
        3.11.
    ValueError
        If the TOML file cannot be parsed.
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
    layout = TestGenerationLayoutConfig(
        strategy=layout_data.get("strategy", "external"),
        structure=layout_data.get("structure", "nested"),
        test_root=layout_data.get("test_root", "tests"),
        granularity=layout_data.get("granularity", "function"),
    )
    discovery = DiscoveryConfig(
        respect_dunder_all=discovery_data.get("respect_dunder_all", True),
        exclude_patterns=discovery_data.get(
            "exclude_patterns", ["*__init__.py", "*test_*.py"]
        ),
        exclude_nodes=discovery_data.get("exclude_nodes", []),
        include_classes=discovery_data.get("include_classes", False),
        max_class_lines=discovery_data.get("max_class_lines", 300),
    )
    llm_data = tool_data.get("llm", {})
    llm = LLMConfig(
        provider=llm_data.get("provider", "mistral"),
        model=llm_data.get("model", "codestral-latest"),
        host=llm_data.get("host", "https://api.mistral.ai"),
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
