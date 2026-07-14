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
    strategy: Literal["external", "adjacent"] = "external"
    structure: Literal["nested", "flat"] = "nested"
    test_root: str = "tests"
    granularity: Literal["function", "class", "module"] = "function"


@dataclass
class DiscoveryConfig:
    respect_dunder_all: bool = True
    exclude_patterns: List[str] = field(
        default_factory=lambda: ["*__init__.py", "build", "tests", "*test_*.py"]
    )
    exclude_functions: List[str] = field(default_factory=list)
    include_classes: bool = False
    max_class_lines: int = 300


@dataclass
class LLMConfig:
    provider: Literal["ollama", "mistral"] = "ollama"
    model: str = "qwen2.5-coder:7b-instruct-q8_0"
    host: str = "http://localhost:11434"
    structured: bool = False


@dataclass
class ProjectConfig:
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
        exclude_functions=discovery_data.get("exclude_functions", []),
        include_classes=discovery_data.get("include_classes", False),
        max_class_lines=discovery_data.get("max_class_lines", 300),
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
