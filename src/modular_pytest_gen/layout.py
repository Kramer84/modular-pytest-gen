from pathlib import Path
from typing import Union

from .config import ProjectConfig


class LayoutManager:
    """Manages the calculation of test file paths based on defined project layout strategies.

    This class serves as a central resolver to determine where test files should be
    located relative to source files, supporting configurations like adjacent
    file placement or centralized external test directories.

    Attributes:
        config (ProjectConfig): The configuration object containing project layout
            definitions (e.g., strategy type, test root path, source root path).
    """

    def __init__(self, config: ProjectConfig):
        """Initializes the manager with the project's configuration.

        Args:
            config (ProjectConfig): The configuration instance governing layout behavior.
        """
        self.config = config

    def get_test_file_path(self, source_file_path: Union[str, Path]) -> Path:
        """Calculates the absolute or relative filesystem path for a corresponding test file.

        The method implements two primary strategies:
        1. 'adjacent': Places the test file in the same directory as the source file.
        2. 'external': Places the test file in a dedicated test directory, with options
        to either flatten the path or mirror the nested source structure.

        Args:
            source_file_path (Union[str, Path]): The path to the source file (e.g., 'path/to/module.py').

        Returns:
            Path: The calculated path where the test file should be generated.

        Raises:
            ValueError: If the source path does not point to a Python file, if the layout
                strategy is unsupported, or if the layout structure is undefined.
        """
        source_path = Path(source_file_path).resolve()
        if not source_path.name.endswith(".py"):
            raise ValueError(f"Source path must be a Python file: {source_path}")
        strategy = self.config.layout.strategy.lower()
        if strategy == "adjacent":
            return source_path.parent / f"test_{source_path.name}"
        elif strategy == "external":
            test_root = Path(self.config.layout.test_root)
            source_root = Path(self.config.source_root).resolve()
            try:
                relative_dir = source_path.parent.relative_to(source_root)
            except ValueError:
                safe_prefix = (
                    str(source_path.parent)
                    .replace("/", "_")
                    .replace("\\", "_")
                    .strip("_")
                )
                return test_root / f"test_external_{safe_prefix}_{source_path.name}"
            structure = self.config.layout.structure.lower()
            if structure == "flat":
                if str(relative_dir) == ".":
                    flat_name = f"test_{source_path.name}"
                else:
                    prefix = str(relative_dir).replace("/", "_").replace("\\", "_")
                    flat_name = f"test_{prefix}_{source_path.name}"
                return test_root / flat_name
            elif structure == "nested":
                return test_root / relative_dir / f"test_{source_path.name}"
            else:
                raise ValueError(
                    f"Unknown layout structure: '{structure}'. Must be 'flat' or 'nested'."
                )
        else:
            raise ValueError(
                f"Unknown layout strategy: '{strategy}'. Must be 'adjacent' or 'external'."
            )
