import pytest
from pathlib import Path
from modular_pytest_gen.resolver import ImportResolver

def test_resolver_standard_modules(tmp_path):
    src_dir = tmp_path / "src"
    otaf_dir = src_dir / "otaf"
    otaf_dir.mkdir(parents=True)
    
    # Create standard python files
    (otaf_dir / "geometry.py").write_text("class Point:\n    pass")
    (otaf_dir / "constants.py").write_text("PI = 3.14")
    
    resolver = ImportResolver(source_root=src_dir, import_prefix="otaf")
    
    # Verify logical mapping of physical files
    assert resolver.physical_to_logical[str(otaf_dir / "geometry.py")] == "otaf.geometry"
    
    # Verify path extraction for isolated objects
    assert resolver.get_import_path(otaf_dir / "geometry.py", "Point") == "otaf.geometry.Point"

def test_resolver_generic_reexports(tmp_path):
    src_dir = tmp_path / "src"
    pkg_dir = src_dir / "my_pkg"
    pkg_dir.mkdir(parents=True)
    
    # Simulate a generic `from .core import Engine`
    init_file = pkg_dir / "__init__.py"
    init_file.write_text("from .core import Engine\n")
    
    core_file = pkg_dir / "core.py"
    core_file.write_text("class Engine:\n    pass")
    
    resolver = ImportResolver(source_root=src_dir, import_prefix="my_pkg")
    
    # Even though Engine physically lives in `my_pkg.core`, the init re-exported it.
    # The resolver should promote it to the public `my_pkg.Engine` path.
    assert resolver.get_import_path(core_file, "Engine") == "my_pkg.Engine"

def test_resolver_otaf_bespoke_reexports(tmp_path):
    src_dir = tmp_path / "src"
    otaf_dir = src_dir / "otaf"
    otaf_dir.mkdir(parents=True)
    
    # Simulate the exact dynamic lazy loading from your codebase
    init_code = '''
_reexports = {
    "SystemOfConstraintsAssemblyModel": "_assembly_modeling",
    "GapMatrix": "_assembly_modeling"
}
'''
    (otaf_dir / "__init__.py").write_text(init_code)
    
    assembly_file = otaf_dir / "_assembly_modeling.py"
    assembly_file.write_text("class GapMatrix:\n    pass\nclass HelperTool:\n    pass")
    
    resolver = ImportResolver(source_root=src_dir, import_prefix="otaf")
    
    # Because GapMatrix is in the bespoke _reexports dict, it gets promoted to the public API
    assert resolver.get_import_path(assembly_file, "GapMatrix") == "otaf.GapMatrix"
    
    # Because HelperTool is NOT re-exported, it falls back to its physical private module path
    assert resolver.get_import_path(assembly_file, "HelperTool") == "otaf._assembly_modeling.HelperTool"

def test_resolver_out_of_bounds_file():
    resolver = ImportResolver(source_root=Path("fake_src"), import_prefix="fake")
    
    with pytest.raises(ValueError, match="outside the known source tree"):
        resolver.get_import_path(Path("completely/unrelated/path.py"), "SomeClass")
        
        
def test_resolver_alias_collision(tmp_path):
    src_dir = tmp_path / "src"
    otaf_dir = src_dir / "otaf"
    (otaf_dir / "api").mkdir(parents=True)
    (otaf_dir / "db").mkdir(parents=True)
    
    # API module exposes a Client
    (otaf_dir / "api" / "__init__.py").write_text("from .client import Client")
    api_client = otaf_dir / "api" / "client.py"
    api_client.write_text("class Client:\n    pass")
    
    # DB module exposes a completely different Client
    (otaf_dir / "db" / "__init__.py").write_text("from .client import Client")
    db_client = otaf_dir / "db" / "client.py"
    db_client.write_text("class Client:\n    pass")
    
    resolver = ImportResolver(source_root=src_dir, import_prefix="otaf")
    
    # If this fails, the 1D global alias dict has overwritten one of these paths
    assert resolver.get_import_path(api_client, "Client") == "otaf.api.Client"
    assert resolver.get_import_path(db_client, "Client") == "otaf.db.Client"

def test_resolver_ignores_local_imports_in_init(tmp_path):
    src_dir = tmp_path / "src"
    pkg_dir = src_dir / "pkg"
    pkg_dir.mkdir(parents=True)
    
    init_code = '''
def lazy_load_secret():
    from .hidden import SecretClass
    return SecretClass
'''
    (pkg_dir / "__init__.py").write_text(init_code)
    hidden_file = pkg_dir / "hidden.py"
    hidden_file.write_text("class SecretClass:\n    pass")
    
    resolver = ImportResolver(source_root=src_dir, import_prefix="pkg")
    
    # If this fails, ast.walk incorrectly grabbed the import inside the function
    # and promoted it to the public API namespace
    assert resolver.get_import_path(hidden_file, "SecretClass") == "pkg.hidden.SecretClass"

def test_resolver_subpackage_alias(tmp_path):
    # Tests the fix for the Sub-Package blindspot
    src_dir = tmp_path / "src"
    pkg_dir = src_dir / "pkg"
    sub_dir = pkg_dir / "core"
    sub_dir.mkdir(parents=True)
    
    # pkg/__init__.py imports from the core directory (which is a sub-package)
    (pkg_dir / "__init__.py").write_text("from .core import BaseException")
    
    # The actual physical file is inside the core/ sub-package
    core_init = sub_dir / "__init__.py"
    core_init.write_text("class BaseException:\n    pass")
    
    resolver = ImportResolver(source_root=src_dir, import_prefix="pkg")
    
    # The resolver should correctly recognize that "core" is a directory and map BaseException to it
    assert resolver.get_import_path(core_init, "BaseException") == "pkg.BaseException"