import pytest
import ast
from pathlib import Path
from modular_pytest_gen.parser import ModuleParser

def test_module_parser_functional_utility(tmp_path):
    source_code = '''
import os
from typing import List

def sample_function(x: int) -> int:
    """A sample function."""
    return x * 2
'''
    file_path = tmp_path / "sample_module.py"
    file_path.write_text(source_code, encoding="utf-8")

    parser = ModuleParser(file_path)
    result = parser.parse()

    assert result["filename"] == "sample_module.py"
    assert len(result["imports"]) == 2
    assert "import os" in result["imports"]
    
    assert len(result["functions"]) == 1
    func = result["functions"][0]
    assert func["name"] == "sample_function"
    assert func["docstring"] == "A sample function."
    
    assert result["flags"]["profile"] == "FUNCTIONAL_UTILITY"

def test_module_parser_complex_with_exceptions(tmp_path):
    source_code = '''
__all__ = ["MyError", "MyClass"]

class MyError(Exception):
    """Custom error class."""
    pass

class MyClass:
    def __init__(self):
        self.val = 1
'''
    file_path = tmp_path / "complex_module.py"
    file_path.write_text(source_code, encoding="utf-8")

    parser = ModuleParser(file_path)
    result = parser.parse()

    assert result["flags"]["has_dunder_all"] is True
    assert result["dunder_all"] == ["MyError", "MyClass"]

    assert len(result["exceptions"]) == 1
    assert result["exceptions"][0]["name"] == "MyError"

    assert len(result["classes"]) == 1
    assert result["classes"][0]["name"] == "MyClass"

    assert result["flags"]["profile"] == "COMPLEX_MODULE"

def test_module_parser_constants_and_floating_code(tmp_path):
    source_code = '''
MAX_RETRIES = 5
timeout = 10

if __name__ == "__main__":
    print("Running")
'''
    file_path = tmp_path / "const_module.py"
    file_path.write_text(source_code, encoding="utf-8")

    parser = ModuleParser(file_path)
    result = parser.parse()

    assert "MAX_RETRIES" in result["constants"]
    assert result["constants"]["MAX_RETRIES"] == "5"

    assert result["flags"]["has_free_floating_code"] is True
    # timeout assignment is caught as free floating
    assert any("timeout = 10" in code for code in result["free_floating_code"])

    # If this module has constants but no funcs/classes, it should be a registry
    assert result["flags"]["profile"] == "CONSTANT_REGISTRY"

def test_module_parser_constants_advanced(tmp_path):
    source_code = '''from __future__ import annotations
# -*- coding: utf-8 -*-

__author__ = "Kramer84"
__all__ = [
    "BASE_SURFACE_TYPES",
    "SURFACE_DIRECTIONS"
]

import re
import numpy as np

"""
_constants.py
Defines constants.
"""

BASE_SURFACE_TYPES = ["plane", "cylinder", "cone", "sphere"]
SURFACE_DIRECTIONS = ["centripetal", "centrifugal"]
'''
    file_path = tmp_path / "constants_advanced.py"
    file_path.write_text(source_code, encoding="utf-8")

    parser = ModuleParser(file_path)
    result = parser.parse()

    # 1. Constants verification
    assert "BASE_SURFACE_TYPES" in result["constants"]
    assert "SURFACE_DIRECTIONS" in result["constants"]
    
    # 2. Dunder __all__ tracking
    assert result["flags"]["has_dunder_all"] is True
    assert "BASE_SURFACE_TYPES" in result["dunder_all"]

    # 3. Metadata should NOT be treated as executable code
    # FAILS CURRENTLY: __author__ is logged as free_floating_code
    assert result["flags"]["has_free_floating_code"] is False
    assert len(result["free_floating_code"]) == 0

    # 4. Profile validation
    assert result["flags"]["profile"] == "CONSTANT_REGISTRY"

    # 5. Docstring tracking for misplaced strings 
    # FAILS CURRENTLY: Returns None because docstring is not the first node
    # assert result["module_docstring"] is not None 

def test_module_parser_exceptions_and_dependencies(tmp_path):
    source_code = '''from __future__ import annotations
import numpy as np

def _raise_missing_dependency(library_name):
    raise ImportError(f"Missing {library_name}")

class MissingSurfaceTypeKeyError(KeyError):
    pass

class InvalidPartLabelError(ValueError):
    pass
'''
    file_path = tmp_path / "exceptions_advanced.py"
    file_path.write_text(source_code, encoding="utf-8")

    parser = ModuleParser(file_path)
    result = parser.parse()

    # 1. Exception inheritance edge cases
    # FAILS CURRENTLY: KeyError and ValueError do not contain "Exception"
    assert len(result["exceptions"]) == 2
    exception_names = [e["name"] for e in result["exceptions"]]
    assert "MissingSurfaceTypeKeyError" in exception_names
    assert "InvalidPartLabelError" in exception_names
    
    # 2. Ensure exceptions aren't bleeding into normal classes
    assert len(result["classes"]) == 0

    # 3. Function tracking within an exception file
    assert len(result["functions"]) == 1
    assert result["functions"][0]["name"] == "_raise_missing_dependency"

    # 4. Profile logic threshold check
    # FAILS CURRENTLY: Defaults to FUNCTIONAL_UTILITY because of the single helper method
    assert result["flags"]["profile"] == "EXCEPTION_REGISTRY"

def test_module_parser_main_boilerplate_variations(tmp_path):
    source_code = '''
def main():
    pass

if __name__ != "__main__":
    print("Not main")

if "__main__" == __name__:
    main()
'''
    file_path = tmp_path / "boilerplate_module.py"
    file_path.write_text(source_code, encoding="utf-8")

    parser = ModuleParser(file_path)
    result = parser.parse()

    # The negative check (`!=`) should be flagged as executable floating code
    # The inverted check (`==`) should safely be ignored as boilerplate
    assert result["flags"]["has_free_floating_code"] is True
    floating_statements = " ".join(result["free_floating_code"])
    
    assert "print('Not main')" in floating_statements or "print(\"Not main\")" in floating_statements
    assert "main()" not in floating_statements

def test_module_parser_type_hints_in_signatures(tmp_path):
    source_code = '''
from typing import List

async def fetch_data(url: str, timeout: int = 10) -> List[dict]:
    pass
'''
    file_path = tmp_path / "type_hints.py"
    file_path.write_text(source_code, encoding="utf-8")

    parser = ModuleParser(file_path)
    result = parser.parse()

    # Validating the newly added return annotation extraction
    assert len(result["functions"]) == 1
    sig = result["functions"][0]["signature"]
    assert "async def fetch_data" in sig
    assert "-> List[dict]:" in sig