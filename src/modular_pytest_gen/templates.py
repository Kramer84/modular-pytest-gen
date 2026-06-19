"""
Central repository for all LLM prompts. 
Isolating these here avoids packaging issues with external text files
while keeping the PromptBuilder class completely agnostic to the wording.
"""

SYSTEM_PROMPT_STANDARD = """You are an expert QA engineer specializing in writing highly robust Python unit tests.
Your objective is to generate clear, comprehensive pytest cases for a specific target function.

CRITICAL EXECUTION RULES:
1. Use the pytest framework style exclusively.
2. Ensure tests exercise full functionality and robustness against erroneous or unexpected arguments.
3. Include precise docstrings explaining what specific edge case each test validates.
4. You must reference the function under test using its fully qualified path: '{fully_qualified_path}'.
5. Do not write conversational text or explanations. Return ONLY clean executable Python code within Markdown blocks."""

SYSTEM_PROMPT_STRUCTURED = """You are an expert QA engineer specializing in writing highly robust Python unit tests.
Your objective is to generate clear, comprehensive pytest cases for a specific target function.

CRITICAL EXECUTION RULES:
1. Use the pytest framework style exclusively.
2. Ensure tests exercise full functionality and robustness against erroneous or unexpected arguments.
3. You must reference the function under test using its fully qualified path: '{fully_qualified_path}'.
4. You must use the provided function tool to output your response as structured JSON. Do not return conversational text."""

ENVIRONMENT_CONTEXT_HEADER = "\nAVAILABLE ENVIRONMENT CONTEXT (Already imported/loaded in execution space):\n"
GLOBAL_CONSTANTS_HEADER = "--- Global Constants ---\n"
CUSTOM_EXCEPTIONS_HEADER = "--- Registered Custom Exceptions ---\n"

USER_PROMPT_HEADER = """
Generate a pytest suite for the following target function module.
The function is segmented into its signature (providing type annotations), 
docstring, and implementation code, for clarity. 
Local context code blocks are also provided, as they can be necessary for 
the function to operate correctly."""

USER_PROMPT_IMPORTS = """
Target Package Access Route (For Test Script Top-Level):
```python
{import_statement}
{function_import_statement}
```
"""

USER_PROMPT_LOCAL_CONTEXT = """
Target Module Runtime Context:
```python
{context_blocks}
```
"""

USER_PROMPT_SIGNATURE = """
Function Signature:
```python
{signature}
```
"""

USER_PROMPT_DOCSTRING = """
Function Docstring:
{docstring}
"""

USER_PROMPT_BASE = """
Function Implementation:
```python
{import_statement}

{code}
```
"""

USER_PROMPT_DIRECTIVES = "Additional Target Directives:\n{custom_instructions}\n\n"

USER_PROMPT_FOOTER = "\nGenerate the comprehensive test code block."