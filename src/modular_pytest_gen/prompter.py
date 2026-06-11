import json
from typing import Any, Dict, List

class PromptBuilder:
    def __init__(self, import_prefix: str, module_name: str):
        """
        Args:
            import_prefix: Top-level framework name (e.g., 'otaf')
            module_name: The target file's logical path (e.g., 'utils.math')
        """
        self.import_prefix = import_prefix
        self.module_name = module_name
        self.full_import_path = f"{import_prefix}.{module_name}"

    def build_system_prompt(self, global_context: Dict[str, Any]) -> str:
        """
        Constructs the high-level system prompt, injecting parsed definitions
        of custom exceptions and global constants.
        """
        system_base = (
            "You are an expert QA engineer specializing in writing highly robust Python unit tests.\n"
            "Your objective is to generate clear, comprehensive pytest cases for a specific target function.\n\n"
            "CRITICAL EXECUTION RULES:\n"
            "1. Use the pytest framework style exclusively.\n"
            "2. Ensure tests exercise full functionality and robustness against erroneous or unexpected arguments.\n"
            "3. Include precise docstrings explaining what specific edge case each test validates.\n"
            f"4. You must reference the function under test using its fully qualified path: '{self.full_import_path}.func_name'.\n"
            "5. Do not write conversational text or explanations. Return ONLY clean executable Python code within Markdown blocks.\n"
        )

        # Inject global custom exception context if extracted by your parser
        exception_blocks = []
        for exc in global_context.get("exceptions", []):
            exception_blocks.append(f"Class {exc['name']}({', '.join(exc['bases'])}): Doc: {exc['docstring']}")
        
        # Inject global constants if available
        constant_blocks = [f"{k} = {v}" for k, v in global_context.get("constants", {}).items()]

        context_str = ""
        if exception_blocks or constant_blocks:
            context_str += "\nAVAILABLE ENVIRONMENT CONTEXT (Already imported/loaded in execution space):\n"
            if constant_blocks:
                context_str += "--- Global Constants ---\n" + "\n".join(constant_blocks) + "\n"
            if exception_blocks:
                context_str += "--- Registered Custom Exceptions ---\n" + "\n".join(exception_blocks) + "\n"

        return system_base + context_str

    def build_user_prompt(self, function_metadata: Dict[str, Any], custom_instructions: str = "") -> str:
        """
        Constructs the unique prompt payload for an individual function targeted for testing.
        """
        user_prompt = (
            f"Generate a pytest suite for the following target function module.\n\n"
            f"Function Signature:\n{function_metadata['signature']}\n\n"
            f"Source Implementation:\n```python\n{function_metadata['code']}\n```\n\n"
        )
        
        if function_metadata.get("docstring"):
            user_prompt += f"Implementation Intention:\n{function_metadata['docstring']}\n\n"

        if custom_instructions:
            user_prompt += f"Additional Target Directives:\n{custom_instructions}\n\n"

        user_prompt += (
            "Generate the comprehensive test code block. Remember to mock deep downstream dependencies "
            f"if present, and call the routine via: {self.full_import_path}.{function_metadata['name']}"
        )
        return user_prompt