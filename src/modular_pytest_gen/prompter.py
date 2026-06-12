from typing import Any, Dict, Optional
from . import templates

class PromptBuilder:
    """
    Constructs contextual LLM prompts for generating pytest suites.
    Agnostic to path resolution—relies on the caller to provide exact paths.
    """
    def __init__(self, structured_output: bool = False):
        """
        Args:
            structured_output: If True, formats the system prompt to expect Tool/JSON calling.
        """
        self.structured_output = structured_output

    def build_system_prompt(self, global_context: Dict[str, Any], fully_qualified_path: str) -> str:
        """
        Constructs the high-level system prompt, injecting parsed definitions
        of custom exceptions and global constants.
        """
        template = templates.SYSTEM_PROMPT_STRUCTURED if self.structured_output else templates.SYSTEM_PROMPT_STANDARD
        
        system_base = template.format(fully_qualified_path=fully_qualified_path)

        exception_blocks = []
        for exc in global_context.get("exceptions", []):
            import_path = exc.get("import_path", exc["name"])
            exception_blocks.append(f"Class {exc['name']}({', '.join(exc['bases'])}): Import via '{import_path}'. Doc: {exc['docstring']}")
        
        constant_blocks = [f"{k} = {v}" for k, v in global_context.get("constants", {}).items()]

        context_str = ""
        if exception_blocks or constant_blocks:
            context_str += templates.ENVIRONMENT_CONTEXT_HEADER
            if constant_blocks:
                context_str += templates.GLOBAL_CONSTANTS_HEADER + "\n".join(constant_blocks) + "\n"
            if exception_blocks:
                context_str += templates.CUSTOM_EXCEPTIONS_HEADER + "\n".join(exception_blocks) + "\n"

        return system_base + context_str

    def build_user_prompt(self, function_metadata: Dict[str, Any], custom_instructions: str = "") -> str:
        """
        Constructs the unique prompt payload for an individual function targeted for testing.
        """
        user_prompt = templates.USER_PROMPT_BASE.format(
            signature=function_metadata['signature'],
            code=function_metadata['code']
        )
        
        docstring = function_metadata.get("docstring")
        if docstring:
            user_prompt += templates.USER_PROMPT_DOCSTRING.format(docstring=docstring)

        if custom_instructions:
            user_prompt += templates.USER_PROMPT_DIRECTIVES.format(custom_instructions=custom_instructions)

        user_prompt += templates.USER_PROMPT_FOOTER
        return user_prompt

    def get_tool_schema(self) -> Dict[str, Any]:
        """
        Returns the JSON schema required if using structured_output=True via Tool Calling.
        """
        return {
            "type": "function",
            "function": {
                "name": "write_pytest_suite",
                "description": "Outputs the generated pytest suite as raw Python code.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {
                            "type": "string",
                            "description": "Brief explanation of the edge cases covered."
                        },
                        "pytest_code": {
                            "type": "string",
                            "description": "The raw Python code containing the pytest functions."
                        }
                    },
                    "required": ["pytest_code"]
                }
            }
        }