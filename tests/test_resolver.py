from pathlib import Path

import pytest

from modular_pytest_gen.resolver import ImportResolver


def test_resolver_standard_modules(tmp_path):
    src_dir = tmp_path / "src"
    otaf_dir = src_dir / "otaf"
    otaf_dir.mkdir(parents=True)
    (otaf_dir / "geometry.py").write_text("class Point:\n    pass")
    (otaf_dir / "constants.py").write_text("PI = 3.14")
    resolver = ImportResolver(source_root=src_dir, import_prefix="otaf")
    assert (
        resolver.physical_to_logical[str(otaf_dir / "geometry.py")] == "otaf.geometry"
    )
    assert (
        resolver.get_import_path(otaf_dir / "geometry.py", "Point")
        == "otaf.geometry.Point"
    )


def test_resolver_generic_reexports(tmp_path):
    src_dir = tmp_path / "src"
    pkg_dir = src_dir / "my_pkg"
    pkg_dir.mkdir(parents=True)
    init_file = pkg_dir / "__init__.py"
    init_file.write_text("from .core import Engine\n")
    core_file = pkg_dir / "core.py"
    core_file.write_text("class Engine:\n    pass")
    resolver = ImportResolver(source_root=src_dir, import_prefix="my_pkg")
    assert resolver.get_import_path(core_file, "Engine") == "my_pkg.Engine"


def test_resolver_otaf_bespoke_reexports(tmp_path):
    src_dir = tmp_path / "src"
    otaf_dir = src_dir / "otaf"
    otaf_dir.mkdir(parents=True)
    init_code = '\n_reexports = {\n    "SystemOfConstraintsAssemblyModel": "_assembly_modeling",\n    "GapMatrix": "_assembly_modeling"\n}\n'
    (otaf_dir / "__init__.py").write_text(init_code)
    assembly_file = otaf_dir / "_assembly_modeling.py"
    assembly_file.write_text("class GapMatrix:\n    pass\nclass HelperTool:\n    pass")
    resolver = ImportResolver(source_root=src_dir, import_prefix="otaf")
    assert resolver.get_import_path(assembly_file, "GapMatrix") == "otaf.GapMatrix"
    assert (
        resolver.get_import_path(assembly_file, "HelperTool")
        == "otaf._assembly_modeling.HelperTool"
    )


def test_resolver_out_of_bounds_file():
    resolver = ImportResolver(source_root=Path("fake_src"), import_prefix="fake")
    with pytest.raises(ValueError, match="outside the known source tree"):
        resolver.get_import_path(Path("completely/unrelated/path.py"), "SomeClass")


def test_resolver_alias_collision(tmp_path):
    src_dir = tmp_path / "src"
    otaf_dir = src_dir / "otaf"
    (otaf_dir / "api").mkdir(parents=True)
    (otaf_dir / "db").mkdir(parents=True)
    (otaf_dir / "api" / "__init__.py").write_text("from .client import Client")
    api_client = otaf_dir / "api" / "client.py"
    api_client.write_text("class Client:\n    pass")
    (otaf_dir / "db" / "__init__.py").write_text("from .client import Client")
    db_client = otaf_dir / "db" / "client.py"
    db_client.write_text("class Client:\n    pass")
    resolver = ImportResolver(source_root=src_dir, import_prefix="otaf")
    assert resolver.get_import_path(api_client, "Client") == "otaf.api.Client"
    assert resolver.get_import_path(db_client, "Client") == "otaf.db.Client"


def test_resolver_ignores_local_imports_in_init(tmp_path):
    src_dir = tmp_path / "src"
    pkg_dir = src_dir / "pkg"
    pkg_dir.mkdir(parents=True)
    init_code = "\ndef lazy_load_secret():\n    from .hidden import SecretClass\n    return SecretClass\n"
    (pkg_dir / "__init__.py").write_text(init_code)
    hidden_file = pkg_dir / "hidden.py"
    hidden_file.write_text("class SecretClass:\n    pass")
    resolver = ImportResolver(source_root=src_dir, import_prefix="pkg")
    assert (
        resolver.get_import_path(hidden_file, "SecretClass") == "pkg.hidden.SecretClass"
    )


def test_resolver_subpackage_alias(tmp_path):
    src_dir = tmp_path / "src"
    pkg_dir = src_dir / "pkg"
    sub_dir = pkg_dir / "core"
    sub_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("from .core import BaseException")
    core_init = sub_dir / "__init__.py"
    core_init.write_text("class BaseException:\n    pass")
    resolver = ImportResolver(source_root=src_dir, import_prefix="pkg")
    assert resolver.get_import_path(core_init, "BaseException") == "pkg.BaseException"
