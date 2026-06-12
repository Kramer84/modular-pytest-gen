Modular Pytest Gen

A highly modular tool for automatically generating pytest suites using Abstract Syntax Tree (AST) parsing and Large Language Model (LLM) prompts.

Overview

modular-pytest-gen scans your Python source files, extracts structural metadata (functions, classes, custom exceptions, and constants) via AST, and formulates highly targeted context prompts. These prompts are then fed into an LLM to generate robust, isolated unit tests.

⚠️ Architectural Disclaimer

While automated test generation is a powerful utility for bringing legacy codebases under test coverage, it is not a replacement for Test-Driven Development (TDD).

Writing tests after the implementation (post-hoc testing) inherently risks calcifying existing bugs. An LLM analyzing written code will write a test asserting that the code does exactly what it currently does, not necessarily what it should do. For optimal software design and correctness, tests should be written concurrently with, or prior to, the target functions to drive design and clarify intent. Use this tool to bootstrap coverage, but rigorously review the generated assertions.

Configuration

The tool defaults to looking for a dedicated configuration file named autotest.toml in the root of your target project.

Option 1: Dedicated File autotest.toml (Recommended for Development)

Create a file named autotest.toml in the root of the project you want to test. Because the file is dedicated to this tool, you do not need to nest the configuration under a [tool] namespace.

# autotest.toml
source_root = "src"
import_prefix = "my_package"
global_context = [
    "src/my_package/constants.py",
    "src/my_package/exceptions.py"
]

[layout]
strategy = "external" 
structure = "nested"  
test_root = "tests"

[discovery]
respect_dunder_all = true
exclude_patterns = ["*__init__.py", "*test_*.py"]
exclude_functions = ["heavy_database_call"]


Option 2: pyproject.toml

If you prefer to keep your repository clean and consolidate tool configurations, you can embed the settings inside your target project's pyproject.toml. The parser will automatically adapt and extract the configuration from the standard [tool.modular_pytest_gen] block.

[tool.modular_pytest_gen]
source_root = "src"
import_prefix = "my_package"
# ... layout and discovery tables follow standard TOML nesting
