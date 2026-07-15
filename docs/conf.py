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
    "sphinx.ext.napoleon",  # Translates NumPy-style docstrings into Sphinx
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]