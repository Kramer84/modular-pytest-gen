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
8. Do not write conversational text or explanations. Return ONLY clean executable Python code within Markdown blocks."""
r"""
    Define the standard system prompt for test generation.
    
    This constant provides the foundational instructions for the LLM to
    generate comprehensive pytest suites. It outlines the critical
    execution rules that ensure the generated tests are robust, isolated,
    and adhere to pytest best practices.
    
    See Also
    --------
    modular_pytest_gen.generate_tests :
        Function that utilizes this prompt to generate tests.
    
    References
    ----------
    .. [1] Pytest documentation on fixtures and parametrization.
    .. [2] Python documentation on exception handling.
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
8. You must use the provided function tool to output your response as structured JSON. Do not write conversational text."""
r"""
    Defines the structured system prompt for test generation.
    
    This constant provides the foundational instructions for the LLM to
    generate comprehensive pytest suites. It specifies the framework to
    use, parameterization requirements, fixture naming conventions, and
    critical execution rules to ensure test robustness and maintainability.
    
    See Also
    --------
    modular_pytest_gen.generate_tests :
        Uses this constant to guide LLM test generation.
    
    References
    ----------
    .. [1] The pytest documentation for framework-specific details:
       https://docs.pytest.org/en/7.4.x/
    """
ENVIRONMENT_CONTEXT_HEADER = """
    AVAILABLE ENVIRONMENT CONTEXT (Already imported/loaded in execution space):
    """
r"""
    Define the header for environment context documentation.
    
    This constant provides a standardized header for documenting the
    available environment context in the execution space. It is used to
    clearly separate and identify the context information that is already
    imported or loaded before the execution of the code.
    
    See Also
    --------
    ENVIRONMENT_CONTEXT_HEADER :
        The constant that defines the header for environment context
        documentation.
    
    References
    ----------
    .. [1] The Python documentation for string constants.
    .. [2] PEP 8 -- Style Guide for Python Code for string constant naming
       conventions.
    """
GLOBAL_CONSTANTS_HEADER = """--- Global Constants ---
"""
r"""
    Define the header for global constants section.
    
    This constant is used to visually separate and identify the section
    containing global constants in the documentation.
    
    See Also
    --------
    GLOBAL_CONSTANTS_FOOTER :
        The footer constant that marks the end of the global constants
        section.
    
    References
    ----------
    .. [1] Python Enhancement Proposal 8 (PEP 8) - Style Guide for Python
       Code
    .. [2] NumPy Documentation Style Guide
    """
CUSTOM_EXCEPTIONS_HEADER = """--- Registered Custom Exceptions ---
"""
r"""
    Define a header string for custom exception documentation.
    
    This constant serves as a visual delimiter in generated documentation,
    separating the custom exception definitions from other code elements.
    It is used by the documentation generator to create clear, scannable
    sections in the output.
    
    See Also
    --------
    modular_pytest_gen.docstring_generation.generate_docstring :
        The function that incorporates this header into the final
        documentation output.
    
    References
    ----------
    .. [1] Sphinx Documentation Markup Guide, Section 5.1.2
    .. [2] Python Enhancement Proposal 257 -- Docstring Conventions
    """
USER_PROMPT_HEADER = """
Generate a pytest suite for the following target function module.
The function is segmented into its signature (providing type annotations), docstring, and implementation code, for clarity. 
Local context code blocks are also provided, as they can be necessary for the function to operate correctly.

NOTE: The implementation code may lack defensive checks described in the docstring. Test the code as it is currently written. Do not assume values or calculations; programmatically evaluate outputs using formulas matching the source.

