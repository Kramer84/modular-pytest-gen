import os
import sys
# Insert project root into path so autodoc can parse source files statically
sys.path.insert(0, os.path.abspath(".."))

project = "Modular Pytest & Doc Gen"
copyright = "2026, kramer84"
author = "kramer84"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Strip type hints from signatures and move them to parameter descriptions
autodoc_typehints = "description"

# Optional: Prevents fully qualified paths from lengthening signatures (e.g., list vs typing.List)
autodoc_typehints_format = "short"