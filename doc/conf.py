import sys
import os
import re

import sphinx

sys.path.insert(0, os.path.abspath('../game/'))

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = u'Joe\'s game engine'
copyright = u'2013, Joseph Lansdowne'
version = 'current'
release = 'current'

# Warn about broken links.
nitpicky = True

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%d %B %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'style.MyStyle'

autodoc_default_flags = ['members', 'undoc-members', 'show-inheritance']
autodoc_member_order = 'bysource'
autodoc_docstring_signature = True

pat1 = re.compile(r',\n\ *')
pat2 = re.compile(r'\n\ *')

def rm_sig (app, o_type, name, obj, options, lines):
    if o_type == 'module' and lines:
        lines.pop(0)
    if callable(obj):
        s = '\n'.join(lines)
        pattern = r'(?s)\n{}\(.*?\)(\s*\-\>[^\n]+)?\n'
        match = re.search(pattern.format(name.split('.')[-1]), s)
        if match is not None:
            s = s[:match.start()] + s[match.end():]
            lines[:] = s.split('\n')

def fix_sig (app, o_type, name, obj, options, sig, rtn):
    if callable(obj) and obj.__doc__ is not None:
        pattern = r'(?s)\n{}(\(.*?\))(\s*\-\>([^\n]+))?\n'
        match = re.search(pattern.format(name.split('.')[-1]), obj.__doc__)
        if match is not None:
            args, outer, rtn = match.groups()
            if rtn is not None:
                rtn = rtn.strip()
            args = re.sub(pat2, '', re.sub(pat1, ', ', args))
            return (args, rtn)

def skip (app, o_type, name, obj, skip, options):
    return skip or obj.__doc__ == ':inherit:'

def setup (app):
    app.connect('autodoc-process-docstring', rm_sig)
    app.connect('autodoc-process-docstring',
                sphinx.ext.autodoc.between('---NODOC---', exclude=True))
    app.connect('autodoc-process-signature', fix_sig)
    app.connect('autodoc-skip-member', skip)


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = 'Joe\'s game engine documentation'

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = 'favicon.ico'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = ''

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Joesgameenginedoc'