...
"""
r"""
    Define the header for pytest suite generation prompts.
    
    This constant serves as the introductory segment for prompts used to
    generate pytest suites. It provides essential context about the
    purpose, structure, and limitations of the automated test generation
    process.
    
    See Also
    --------
    modular_pytest_gen.generate_pytest_suite :
        The function that utilizes this header to construct complete pytest
        suite generation prompts.
    
    References
    ----------
    .. [1] The modular-pytest-gen architecture documentation, section on
       automated test generation.
    """
USER_PROMPT_IMPORTS = """
Target Package Access Route (For Test Script Top-Level):
```python
{import_statement}
{function_import_statement}
```
"""
r"""
    Constructs the import statement for the target function.
    
    This constant is used to generate the import statement for the target
    function. It is used in the test generation process to ensure that the
    target function is properly imported and accessible in the test script.
    
    See Also
    --------
    modular_pytest_gen.test_generation.generate_test :
        The function that uses this constant to generate the import
        statement for the target function.
    
    References
    ----------
    .. [1] The import statement is generated using the target package
       access route, which is extracted from the source code using Abstract
       Syntax Tree (AST) parsing.
    """
USER_PROMPT_LOCAL_CONTEXT = """
    Target Module Runtime Context:
    ```python
    {context_blocks}
    ```
    """
r"""
    Define template for embedding local module context in llm prompts.
    
    This constant serves as a structured template for injecting the parsed
    local module context into the LLM prompt. The template uses a code
    block to clearly separate the context from the rest of the prompt,
    ensuring the LLM can accurately interpret the provided context.
    
    See Also
    --------
    modular_pytest_gen.prompting.context_extraction.extract_local_context :
        Extracts the local context from the module.
    
    References
    ----------
    .. [1] The template is designed to be compatible with the LLM prompt
       generation pipeline, ensuring that the context is presented in a
       format that the LLM can understand and utilize effectively.
    """

USER_PROMPT_SIGNATURE = """
Function Signature:
```python
{signature}
```
"""
r"""
    Defines the template for user-provided function signatures.
    
    This constant serves as the foundational template for capturing
    user-defined function signatures within the modular-pytest-gen
    framework. It ensures consistent formatting and integration with the
    automated test generation pipeline.
    
    See Also
    --------
    modular_pytest_gen.generate_tests :
        The primary function that utilizes this template to construct test
        cases.
    
    References
    ----------
    .. [1] The modular-pytest-gen architecture documentation, section 3.2.1
    """
USER_PROMPT_DOCSTRING = """
Function Docstring:
{docstring}
"""
r"""
    Define the constant for user prompt docstring.
    
    This constant is used to format the function docstring for display
    purposes. It includes a newline character, the string 'Function
    Docstring:', another newline character, and the docstring itself
    enclosed in curly braces.
    
    See Also
    --------
    modular-pytest-gen :
        A highly modular tool for automatically generating comprehensive
        pytest suites and context-aware docstrings using syntax tree
        parsing and Large Language Model (LLM) prompts.
    
    References
    ----------
    .. [1] modular-pytest-gen documentation:
       https://github.com/yourusername/modular-pytest-gen
    """
USER_PROMPT_BASE = """
    Function Implementation:
    ```python
    {import_statement}
    
    {code}
    ```
    """
r"""
    Define the base template for user-provided function implementations.
    
    This constant serves as the foundational template for structuring
    user-provided function implementations within the modular pytest
    generation framework. It ensures consistent formatting and includes
    placeholders for essential components like import statements and the
    actual code block.
    
    See Also
    --------
    modular_pytest_gen.generate_tests :
        The primary function that utilizes this template to generate
        comprehensive test suites.
    
    References
    ----------
    .. [1] The modular pytest generation framework documentation for
       detailed usage examples and integration patterns.
    """
USER_PROMPT_DIRECTIVES = """Additional Target Directives:
{custom_instructions}

