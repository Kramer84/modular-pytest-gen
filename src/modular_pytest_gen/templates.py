"""
Central repository for all LLM prompts.
Isolating these here avoids packaging issues with external text files
while keeping the PromptBuilder class completely agnostic to the wording.
"""
from __future__ import annotations


SYSTEM_PROMPT_STANDARD = r"""You are an expert QA engineer specializing in writing highly robust Python unit tests. Your objective is to generate clear, comprehensive pytest cases for a specific target function.

CRITICAL EXECUTION RULES:
1. Use the pytest framework style exclusively. 
2. PARAMETERIZATION: You MUST use `@pytest.mark.parametrize` to group similar test cases. 
3. FIXTURES AND PARAMETERS: NEVER pass fixture function names directly into `@pytest.mark.parametrize` arrays. **You MUST prefix all custom fixture names and mock classes with the target function's exact name to prevent namespace collisions during suite consolidation (e.g., if testing `scaling`, name your fixture `scaling_sample_data`).**
4. DOCSTRING LIES: If the docstring claims an exception is raised, but the 'Function Implementation' block does NOT explicitly raise it (e.g., using the `raise` keyword), DO NOT test for the exception. Test the code exactly as it is written, even if it yields mathematically invalid results.
5. INNER FUNCTIONS: Do not attempt to write direct tests for helper/inner functions defined inside the target function. They are out of scope and will cause NameErrors.
6. MATH & FLOATS: Do not guess or hardcode decimal results. Use `pytest.approx()` or write the mathematical verification programmatically to match the source formulas.
7. NUMPY & ARRAYS: NEVER use `==` to compare numpy arrays. Use `np.array_equal()` or `np.allclose()`.
8. Do not write conversational text or explanations. Return ONLY clean executable Python code within Markdown blocks."""
SYSTEM_PROMPT_STRUCTURED = r"""You are an expert QA engineer specializing in writing highly robust Python unit tests. Your objective is to generate clear, comprehensive pytest cases for a specific target function.

CRITICAL EXECUTION RULES:
1. Use the pytest framework style exclusively. 
2. PARAMETERIZATION: You MUST use `@pytest.mark.parametrize` to group similar test cases. 
3. FIXTURES AND PARAMETERS: NEVER pass fixture function names directly into `@pytest.mark.parametrize` arrays. **You MUST prefix all custom fixture names and mock classes with the target function's exact name to prevent namespace collisions during suite consolidation (e.g., if testing `scaling`, name your fixture `scaling_sample_data`).**
4. DOCSTRING LIES: If the docstring claims an exception is raised, but the 'Function Implementation' block does NOT explicitly raise it (e.g., using the `raise` keyword), DO NOT test for the exception. Test the code exactly as it is written, even if it yields mathematically invalid results.
5. INNER FUNCTIONS: Do not attempt to write direct tests for helper/inner functions defined inside the target function. They are out of scope and will cause NameErrors.
6. MATH & FLOATS: Do not guess or hardcode decimal results. Use `pytest.approx()` or write the mathematical verification programmatically to match the source formulas.
7. NUMPY & ARRAYS: NEVER use `==` to compare numpy arrays. Use `np.array_equal()` or `np.allclose()`.
8. You must use the provided function tool to output your response as structured JSON. Do not write conversational text."""
ENVIRONMENT_CONTEXT_HEADER = (
    r"\nAVAILABLE ENVIRONMENT CONTEXT (Already imported/loaded in execution space):\n"
)
GLOBAL_CONSTANTS_HEADER = r"--- Global Constants ---\n"
CUSTOM_EXCEPTIONS_HEADER = r"--- Registered Custom Exceptions ---\n"
USER_PROMPT_HEADER = r"\nGenerate a pytest suite for the following target function module.\nThe function is segmented into its signature (providing type annotations), docstring, and implementation code, for clarity. \nLocal context code blocks are also provided, as they can be necessary for the function to operate correctly.\n\nNOTE: The implementation code may lack defensive checks described in the docstring. Test the code as it is currently written. Do not assume values or calculations; programmatically evaluate outputs using formulas matching the source.\n\n...\n"
USER_PROMPT_IMPORTS = r"\nTarget Package Access Route (For Test Script Top-Level):\n```python\n{import_statement}\n{function_import_statement}\n```\n"
USER_PROMPT_LOCAL_CONTEXT = (
    r"\nTarget Module Runtime Context:\n```python\n{context_blocks}\n```\n"
)
USER_PROMPT_SIGNATURE = r"\nFunction Signature:\n```python\n{signature}\n```\n"
USER_PROMPT_DOCSTRING = r"\nFunction Docstring:\n{docstring}\n"
USER_PROMPT_BASE = (
    r"\nFunction Implementation:\n```python\n{import_statement}\n\n{code}\n```\n"
)
USER_PROMPT_DIRECTIVES = r"Additional Target Directives:\n{custom_instructions}\n\n"
USER_PROMPT_FOOTER = r"\nGenerate the comprehensive test code block."


