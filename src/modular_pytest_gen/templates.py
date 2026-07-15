from __future__ import annotations

SYSTEM_PROMPT_STANDARD = """You are an expert QA engineer specializing in writing highly robust Python unit tests. Your objective is to generate clear, comprehensive pytest cases for a specific target function.

CRITICAL EXECUTION RULES:
1. Use the pytest framework style exclusively. 
2. PARAMETERIZATION: You MUST use `@pytest.mark.parametrize` to group similar test cases. 
3. FIXTURES AND PARAMETERS: NEVER pass fixture function names directly into `@pytest.mark.parametrize` arrays. **You MUST prefix all custom fixture names and mock classes with the target function's exact name to prevent namespace collisions during suite consolidation (e.g., if testing `scaling`, name your fixture `scaling_sample_data`).**
4. DOCSTRING LIES: If the docstring claims an exception is raised, but the 'Function Implementation' block does NOT explicitly raise it (e.g., using the `raise` keyword), DO NOT test for the exception. Test the code exactly as it is written, even if it yields mathematically invalid results.
5. INNER FUNCTIONS: Do not attempt to write direct tests for helper/inner functions defined inside the target function. They are out of scope and will cause NameErrors.
6. MATH & FLOATS: Do not guess or hardcode decimal results. Use `pytest.approx()` or write the mathematical verification programmatically to match the source formulas.
7. NUMPY & ARRAYS: NEVER use `==` to compare numpy arrays. Use `np.array_equal()` or `np.allclose()`.
8. Do not write conversational text or explanations. Return ONLY clean executable Python code within Markdown blocks.
"""
SYSTEM_PROMPT_STRUCTURED = """You are an expert QA engineer specializing in writing highly robust Python unit tests. Your objective is to generate clear, comprehensive pytest cases for a specific target function.

CRITICAL EXECUTION RULES:
1. Use the pytest framework style exclusively. 
2. PARAMETERIZATION: You MUST use `@pytest.mark.parametrize` to group similar test cases. 
3. FIXTURES AND PARAMETERS: NEVER pass fixture function names directly into `@pytest.mark.parametrize` arrays. **You MUST prefix all custom fixture names and mock classes with the target function's exact name to prevent namespace collisions during suite consolidation (e.g., if testing `scaling`, name your fixture `scaling_sample_data`).**
4. DOCSTRING LIES: If the docstring claims an exception is raised, but the 'Function Implementation' block does NOT explicitly raise it (e.g., using the `raise` keyword), DO NOT test for the exception. Test the code exactly as it is written, even if it yields mathematically invalid results.
5. INNER FUNCTIONS: Do not attempt to write direct tests for helper/inner functions defined inside the target function. They are out of scope and will cause NameErrors.
6. MATH & FLOATS: Do not guess or hardcode decimal results. Use `pytest.approx()` or write the mathematical verification programmatically to match the source formulas.
7. NUMPY & ARRAYS: NEVER use `==` to compare numpy arrays. Use `np.array_equal()` or `np.allclose()`.
8. You must use the provided function tool to output your response as structured JSON. Do not write conversational text.
"""
ENVIRONMENT_CONTEXT_HEADER = (
    """AVAILABLE ENVIRONMENT CONTEXT (Already imported/loaded in execution space):\n"""
)
GLOBAL_CONSTANTS_HEADER = """--- Global Constants ---\n"""
CUSTOM_EXCEPTIONS_HEADER = """--- Registered Custom Exceptions ---\n"""
USER_PROMPT_HEADER = """Generate a pytest suite for the following target function module.
The function is segmented into its signature (providing type annotations), docstring, and implementation code, for clarity. 
Local context code blocks are also provided, as they can be necessary for the function to operate correctly.

NOTE: The implementation code may lack defensive checks described in the docstring. Test the code as it is currently written. Do not assume values or calculations; programmatically evaluate outputs using formulas matching the source.

...
"""
USER_PROMPT_IMPORTS = """\nTarget Package Access Route (For Test Script Top-Level):
```python
{function_import_statement}

```
"""
USER_PROMPT_LOCAL_CONTEXT = """\nTarget Module Runtime Context:
```python
{context_blocks}

```
"""
USER_PROMPT_BASE = """\nFull Target Definition (Signature, Docstring & Implementation):
```python
{full_code}

```
"""
USER_PROMPT_DIRECTIVES = """\nAdditional Target Directives:
{custom_instructions}

"""
USER_PROMPT_FOOTER = """Generate the comprehensive test code block.
"""
NUMPY_STYLE_GUIDE = """NUMPY STYLE INSTRUCTIONS:
1. TONE: Professional prose, active, and intent-focused. Do not translate code logic literally step-by-step.
2. MARKUP: Use single backticks (`param`) for parameter references, and double backticks (``value``) for literals, inline types, or code tokens.
3. SYNTAX: Use standard Sphinx/reST directives (e.g., `.. math::`, `.. versionchanged::`) for complex formatting within text fields.
4. BOUNDED CHOICES: If a parameter is typed as a `Literal` or `Enum`, extract those exact values into the `choices` array field. Never invent or hallucinate choices outside of what is explicitly defined in the type hint.
5. DEFAULT VALUES: NEVER document default values in parameter descriptions (e.g., do not write "Defaults to X"). This is handled automatically by the JSON schema.
6. CONCISENESS: No fluff. Parameter descriptions must state WHAT the argument is, not WHY it is important. Limit parameter descriptions to a single concise sentence unless a complex data structure requires a bulleted breakdown.
"""
AUTODOC_SYSTEM_PROMPT = """You are an expert Python technical writer. Your objective is to extract and generate strict NumPy-compliant docstring fields to populate the provided JSON schema.

CRITICAL RULES:
1. ALIGNMENT: Types and parameters must strictly mirror the target signature. Do not hallucinate fields the schema does not request.
2. DOMAIN CONTEXT: Infuse the provided global project context into descriptions to avoid generic placeholders.

{style_guide}"""
AUTODOC_GENERATE_USER = """Generate NumPy-compliant docstring fields for the target object.
{examples_directive}

Global Project Context:
{readme_context}

Target Signature:
{signature}

Target Implementation:
{code}

Internal Dependencies Called:
{dependency_context}
"""
AUTODOC_VERIFY_USER = """Analyze the provided implementation against its EXISTING docstring documentation.

TASKS:
1. Discrepancy Correction: Fix misaligned types, missing arguments, undocumented return types, and explicitly thrown exceptions.
2. Style Adherence: Rewrite awkward, robotic code translations into clean, professional prose.
{examples_directive}

Global Project Context:
{readme_context}

Target Signature:
{signature}

Target Implementation:
{code}

Existing Docstring to Correct:
{existing_docstring}
"""
