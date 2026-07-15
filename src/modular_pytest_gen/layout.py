from pathlib import Path
from typing import Union

from .config import ProjectConfig


class LayoutManager:
    r"""
    Construct a LayoutManager instance.
    
    Initializes the LayoutManager with a ProjectConfig object to manage
    test file paths based on project configuration.
    
    Parameters
    ----------
    config : ProjectConfig
        The project configuration object containing layout strategy and
        structure settings.
    
    Methods
    -------
    get_test_file_path :
        Derive the test file path from the source file path based on the
        project configuration.
    """

    def __init__(self, config: ProjectConfig):
        r"""
        Initialize the project configuration.
        
        Sets up the project configuration by storing the provided
        `ProjectConfig` object.
        
        Warnings
        --------
        Ensure the `ProjectConfig` object is valid and contains all
        necessary configuration parameters.
        
        See Also
        --------
        ProjectConfig :
            The configuration object used to initialize the project.
        
        Notes
        -----
        The `ProjectConfig` object must be properly initialized before
        passing it to this method.
        """

        self.config = config

    def get_test_file_path(self, source_file_path: Union[str, Path]) -> Path:
        r"""
        Generate test file path from source file path and configuration.
        
        Parameters
        ----------
        source_file_path : Union[str, Path]
            The path to the source file for which the test file path is to
            be generated.
        
        Returns
        -------
        Path
            The generated test file path as a Path object.
        
        Raises
        ------
        ValueError
            If the source file path is not a Python file.
        
            If the layout strategy or structure is unknown.
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
