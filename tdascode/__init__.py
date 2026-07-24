"""
TD-as-Code — programmatic TouchDesigner project manipulation.

Provides expand/collapse wrappers, a TDProject class and a TDNode class
for reading, modifying and writing .toe projects entirely from Python.

Usage:
    from tdascode import expand, collapse, TDProject

    proj = expand("my_project.toe")
    proj.add_node("/", "my_noise", type="POP:noise")
    proj.connect("my_noise", "null1")
    proj.set_param("my_noise", "size", 2.5)
    collapse("my_project.toe")

CLI:
    td-install --expand project.toe        # → .dir/
    td-install --collapse project.toe      # → .toe
    td-install --info project.toe          # show structure
    td-install --list-types                # available node types
    td-install --type-info "POP:null"      # type details
"""

from tdascode.core import expand, collapse, TDProject, TDNode
from tdascode.types import (
    discover_types,
    discover_type_names,
    print_node_types,
    print_type_info,
    _parse_text_file,
    _write_text_file,
)