"""
r"""
    Define custom directives for test generation.
    
    This constant holds the template string used to inject custom
    instructions into the test generation prompt. The template includes a
    placeholder for user-provided directives, ensuring flexibility in test
    generation.
    
    See Also
    --------
    modular_pytest_gen.generate_tests :
        Function that uses this constant to generate tests.
    
    References
    ----------
    .. [1] The modular-pytest-gen architecture documentation.
    """
USER_PROMPT_FOOTER = """
Generate the comprehensive test code block."""
r"""
    Define the footer for user prompts.
    
    This constant is used to append a standardized footer to user prompts,
    ensuring consistent formatting and context for LLM-generated test code
    blocks.
    
    See Also
    --------
    USER_PROMPT_HEADER :
        The header constant used to standardize user prompts.
    
    References
    ----------
    .. [1] The Modular Pytest & Doc Gen project documentation.
    """
NUMPY_STYLE_GUIDE = """NUMPY STYLE INSTRUCTIONS:
1. TONE: Professional prose, active, and intent-focused. Do not translate code logic literally step-by-step.
2. MARKUP: Use single backticks (`param`) for parameter references, and double backticks (``value``) for literals, inline types, or code tokens.
3. SYNTAX: Use standard Sphinx/reST directives (e.g., `.. math::`, `.. versionchanged::`) for complex formatting within text fields.
4. BOUNDED CHOICES: If a parameter is typed as a `Literal` or `Enum`, extract those exact values into the `choices` array field. Never invent or hallucinate choices outside of what is explicitly defined in the type hint."""
r"""
    Define the standard for generating NumPy-compliant docstrings.
    
    The `NUMPY_STYLE_GUIDE` constant provides a comprehensive set of
    instructions for generating professional, intent-focused docstrings
    that align with NumPy standards. It includes guidelines on tone,
    markup, syntax, and handling bounded choices, ensuring consistency and
    clarity in documentation.
    
    See Also
    --------
    modular-pytest-gen :
        A highly modular tool for automatically generating comprehensive
        pytest suites and context-aware docstrings.
    
    References
    ----------
    .. [1] NumPy Documentation Style Guide
       (https://numpydoc.readthedocs.io/en/latest/format.html)
    """

AUTODOC_SYSTEM_PROMPT = """You are an expert Python technical writer. Your objective is to extract and generate strict NumPy-compliant docstring fields to populate the provided JSON schema.

CRITICAL RULES:
1. ALIGNMENT: Types and parameters must strictly mirror the target signature. Do not hallucinate fields the schema does not request.
2. DOMAIN CONTEXT: Infuse the provided global project context into descriptions to avoid generic placeholders.

{style_guide}"""
r"""
    Define system prompt template for numpy-compliant docstrings.
    
    This constant serves as the foundational template for the docstring
    generation process. It provides the LLM with explicit instructions for
    generating accurate, context-aware documentation that adheres to NumPy
    standards. The template includes critical rules for alignment and
    domain context to ensure the generated docstrings are both technically
    precise and relevant to the project's specific domain.
    
    See Also
    --------
    modular_pytest_gen.generate_docstrings :
        The function that utilizes this template to generate docstrings for
        Python source files.
    
    References
    ----------
    .. [1] NumPy Documentation Style Guide
       (https://numpydoc.readthedocs.io/en/latest/format.html)
    """

AUTODOC_GENERATE_USER = """Generate NumPy-compliant docstring fields for the target object.
{examples_directive}

Global Project Context:
{readme_context}

Target Signature:
{signature}

Target Implementation:
{code}

Internal Dependencies Called:
{dependency_context}"""
r"""
    Generate NumPy-compliant docstring fields for the target object.
    
    This constant defines the prompt template used to generate
    NumPy-compliant docstring fields for a target object. The template
    includes placeholders for examples, global project context, target
    signature, target implementation, and internal dependencies called.
    
    See Also
    --------
    modular-pytest-gen :
        The highly modular tool for automatically generating comprehensive
        pytest suites and context-aware docstrings.
    
    References
    ----------
    .. [1] modular-pytest-gen documentation
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
{existing_docstring}"""
r"""
    Define the prompt template for docstring verification.
    
    This constant holds the template used to verify and correct docstrings
    against their corresponding implementations. The template includes
    specific tasks such as discrepancy correction and style adherence, and
    incorporates examples and project context.
    
    See Also
    --------
    AUTODOC_GENERATE_DOCSTRING :
        The constant used for generating docstrings from scratch.
    
    References
    ----------
    .. [1] The modular-pytest-gen project documentation for more details on
       docstring verification.
    """