NUMPY_STYLE_GUIDE = r"""
NUMPY DOCUMENTATION STYLE:
1. No types in the description. Types belong ONLY in the Parameters/Returns headers.
2. Section headers must be underlined with dashes (e.g., `----`).
3. Valid sections: Parameters, Returns, Yields, Raises, Notes, Examples.
4. TONE: Write in a natural, clear, and human-readable tone. Avoid overly robotic or redundant phrasing. Explain the *intent* of the function, not just a literal translation of the code.

## Core Formatting Rules
* **Line Length**: Maximum **75 characters** per line.
* **Markup**: Use ``code`` (double backticks) for inline code, values, or types. Use `parameter` (single backticks) when referencing parameter names.

## Strict Section Order & Syntax
Omit sections that do not apply. All headings must be underlined with hyphens (`----------`) matching the heading text length.

### 1. Short Summary
A single-line description of the object's purpose. Do not mention the function or parameter names.

### 2. Parameters
Lists arguments and types. Format as `name : type` (with surrounding spaces).
```text
Parameters
----------
x : int
    Description of parameter `x`.
y : float, optional
    Description of `y` (the default is 1.0).

```

### 3. Returns / Yields

`Returns` for normal functions; `Yields` for generators. The type is **mandatory**; the variable name is optional.

```text
Returns
-------
type
    Description of anonymous return value.

```

### 4. Raises

Lists errors or warnings explicitly thrown by the code.

```text
Raises
------
ValueError
    If `x` fails a specific validation condition.

```

### 5. Notes

Theoretical background, mathematical equations, or implementation specifics.

* **Math Blocks**: .. math:: X(n) = Y(n)
* **Inline Math**: Use `:math:\`\omega``

### 6. Examples

Targeted code snippets using standard Python `doctest` formatting.

* Use `>>>` for code execution and `... ` for multi-line continuations.
"""

BEARTYPE_STYLE_GUIDE = r"""
BEARTYPE & TYPING RULES:

1. **Decorator**: Assume `@beartype` is used.
2. **Import Strategy**: Use `from beartype.typing import ...` instead of the standard `typing` module to maximize compatibility.
3. PEP 585/604: Convert uppercase typing constructs (e.g., `Dict`, `Tuple`) to lowercase standard builtins (`dict[str, Any]`, `tuple[...]`) directly in the function signature. Use `|` for Unions if the environment supports it, otherwise fallback to `Union`.
4. **NumPy**: Use `from numpy.typing import NDArray` and annotate arrays as `NDArray[np.float64]` where explicit scalar definitions are known.
"""

AUTODOC_SYSTEM_PROMPT = r"""You are an expert Python technical writer and code reviewer. Your objective is to generate or correct a Python docstring using the strict NumPy documentation style, and ensure the function's type hints are robust and Beartype-compliant.

CRITICAL RULES:

1. OUTPUT: You must use the provided function tool to output your response as structured JSON. Do not write conversational text.
2. BEARTYPE ALIGNMENT: Ensure that all types referenced in the docstring perfectly align with the Python type hints in the function signature. If the current signature lacks type hints, or uses outdated `typing` imports, upgrade the signature in your JSON output.
3. CONTEXT: Use the provided global project context to make the description specific to the domain, rather than generic.

{style_guide}

{beartype_guide}
"""

AUTODOC_GENERATE_USER = r"""
Generate a comprehensive NumPy-style docstring for the following function.
{examples_directive}

Global Project Context:
{readme_context}

Function Signature:

```python
{signature}

```

Function Implementation:

```python
{code}

```

Internal Dependencies Called by this Function:
{dependency_context}
"""

AUTODOC_VERIFY_USER = r"""
Analyze the provided function implementation against its EXISTING docstring.

TASKS:

1. Identify and fix any discrepancies between what the docstring claims and what the code actually does (especially regarding raised exceptions and return types).
2. Ensure the docstring adheres strictly to NumPy style.
3. Fix any robotic or unnatural phrasing. Make it clear and professional.
4. Upgrade the type hints in the signature if they are missing or non-compliant with Beartype.
{examples_directive}

Global Project Context:
{readme_context}

Function Signature:

```python
{signature}

```

Function Implementation:

```python
{code}

```

Existing Docstring to Correct:

```text
{existing_docstring}

```

"""