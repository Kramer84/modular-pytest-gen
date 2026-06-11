import pytest
from modular_pytest_gen.prompter import PromptBuilder

def test_prompt_builder_init():
    builder = PromptBuilder(import_prefix="my_pkg", module_name="utils.core")
    assert builder.import_prefix == "my_pkg"
    assert builder.module_name == "utils.core"
    assert builder.full_import_path == "my_pkg.utils.core"

def test_build_system_prompt_empty_context():
    builder = PromptBuilder("pkg", "mod")
    system_prompt = builder.build_system_prompt({})
    
    assert "You are an expert QA engineer" in system_prompt
    assert "CRITICAL EXECUTION RULES:" in system_prompt
    assert "'pkg.mod.func_name'" in system_prompt
    
    # If no context is provided, the environment context block should be omitted entirely
    assert "AVAILABLE ENVIRONMENT CONTEXT" not in system_prompt
    assert "--- Global Constants ---" not in system_prompt

def test_build_system_prompt_rich_context():
    builder = PromptBuilder("otaf", "constants")
    
    # Mocking the exact structure produced by the ModuleParser
    global_context = {
        "constants": {
            "BASE_SURFACE_TYPES": '["plane", "cylinder"]',
            "TIMEOUT": "10"
        },
        "exceptions": [
            {
                "name": "MissingSurfaceTypeKeyError",
                "bases": ["KeyError"],
                "docstring": "Raised when surface type is missing."
            },
            {
                "name": "ComplexMultiBaseError",
                "bases": ["ValueError", "Exception"],
                "docstring": None
            }
        ]
    }
    
    system_prompt = builder.build_system_prompt(global_context)
    
    # Verify Context Headers
    assert "AVAILABLE ENVIRONMENT CONTEXT" in system_prompt
    assert "--- Global Constants ---" in system_prompt
    assert "--- Registered Custom Exceptions ---" in system_prompt
    
    # Verify Constants Formatting
    assert 'BASE_SURFACE_TYPES = ["plane", "cylinder"]' in system_prompt
    assert "TIMEOUT = 10" in system_prompt
    
    # Verify Exception Formatting and None handling
    assert "Class MissingSurfaceTypeKeyError(KeyError): Doc: Raised when surface type is missing." in system_prompt
    assert "Class ComplexMultiBaseError(ValueError, Exception): Doc: None" in system_prompt

def test_build_system_prompt_partial_context():
    builder = PromptBuilder("app", "logic")
    global_context = {
        "constants": {"DEBUG_MODE": "True"}
        # exceptions deliberately missing
    }
    system_prompt = builder.build_system_prompt(global_context)
    
    assert "AVAILABLE ENVIRONMENT CONTEXT" in system_prompt
    assert "--- Global Constants ---" in system_prompt
    assert "DEBUG_MODE = True" in system_prompt
    assert "--- Registered Custom Exceptions ---" not in system_prompt

def test_build_user_prompt_minimal():
    builder = PromptBuilder("app", "logic")
    function_metadata = {
        "name": "calculate_sum",
        "signature": "def calculate_sum(a: int, b: int) -> int:",
        "code": "def calculate_sum(a, b):\n    return a + b",
        "docstring": None
    }
    
    user_prompt = builder.build_user_prompt(function_metadata)
    
    # Verify core injected elements
    assert "Function Signature:\ndef calculate_sum(a: int, b: int) -> int:" in user_prompt
    
    # Safely constructing the markdown backticks using concatenation 
    # to avoid UI markdown rendering bugs.
    expected_code_block = "Source Implementation:\n" + "```python\ndef calculate_sum(a, b):\n    return a + b\n```"
    assert expected_code_block in user_prompt
    
    # Verify optional elements are correctly omitted
    assert "Implementation Intention:" not in user_prompt
    assert "Additional Target Directives:" not in user_prompt
    
    # Verify the specific execution path instruction
    assert "app.logic.calculate_sum" in user_prompt

def test_build_user_prompt_full_with_directives():
    builder = PromptBuilder("core", "engine")
    function_metadata = {
        "name": "run_migration",
        "signature": "async def run_migration(force: bool = False) -> bool:",
        "code": "async def run_migration(force=False):\n    pass",
        "docstring": "Executes the database migration safely."
    }
    custom_instructions = "Do NOT mock the database connection, use the test engine fixture."
    
    user_prompt = builder.build_user_prompt(function_metadata, custom_instructions)
    
    # Verify optional blocks are included when data is present
    assert "Implementation Intention:\nExecutes the database migration safely." in user_prompt
    assert "Additional Target Directives:\nDo NOT mock the database connection, use the test engine fixture." in user_prompt
    
    # Verify the specific execution path instruction
    assert "core.engine.run_migration" in user_prompt