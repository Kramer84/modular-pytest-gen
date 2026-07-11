import ast
from pathlib import Path

import pytest

from modular_pytest_gen.parser import ModuleParser


def test_module_parser_functional_utility(tmp_path):
    source_code = '\nimport os\nfrom typing import List\n\ndef sample_function(x: int) -> int:\n    """A sample function."""\n    return x * 2\n'
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
    source_code = '\n__all__ = ["MyError", "MyClass"]\n\nclass MyError(Exception):\n    """Custom error class."""\n    pass\n\nclass MyClass:\n    def __init__(self):\n        self.val = 1\n'
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
    source_code = '\nMAX_RETRIES = 5\ntimeout = 10\n\nif __name__ == "__main__":\n    print("Running")\n'
    file_path = tmp_path / "const_module.py"
    file_path.write_text(source_code, encoding="utf-8")
    parser = ModuleParser(file_path)
    result = parser.parse()
    assert "MAX_RETRIES" in result["constants"]
    assert result["constants"]["MAX_RETRIES"] == "5"
    assert result["flags"]["has_free_floating_code"] is True
    assert any(("timeout = 10" in code for code in result["free_floating_code"]))
    assert result["flags"]["profile"] == "CONSTANT_REGISTRY"


def test_module_parser_constants_advanced(tmp_path):
    source_code = 'from __future__ import annotations\n# -*- coding: utf-8 -*-\n\n__author__ = "Kramer84"\n__all__ = [\n    "BASE_SURFACE_TYPES",\n    "SURFACE_DIRECTIONS"\n]\n\nimport re\nimport numpy as np\n\n"""\n_constants.py\nDefines constants.\n"""\n\nBASE_SURFACE_TYPES = ["plane", "cylinder", "cone", "sphere"]\nSURFACE_DIRECTIONS = ["centripetal", "centrifugal"]\n'
    file_path = tmp_path / "constants_advanced.py"
    file_path.write_text(source_code, encoding="utf-8")
    parser = ModuleParser(file_path)
    result = parser.parse()
    assert "BASE_SURFACE_TYPES" in result["constants"]
    assert "SURFACE_DIRECTIONS" in result["constants"]
    assert result["flags"]["has_dunder_all"] is True
    assert "BASE_SURFACE_TYPES" in result["dunder_all"]
    assert result["flags"]["has_free_floating_code"] is False
    assert len(result["free_floating_code"]) == 0
    assert result["flags"]["profile"] == "CONSTANT_REGISTRY"


def test_module_parser_exceptions_and_dependencies(tmp_path):
    source_code = 'from __future__ import annotations\nimport numpy as np\n\ndef _raise_missing_dependency(library_name):\n    raise ImportError(f"Missing {library_name}")\n\nclass MissingSurfaceTypeKeyError(KeyError):\n    pass\n\nclass InvalidPartLabelError(ValueError):\n    pass\n'
    file_path = tmp_path / "exceptions_advanced.py"
    file_path.write_text(source_code, encoding="utf-8")
    parser = ModuleParser(file_path)
    result = parser.parse()
    assert len(result["exceptions"]) == 2
    exception_names = [e["name"] for e in result["exceptions"]]
    assert "MissingSurfaceTypeKeyError" in exception_names
    assert "InvalidPartLabelError" in exception_names
    assert len(result["classes"]) == 0
    assert len(result["functions"]) == 1
    assert result["functions"][0]["name"] == "_raise_missing_dependency"
    assert result["flags"]["profile"] == "EXCEPTION_REGISTRY"


def test_module_parser_main_boilerplate_variations(tmp_path):
    source_code = '\ndef main():\n    pass\n\nif __name__ != "__main__":\n    print("Not main")\n\nif "__main__" == __name__:\n    main()\n'
    file_path = tmp_path / "boilerplate_module.py"
    file_path.write_text(source_code, encoding="utf-8")
    parser = ModuleParser(file_path)
    result = parser.parse()
    assert result["flags"]["has_free_floating_code"] is True
    floating_statements = " ".join(result["free_floating_code"])
    assert (
        "print('Not main')" in floating_statements
        or 'print("Not main")' in floating_statements
    )
    assert "main()" not in floating_statements


def test_module_parser_type_hints_in_signatures(tmp_path):
    source_code = "\nfrom typing import List\n\nasync def fetch_data(url: str, timeout: int = 10) -> List[dict]:\n    pass\n"
    file_path = tmp_path / "type_hints.py"
    file_path.write_text(source_code, encoding="utf-8")
    parser = ModuleParser(file_path)
    result = parser.parse()
    assert len(result["functions"]) == 1
    sig = result["functions"][0]["signature"]
    assert "async def fetch_data" in sig
    assert "-> List[dict]:" in sig
