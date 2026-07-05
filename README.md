# Modular Pytest & Doc Gen

A highly modular tool for automatically generating comprehensive pytest suites and context-aware docstrings using syntax tree parsing and Large Language Model (LLM) prompts.

## Overview

`modular-pytest-gen` scans your Python source files, extracts structural metadata (functions, global constants, custom exceptions), and formulates highly targeted context prompts for LLMs. 

The architecture is built around a shared intelligence pipeline, powering two distinct capabilities:

1. **Automated Test Generation:** Generates robust, isolated unit tests for functional programming paradigms using standard Abstract Syntax Tree (AST) extraction. Includes autonomous multi-attempt self-healing mechanisms.
2. **Context-Aware Docstring Generation (Roadmap):** Injects highly specific, domain-accurate docstrings directly into your source code using a Concrete Syntax Tree (CST) and a bottom-up graph resolution strategy.

---

## ⚠️ Architectural Disclaimers & Known Limitations

Before deploying this tool in CI/CD or across legacy codebases, it is critical to understand the boundaries of LLM-driven code generation.

### 1. Functional Scope Limitation
Currently, the test generation engine **only operates on top-level functions**. It does not parse, mock, or generate tests for Object-Oriented paradigms (class definitions, stateful methods, or `@classmethod`/`@staticmethod` structures). Repositories heavily reliant on mutable class states will see limited coverage. This is mainly due to the context restrctions of the LLMs used for the tests. 

### 2. The "Scientific Computing" Vulnerability
If your codebase involves complex mathematics, geometry, probability, or strict numerical tolerances, expect a high failure rate (~50%) on initial generation runs. 
* **Input Hallucination:** LLMs struggle to generate valid complex data structures natively. For example, if a function requires an SE(3) transformation matrix, the LLM will likely generate a 4x4 matrix of random floats that fails mathematical orthogonality preconditions, causing the test to crash before the assertion.
* **Floating-Point Assertions:** LLMs frequently attempt exact `==` assertions on floating-point arithmetic rather than using `pytest.approx()`, leading to brittle tests.
* **Stochastic Flakiness:** Functions involving random distributions (e.g., Monte Carlo simulations, LHS sampling) often receive deterministic assertions that fail randomly. 

### 3. Test Generation is Not a TDD Replacement
While automated test generation is a powerful utility for bootstrapping legacy codebases under test coverage, it is not Test-Driven Development (TDD). An LLM analyzing written code writes a test asserting that the code *does exactly what it currently does*, not what it *should* do. Rigorously review generated assertions to ensure they aren't just cementing existing bugs into your test suite.

### 4. Version Control is Mandatory for Autodoc
The `autodoc` pipeline modifies your source code in place. Despite using CST for safe mutation, this tool should **never** be run on a repository with uncommitted changes. Always isolate generation runs to a clean Git branch to review and revert the LLM's additions safely.

---

## 🚀 The Roadmap: Advanced Features

### 1. Object-Oriented Test Generation
Expanding the AST parser to handle class structures, properly mocking `self` states, initializing complex objects, and handling inheritance chains for robust method testing:
* A complete dummy python project is needed in the tests to serve as a basis to verify capabilities and limitations.

### 2. Complex Fixture Injection & Domain Context
To combat the "Scientific Computing" vulnerability, future versions will allow users to define strict data-generation fixtures (e.g., `generate_valid_rotation_matrix()`) that the LLM is instructed to use, preventing input precondition failures.
* Implement a "Constraint-Aware Prompting" layer where the configuration file can map specific modules to specific "Valid Input Generators."
* Replace the LLM's default assert generation with a template-based system for common scientific assertions (pytest.approx, matrix shape validation, distribution range checks).
* Implement a "Critic" loop where the tool runs the test, observes a failure, and provides the entire stack trace and the function signature back to the LLM to perform a root-cause analysis before attempting the next iteration.

### 3. Bottom-Up DAG Context Compression (Docstrings)
To prevent complex components from receiving generic, superficial docstrings, the tool will implement a **Directed Acyclic Graph (DAG) Toposort**.
* The parser will map the dependency tree of your project.
* It will generate docstrings for "leaf nodes" (elementary functions) first.
* When evaluating a parent function/class, the tool will inject the *newly generated docstrings of its dependencies* into the LLM's context.
* **The Result:** The LLM compresses deep architectural context into the prompt without exceeding token limits. Cycle-breaking algorithms will ensure circular imports do not hang the pipeline.

### 4. Non-Destructive Code Mutation (`libcst`)
Standard `ast` modules destroy inline comments and force standard formatting when writing code back to disk. The upcoming `injector.py` engine utilizes a **Concrete Syntax Tree (`libcst`)**, guaranteeing that when a generated docstring is written into a source file, every space, newline, and inline comment remains exactly as originally typed.

---

## Configuration

The tool defaults to looking for a dedicated configuration file named `autotest.toml` (or `autodoc.toml` for documentation runs) in the root of your target project. You can also embed these configurations inside your standard `pyproject.toml`.

### Dedicated File `autotest.toml` (Recommended)

```toml
# Core Settings
source_root = "src"
import_prefix = "my_package"
global_context = [
    "src/my_package/constants.py",
    "src/my_package/exceptions.py"
]
custom_instructions = "Use pytest.approx for all float comparisons. Use patch instead of Mock."

# Test Generation Specifics
[layout]
strategy = "external" 
structure = "nested"  
test_root = "tests"

[discovery]
respect_dunder_all = true
exclude_patterns = ["*__init__.py", "*test_*.py", "legacy_modules"]
exclude_functions = ["heavy_database_call"]

# LLM Provider Setup
[llm]
provider = "mistral"
model = "codestral-latest"
host = "[https://api.mistral.ai](https://api.mistral.ai)"
structured = true

# --- ROADMAP: Upcoming Docstring Settings ---
[autodoc]
style = "google"           # Options: google, numpy, sphinx
overwrite_existing = false # Whether to replace existing manual docstrings
enforce_git_clean = true   # Fail run if uncommitted changes are detected
```

### Option 2: `pyproject.toml`

If you prefer to keep your repository clean and consolidate tool configurations, you can embed the settings inside your target project's `pyproject.toml` under the `[tool.modular_pytest_gen]` block.
