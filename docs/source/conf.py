# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
from datetime import date
import tufup
from urllib import parse
import pathlib
import sys

try:
    import tomllib as toml  # part of standard library for python >=3.11
except ModuleNotFoundError:
    import tomli as toml  # 3rd-party (this is what setuptools uses)

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / 'src'
sys.path.insert(0, str(SRC_DIR))


# -- Project information -----------------------------------------------------
pyproject = toml.loads((ROOT_DIR / 'pyproject.toml').read_text())
project = pyproject['project']['name']
author = pyproject['project']['authors'][0]['name']
copyright = f'{date.today().year}, {author}'

# The full version, including alpha/beta/rc tags
release = tufup.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx_sitemap']


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Settings from the theme. See https://sphinx-rtd-theme.readthedocs.io/en/stable/configuring.html
html_theme_options = {
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 2,
    'includehidden': True,
    'titles_only': False,
}

# config for autodoc. See https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_default_options
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': False,
    'inherited-members': True,
}

#  find documentation url
project_urls = list(pyproject['project']['urls'].values())
html_baseurl = ''
for url in project_urls:
    if 'readthedocs' in url:
        parsed_url = parse.urlparse(url)
        html_baseurl = f'{parsed_url.scheme}://{parsed_url.netloc}'
html_extra_path = ['robots.txt']
