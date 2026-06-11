Modular Pytest Gen

A highly modular tool for automatically generating pytest suites using Abstract Syntax Tree (AST) parsing and Large Language Model (LLM) prompts.

Overview

modular-pytest-gen scans your Python source files, extracts structural metadata (functions, classes, custom exceptions, and constants) via AST, and formulates highly targeted context prompts. These prompts are then fed into an LLM to generate robust, isolated unit tests.

⚠️ Architectural Disclaimer

While automated test generation is a powerful utility for bringing legacy codebases under test coverage, it is not a replacement for Test-Driven Development (TDD).

Writing tests after the implementation (post-hoc testing) inherently risks calcifying existing bugs. An LLM analyzing written code will write a test asserting that the code does exactly what it currently does, not necessarily what it should do. For optimal software design and correctness, tests should be written concurrently with, or prior to, the target functions to drive design and clarify intent. Use this tool to bootstrap coverage, but rigorously review the generated assertions.

Configuration

The tool requires configuration to understand your project's layout and discovery rules. There are two ways to configure modular-pytest-gen for a target repository:

Option 1: pyproject.toml (Recommended)

Add the configuration block directly into the target project's existing pyproject.toml file. This is the modern Python standard.

[tool.modular_pytest_gen]
source_root = "src"
import_prefix = "my_package"
global_context = [
    "src/my_package/constants.py",
    "src/my_package/exceptions.py"
]

[tool.modular_pytest_gen.layout]
strategy = "external" 
structure = "nested"  
test_root = "tests"

[tool.modular_pytest_gen.discovery]
respect_dunder_all = true
exclude_patterns = ["*__init__.py", "*test_*.py"]
exclude_functions = ["heavy_database_call"]


Option 2: Standalone Template

If you do not want to modify your target's pyproject.toml, you can drop the provided modular_pytest_gen_config.template.toml file into the root of your target project and point the CLI to it. The tool searches for the [tool.modular_pytest_gen] section regardless of the filename.