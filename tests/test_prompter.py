import pytest
from modular_pytest_gen.prompter import PromptBuilder

def test_prompt_builder_init():
    builder = PromptBuilder()
    assert builder.structured_output is False

def test_build_system_prompt_empty_context():
    builder = PromptBuilder()
    system_prompt = builder.build_system_prompt({}, "pkg.mod.func_name")
    
    assert "You are an expert QA engineer" in system_prompt
    assert "CRITICAL EXECUTION RULES:" in system_prompt
    assert "'pkg.mod.func_name'" in system_prompt
    
    assert "AVAILABLE ENVIRONMENT CONTEXT" not in system_prompt

def test_build_system_prompt_rich_context():
    builder = PromptBuilder()
    
    global_context = {
        "constants": {
            "BASE_SURFACE_TYPES": '["plane", "cylinder"]',
            "TIMEOUT": "10"
        },
        "exceptions": [
            {
                "name": "MissingSurfaceTypeKeyError",
                "bases": ["KeyError"],
                "docstring": "Raised when surface type is missing.",
                "import_path": "otaf.exceptions.MissingSurfaceTypeKeyError"
            },
            {
                "name": "ComplexMultiBaseError",
                "bases": ["ValueError", "Exception"],
                "docstring": None
            }
        ]
    }
    
    system_prompt = builder.build_system_prompt(global_context, "run")
    
    assert "AVAILABLE ENVIRONMENT CONTEXT" in system_prompt
    assert "--- Global Constants ---" in system_prompt
    assert "--- Registered Custom Exceptions ---" in system_prompt
    
    assert 'BASE_SURFACE_TYPES = ["plane", "cylinder"]' in system_prompt
    assert "TIMEOUT = 10" in system_prompt
    
    # Updated to verify the new import path logic
    assert "Class MissingSurfaceTypeKeyError(KeyError): Import via 'otaf.exceptions.MissingSurfaceTypeKeyError'. Doc: Raised when surface type is missing." in system_prompt
    assert "Class ComplexMultiBaseError(ValueError, Exception): Import via 'ComplexMultiBaseError'. Doc: None" in system_prompt


def test_build_system_prompt_structured():
    builder = PromptBuilder(structured_output=True)
    system_prompt = builder.build_system_prompt({}, "pkg.my_func")
    
    assert "use the provided function tool" in system_prompt
    assert "within Markdown blocks" not in system_prompt

def test_build_user_prompt_minimal():
    builder = PromptBuilder()
    function_metadata = {
        "name": "calc",
        "signature": "def calc():",
        "code": "def calc(): pass",
        "docstring": None
    }
    
    user_prompt = builder.build_user_prompt(function_metadata)
    
    assert "Function Signature:\ndef calc():" in user_prompt
    
    expected_code = "Source Implementation:\n" + "```python\ndef calc(): pass\n```"
    assert expected_code in user_prompt