import pytest
from pathlib import Path
from modular_pytest_gen.config import ProjectConfig, LayoutConfig
from modular_pytest_gen.layout import LayoutManager

def test_layout_manager_adjacent():
    config = ProjectConfig(
        layout=LayoutConfig(strategy="adjacent")
    )
    manager = LayoutManager(config)
    
    source_path = Path("src/my_pkg/utils/math.py")
    test_path = manager.get_test_file_path(source_path)
    
    # Should be in the exact same directory
    assert test_path == Path("src/my_pkg/utils/test_math.py")

def test_layout_manager_external_flat():
    config = ProjectConfig(
        layout=LayoutConfig(strategy="external", structure="flat", test_root="tests")
    )
    manager = LayoutManager(config)
    
    source_path = Path("src/my_pkg/utils/math.py")
    test_path = manager.get_test_file_path(source_path)
    
    # Should inject all intermediate directories to prevent collisions
    assert test_path == Path("tests/test_my_pkg_utils_math.py")

def test_layout_manager_external_nested_within_source_root():
    config = ProjectConfig(
        source_root="src",
        layout=LayoutConfig(strategy="external", structure="nested", test_root="tests")
    )
    manager = LayoutManager(config)
    
    source_path = Path("src/my_pkg/utils/math.py")
    test_path = manager.get_test_file_path(source_path)
    
    # Should mirror 'my_pkg/utils' under 'tests'
    assert test_path == Path("tests/my_pkg/utils/test_math.py")

def test_layout_manager_external_nested_outside_source_root():
    config = ProjectConfig(
        source_root="src",
        layout=LayoutConfig(strategy="external", structure="nested", test_root="tests")
    )
    manager = LayoutManager(config)
    
    # A file that isn't inside the defined 'src' root
    source_path = Path("scripts/tools/helper.py")
    test_path = manager.get_test_file_path(source_path)
    
    # Determine the expected safe prefix dynamically based on the runtime absolute path
    safe_prefix = str(source_path.parent.resolve()).replace("/", "_").replace("\\", "_").strip("_")
    expected_path = Path("tests") / f"test_external_{safe_prefix}_{source_path.name}"
    
    # Should gracefully fallback to a flattened absolute structure in the test root
    assert test_path == expected_path

def test_layout_manager_invalid_file():
    config = ProjectConfig()
    manager = LayoutManager(config)
    
    with pytest.raises(ValueError, match="Source path must be a Python file"):
        manager.get_test_file_path(Path("src/README.md"))

def test_layout_manager_invalid_strategy():
    config = ProjectConfig(
        layout=LayoutConfig(strategy="unknown_strat")
    )
    manager = LayoutManager(config)
    
    with pytest.raises(ValueError, match="Unknown layout strategy"):
        manager.get_test_file_path(Path("src/app.py"))

def test_layout_manager_invalid_structure():
    config = ProjectConfig(
        layout=LayoutConfig(strategy="external", structure="pyramid")
    )
    manager = LayoutManager(config)
    
    with pytest.raises(ValueError, match="Unknown layout structure"):
        manager.get_test_file_path(Path("src/app.py"))
        
def test_layout_manager_external_flat_collision_avoidance():
    config = ProjectConfig(
        source_root="src",
        layout=LayoutConfig(strategy="external", structure="flat", test_root="tests")
    )
    manager = LayoutManager(config)
    
    path1 = Path("src/core/math.py")
    path2 = Path("src/utils/math.py")
    path3 = Path("src/math.py")
    
    # If this fails, tests for utils/math.py will overwrite core/math.py
    assert manager.get_test_file_path(path1) == Path("tests/test_core_math.py")
    assert manager.get_test_file_path(path2) == Path("tests/test_utils_math.py")
    assert manager.get_test_file_path(path3) == Path("tests/test_math.py")
    
def test_layout_manager_external_flat_deep_nesting():
    config = ProjectConfig(
        source_root="src",
        layout=LayoutConfig(strategy="external", structure="flat", test_root="tests")
    )
    manager = LayoutManager(config)
    
    path = Path("src/otaf/core/solvers/math.py")
    assert manager.get_test_file_path(path) == Path("tests/test_otaf_core_solvers_math.py")