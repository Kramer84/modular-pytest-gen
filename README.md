# Modular Pytest & Doc Gen

An autonomous, AST-aware LLM pipeline for generating self-healing unit tests and NumPy-compliant docstrings. 

Unlike standard autocomplete extensions, this tool utilizes a closed-loop validation system: it statically parses your repository, maps local context and structural metadata without executing your code, handles generation using local (Ollama) or remote (Mistral) models, and actively runs the outputs to self-heal code errors before final integration.

---

## ⚠️ Architectural Reality: What Has Been Delivered

The roadmap from earlier iterations has been entirely built out and implemented. Below is the precise state of the engine's capabilities, along with critical operational realities you must acknowledge before executing it.

### 1. Object-Oriented Test Generation & Discovery
The limitation to top-level functional paradigms has been resolved. The AST scanner natively surfaces class structures, methods, constructor logic (`__init__`), and custom exceptions. When targeting a stateful method, the prompt orchestrator automatically embeds the parent class docstring and initialization signatures to give the LLM full runtime context.

### 2. The "Scientific Computing" Critic Loop (Self-Healing)
To solve the high failure rates seen in scientific and mathematical assertions, a **closed-loop validation mechanism** is fully operational.
* **Execution Feedback Loop:** The tool executes generated tests inside a runtime-monitored subprocess. If a test fails, a `CRITIC PROTOCOL` is initiated. 
* **Mandatory Root-Cause Analysis:** The failing traceback is piped back to the model. The model is blocked from writing code until it outputs a structural root-cause analysis explaining exactly which assumption failed (e.g., matrix dimensionality mismatches or floating-point comparison issues).
* **Dynamic Temperature Scaling:** Each retry step increments the temperature setting dynamically ($0.025 \rightarrow 0.7$) to force creative code alternatives and break infinite correction loops.

### 3. Bottom-Up DAG Context Compression (Autodoc)
The documentation engine is entirely driven by a **Topological Directed Acyclic Graph (DAG)** via `graphlib.TopologicalSorter`.
* The repository is parsed into an abstract dependency graph.
* Leaf-node utilities and functions are documented first.
* As the execution path moves up to parent orchestrators, the *newly generated docstrings of those internal leaf dependencies* are dynamically pulled from a cache and packed directly into the parent's prompt window.
* **The Result:** The model leverages contextual compression, knowing the exact documented behavior of its structural dependencies without breaking prompt token ceilings.

### 4. Non-Destructive Code Mutation (`libcst`)
The file modification pipeline uses **Concrete Syntax Tree (`libcst`)** mutation rather than destructive standard `ast` parsing. When injecting generated docstrings, the engine modifies only the exact docstring nodes, completely preserving every line break, indentation spacing, and raw inline comment across your source files.

---

## Security Warning ⚠️

**This engine executes LLM-generated code locally on your machine.** 
During the `autotest run` process, the `TestValidator` spawns your local python interpreter to run `pytest` over raw, unverified AI outputs. While a strict 10-second subprocess timeout is enforced to catch infinite loops or hanging operations, **the runtime execution environment is not sandboxed**. 

Do not execute this library on production servers or environments with sensitive local credentials. Run test generation workflows within a Docker container, an isolated virtual machine, or disposable CI/CD runners.

---

## Configuration (`autotest.toml`)

The configuration file allows granular control over discovery, layout strategies, and model selection. You can use a dedicated `autotest.toml` file or embed a `[tool.modular_pytest_gen]` block directly inside your project's `pyproject.toml`.

```toml
source_root = "src"
import_prefix = "my_package"
global_context = [
    "src/my_package/constants.py",
    "src/my_package/exceptions.py"
]
custom_instructions = "Use pytest.approx for float comparison operations."

[layout]
strategy = "external"   # Options: 'external' or 'adjacent'
structure = "nested"    # Options: 'nested' or 'flat'
test_root = "tests"
granularity = "module"  # Options: 'function', 'class', or 'module'

[discovery]
respect_dunder_all = true
include_classes = true
max_class_lines = 300
exclude_patterns = [
    "*__init__.py",
    "build",
    "tests",
    "*test_*.py"
]
exclude_functions = []

[llm]
provider = "ollama"     # Options: 'ollama' or 'mistral'
model = "qwen2.5-coder:7b-instruct-q8_0"
host = "http://localhost:11434"
structured = false       # Enforces schema validation using model function tool calling

```

---

## Core Command Architecture

The system is managed through a clear hierarchy of subcommands via Typer:

### `autotest init`

Scans your system architecture to infer your `import_prefix` and `source_root` values out of an existing `pyproject.toml` file, writing an optimized `autotest.toml` dynamically.

### `autotest run`

Begins the evaluation sequence. Statically harvests source modules, references global constraints, generates prompt matrices, evaluates tests within the critic validation loop, and writes successfully verified output items into an isolated `.tmp` workspace.

### `autotest analyze`

Provides an assessment of the temporary generation workspace. Employs varying verbosity flags (`-v`, `-vv`) to generate structural reports covering error distributions, system tracebacks, and model "struggle index" logs.

### `autotest merge`

Performs an AST-aware consolidation pass, moving validated scripts from the `.tmp` workspace into your permanent `tests/` tree. It isolates individual functions or safely appends new tests to existing test files without corrupting human-written test definitions.

### `autotest autodoc`

Invokes the bottom-up topological graph processing tree to generate or clean repository documentation. Natively builds structured, NumPy-style docstrings using a secondary model pipeline pass to compress headers to under 70 characters.

### `autotest clean`

Removes all temporary staging files, validation directories, and dry-run prompt files to restore a clean directory tree status.

## 🐕 Dogfooding: Self-Documentation Performance

The `autodoc` pipeline has been successfully validated by running it recursively against its own engine source modules. 

### Core Benchmarks & Behaviors Observed
* **Structural Integration:** The LibCST `AutodocInjector` successfully navigated complex class structural boundaries, maintaining absolute format conservation across whitespace, indent parameters, and inline developer notes.
* **Constant Targeting via CST:** The module correctly targeted free-floating assignment nodes within `templates.py`, positioning raw string literals directly below assignments to simulate clean module-level metadata constants.

### Critical Extraction Nuances (Review Required)
While the pipeline accelerates code understanding, the underlying model demonstrates a structural bias toward **Defensive Over-Documentation**:
* **Hallucinated Exception Layers:** The model regularly generates `Raises` documentation blocks (e.g., `TypeError`, `KeyError`) for structural checks it assumes *should* exist, even when the implementation uses safe fallbacks, typing coercions, or empty returns (`return ""`).
* **Schema Redundancy:** Despite explicit systemic prompt parameters forbidding default values inside semantic parameters, models occasionally duplicate default markers inline rather than allowing the automatic formatting builders to parse them cleanly.

Always perform a validation audit of the `Raises` blocks in a clean feature branch before completing an overwrite pass.