__version__ = "0.1.0"
from .analyzer import TestRegistryAnalyzer
from .client import BaseLLMClient, MistralClient, OllamaClient, unload_ollama_model
from .config import (
    DiscoveryConfig,
    LLMConfig,
    ProjectConfig,
    TestGenerationLayoutConfig,
    load_config,
)
from .docstring import (
    ClassDocstringSchema,
    ConstantDocstringSchema,
    FunctionDocstringSchema,
    InitMethodDocstringSchema,
    MethodDocstringSchema,
    build_numpy_docstring,
)
from .graph import DependencyGraph
from .injector import AutodocInjector, inject_autodoc
from .layout import LayoutManager
from .merge import TestMerger
from .parser import ModuleParser
from .prompter import PromptBuilder
from .resolver import ImportResolver
from .templates import (
    AUTODOC_GENERATE_USER,
    AUTODOC_SYSTEM_PROMPT,
    AUTODOC_VERIFY_USER,
    CUSTOM_EXCEPTIONS_HEADER,
    ENVIRONMENT_CONTEXT_HEADER,
    GLOBAL_CONSTANTS_HEADER,
    NUMPY_STYLE_GUIDE,
    SYSTEM_PROMPT_STANDARD,
    SYSTEM_PROMPT_STRUCTURED,
    USER_PROMPT_BASE,
    USER_PROMPT_DIRECTIVES,
    USER_PROMPT_DOCSTRING,
    USER_PROMPT_FOOTER,
    USER_PROMPT_HEADER,
    USER_PROMPT_IMPORTS,
    USER_PROMPT_LOCAL_CONTEXT,
    USER_PROMPT_SIGNATURE,
)
from .validator import TestValidator

__all__ = [
    "TestRegistryAnalyzer",
    "BaseLLMClient",
    "MistralClient",
    "OllamaClient",
    "unload_ollama_model",
    "DiscoveryConfig",
    "TestGenerationLayoutConfig",
    "LLMConfig",
    "ProjectConfig",
    "load_config",
    "DeprecationDetail",
    "NumpyDocstringSchema",
    "ParameterDetail",
    "ReturnDetail",
    "SeeAlsoItem",
    "build_numpy_docstring",
    "smart_wrap",
    "DependencyGraph",
    "AutodocInjector",
    "inject_autodoc",
    "LayoutManager",
    "TestMerger",
    "ModuleParser",
    "PromptBuilder",
    "ImportResolver",
    "AUTODOC_GENERATE_USER",
    "AUTODOC_SYSTEM_PROMPT",
    "AUTODOC_VERIFY_USER",
    "CUSTOM_EXCEPTIONS_HEADER",
    "ENVIRONMENT_CONTEXT_HEADER",
    "GLOBAL_CONSTANTS_HEADER",
    "NUMPY_STYLE_GUIDE",
    "SYSTEM_PROMPT_STANDARD",
    "SYSTEM_PROMPT_STRUCTURED",
    "USER_PROMPT_BASE",
    "USER_PROMPT_DIRECTIVES",
    "USER_PROMPT_DOCSTRING",
    "USER_PROMPT_FOOTER",
    "USER_PROMPT_HEADER",
    "USER_PROMPT_IMPORTS",
    "USER_PROMPT_LOCAL_CONTEXT",
    "USER_PROMPT_SIGNATURE",
    "TestValidator",
]
