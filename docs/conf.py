# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'HippoMetric'
copyright = '2025, Na Gao'
author = 'Na Gao'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = []

language = 'English'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

# 添加 Markdown 支持
extensions = [
    'myst_parser',
    'sphinx_rtd_theme',
]

# 支持 .md 文件
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# 使用 Read the Docs 主题
html_theme = 'sphinx_rtd_theme'
