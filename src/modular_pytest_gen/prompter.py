import textwrap
from typing import Any, Dict

from . import templates


class PromptBuilder:
    def __init__(self, structured_output: bool = False):

        self.structured_output = structured_output

    def build_system_prompt(
        self, global_context: Dict[str, Any], fully_qualified_path: str
    ) -> str:

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

        user_prompt = templates.USER_PROMPT_HEADER + "\n"
        user_prompt += templates.USER_PROMPT_IMPORTS.format(
            import_statement=import_statement,
            function_import_statement=function_import_statement,
        )
        if function_metadata.get("local_context_code"):
            context_blocks = "\n".join(function_metadata["local_context_code"])
            user_prompt += templates.USER_PROMPT_LOCAL_CONTEXT.format(
                context_blocks=context_blocks
            )
        user_prompt += templates.USER_PROMPT_SIGNATURE.format(
            signature=function_metadata["signature"]
        )
        docstring = function_metadata.get("docstring")
        if docstring:
            user_prompt += templates.USER_PROMPT_DOCSTRING.format(
                docstring=textwrap.indent(docstring, "    ")
            )
        user_prompt += templates.USER_PROMPT_BASE.format(
            import_statement=import_statement, code=function_metadata["code"]
        )
        if custom_instructions:
            user_prompt += templates.USER_PROMPT_DIRECTIVES.format(
                custom_instructions=custom_instructions
            )
        user_prompt += templates.USER_PROMPT_FOOTER
        return user_prompt

    def get_tool_schema(self) -> Dict[str, Any]:

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
