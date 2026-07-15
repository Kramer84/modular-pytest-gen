import textwrap
from typing import Any, Dict

from . import templates


class PromptBuilder:
    r"""
    Constructs prompts for LLM test generation.
    
    The `PromptBuilder` class orchestrates the construction of system and
    user prompts for LLM test generation. It formats global context,
    function metadata, and custom instructions into structured prompts that
    guide the LLM in generating appropriate test cases.
    
    Parameters
    ----------
    structured_output : bool, optional
        Flag to use structured output templates.
    
    Attributes
    ----------
    structured_output : bool
        Flag indicating whether structured output templates are used.
    
    Methods
    -------
    build_system_prompt :
        Constructs the system prompt with global context and fully
        qualified path.
    build_user_prompt :
        Constructs the user prompt with function metadata, import
        statements, and custom instructions.
    get_tool_schema :
        Returns the tool schema for LLM test generation.
    
    See Also
    --------
    templates :
        Module containing prompt templates.
    """

    def __init__(self, structured_output: bool = False):
        r"""
        Initialize the object with structured output configuration.
        
        Configures the object to produce outputs in a structured format if
        enabled.
        
        Warnings
        --------
        Ensure that the structured output flag is set correctly to avoid
        unexpected output formats.
        
        See Also
        --------
        structured_output :
            Flag indicating whether the output should be structured.
        
        Notes
        -----
        The structured output flag determines the format of the output
        data. When enabled, the output will be formatted as a structured
        object, otherwise it will be in a default format.
        """

        self.structured_output = structured_output

    def build_system_prompt(
        self, global_context: Dict[str, Any], fully_qualified_path: str
    ) -> str:
        r"""
        Constructs a system prompt for LLM test generation.
        
        This method dynamically generates a system prompt by integrating
        the fully qualified path of the target object and contextual
        metadata from the global context. The prompt structure varies based
        on the `structured_output` flag, and includes blocks for custom
        exceptions and global constants if available.
        
        Parameters
        ----------
        global_context : Dict[str, Any]
            A dictionary containing contextual metadata such as custom
            exceptions and global constants.
        fully_qualified_path : str
            The fully qualified path of the target object for which the
            system prompt is being generated.
        
        Returns
        -------
        str
            The constructed system prompt string, which includes the base
            template and any additional context blocks for exceptions and
            constants.
        
        Raises
        ------
        KeyError
            If the `global_context` dictionary is missing required keys
            such as 'exceptions' or 'constants'.
        
        Warnings
        --------
        Ensure that the `global_context` dictionary contains all necessary
        keys to avoid missing context in the generated prompt.
        """

        template = (
            templates.SYSTEM_PROMPT_STRUCTURED
            if self.structured_output
            else templates.SYSTEM_PROMPT_STANDARD
        )
        system_base = template.format(fully_qualified_path=fully_qualified_path)
        exception_blocks = []
        for exc in global_context.get("exceptions", []):
            import_path = exc.get("import_path", exc["name"])
            exception_blocks.append(
                f"Class {exc['name']}({', '.join(exc['bases'])}): Import via '{import_path}'. Doc: {exc['docstring']}"
            )
        constant_blocks = [
            f"{k} = {v}" for k, v in global_context.get("constants", {}).items()
        ]
        context_str = ""
        if exception_blocks or constant_blocks:
            context_str += templates.ENVIRONMENT_CONTEXT_HEADER
            if constant_blocks:
                context_str += (
                    templates.GLOBAL_CONSTANTS_HEADER
                    + "\n".join(constant_blocks)
                    + "\n"
                )
            if exception_blocks:
                context_str += (
                    templates.CUSTOM_EXCEPTIONS_HEADER
                    + "\n".join(exception_blocks)
                    + "\n"
                )
        return system_base + context_str

    def build_user_prompt(
        self,
        function_metadata: Dict[str, Any],
        function_import_statement: str,
        import_statement: str,
        custom_instructions: str = "",
    ) -> str:
        r"""
        Constructs a user prompt for LLM test generation.
        
        This method dynamically assembles a prompt by combining static
        templates with function-specific metadata, import statements, and
        optional custom instructions. The resulting prompt provides the LLM
        with comprehensive context for generating accurate unit tests.
        
        Parameters
        ----------
        function_metadata : Dict[str, Any]
            A dictionary containing function-specific metadata including
            signature, code, and optional docstring.
        function_import_statement : str
            The import statement for the function being tested.
        import_statement : str
            The general import statement for the module containing the
            function.
        custom_instructions : str, optional
            Optional custom instructions to guide the LLM in test
            generation. Default is .
        
        Returns
        -------
        str
            The constructed user prompt as a single string, combining all
            provided components and templates.
        
        See Also
        --------
        templates.USER_PROMPT_HEADER :
            The header template for the user prompt.
        templates.USER_PROMPT_IMPORTS :
            The template for import statements in the user prompt.
        templates.USER_PROMPT_LOCAL_CONTEXT :
            The template for local context code in the user prompt.
        templates.USER_PROMPT_SIGNATURE :
            The template for the function signature in the user prompt.
        templates.USER_PROMPT_DOCSTRING :
            The template for the function docstring in the user prompt.
        templates.USER_PROMPT_BASE :
            The base template for the function code in the user prompt.
        templates.USER_PROMPT_DIRECTIVES :
            The template for custom instructions in the user prompt.
        templates.USER_PROMPT_FOOTER :
            The footer template for the user prompt.
        """

        user_prompt = templates.USER_PROMPT_HEADER + "\n"
        user_prompt += templates.USER_PROMPT_IMPORTS.format(
            function_import_statement=function_import_statement,
        )
        if function_metadata.get("local_context_code"):
            context_blocks = "\n".join(function_metadata["local_context_code"])
            user_prompt += templates.USER_PROMPT_LOCAL_CONTEXT.format(
                context_blocks=context_blocks
            )
        full_code_lines = []
        if import_statement:
            full_code_lines.append(import_statement)
            full_code_lines.append("")
        signature = function_metadata["signature"].strip()
        full_code_lines.append(signature)
        docstring = function_metadata.get("docstring")
        if docstring:
            wrapped_docstring = (
                f'    """\n{textwrap.indent(docstring.strip(), "    ")}\n    """'
            )
            full_code_lines.append(wrapped_docstring)
        impl_lines = function_metadata["code"].strip().splitlines()
        if impl_lines:
            body_code = "\n".join(impl_lines[1:])
            full_code_lines.append(body_code)

        full_code_block = "\n".join(full_code_lines)
        user_prompt += templates.USER_PROMPT_BASE.format(full_code=full_code_block)
        if custom_instructions:
            user_prompt += templates.USER_PROMPT_DIRECTIVES.format(
                custom_instructions=custom_instructions
            )
        user_prompt += templates.USER_PROMPT_FOOTER
        return user_prompt

    def get_tool_schema(self) -> Dict[str, Any]:
        r"""
        Retrieve the JSON schema for the pytest generation tool.
        
        This method returns the structured schema definition used by the
        pytest generation tool to validate and process test case inputs.
        
        Returns
        -------
        Dict[str, Any]
            The JSON schema defining the structure and validation rules for
            the pytest generation tool's input parameters.
        """

        return {
            "type": "function",
            "function": {
                "name": "write_pytest_suite",
                "description": "Outputs clean, functional pytest components for the target unit.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "local_fixtures_and_mocks": {
                            "type": "string",
                            "description": "Any specific pytest fixtures, mock definitions, or setups required strictly for these tests. Leave empty if none are needed.",
                        },
                        "test_cases": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "A list of individual test function implementations (e.g., ['def test_case_1()...', 'def test_case_2()...']). Do not include imports here.",
                        },
                    },
                    "required": ["test_cases"],
                },
            },
        }
