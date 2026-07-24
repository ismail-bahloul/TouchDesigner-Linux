"""
CLI handlers for TD-as-Code subcommands.

Called from the tact entry point when --expand, --collapse, --info,
--list-types, or --type-info is used.
"""

from __future__ import annotations

import sys
from pathlib import Path

from td_lib.utils import error

from tdascode.core import expand, collapse, TDProject
from tdascode.types import (
    discover_types,
    discover_type_names,
    print_node_types,
    print_type_info,
    _FAMILY_NAMES,
)


def dispatch_code_action(args) -> int:
    """Dispatch a code action based on args.code_action."""
    handlers = {
        "expand": cli_expand,
        "collapse": cli_collapse,
        "info": cli_info,
        "list_types": cli_list_types,
    }
    handler = handlers.get(args.code_action)
    if handler:
        return handler(args)
    error(f"Unknown code action: {args.code_action}")
    return 1


def dispatch_type_info(args) -> int:
    """Handle --type-info."""
    return cli_type_info(args)


# ── CLI handlers ─────────────────────────────────────────────────────────────


def cli_expand(args) -> int:
    """Handler for 'tact --expand <file.toe>'.

    Leaves the .dir folder on disk so the user can inspect/edit files.
    """
    if not args.run:
        error("Usage: tact --expand <file.toe>")
        return 1
    try:
        proj = expand(args.run)
        from td_lib.utils import info as log_info
        log_info(f"Project: {len(proj.nodes)} nodes, "
                 f"{len(proj.meta_files)} meta files")
        print(f"  .dir folder: {Path(proj.dir_path).name}/")
        print(f"  .toc file:   {Path(proj.toc_path).name}")
        print()
        # List top-level nodes
        for key, node in sorted(proj.nodes.items()):
            if not node.parent_path or "/" not in node.parent_path:
                print(f"  {key:<35} {node.type}")
        return 0
    except Exception as e:
        error(str(e))
        return 1


def cli_collapse(args) -> int:
    """Handler for 'tact --collapse <file.toe>'."""
    if not args.run:
        error("Usage: tact --collapse <file.toe>")
        return 1
    try:
        collapse(args.run)
        return 0
    except Exception as e:
        error(str(e))
        return 1


def cli_info(args) -> int:
    """Handler for 'tact --info <file.toe>'."""
    if not args.run:
        error("Usage: tact --info <file.toe>")
        return 1
    try:
        proj = expand(args.run)
        print(f"\n{'='*60}")
        print(f"  Project: {Path(args.run).name}")
        print(f"  Nodes:   {len(proj.nodes)}")
        print(f"{'='*60}\n")

        containers = {}
        plain = []
        for key, node in sorted(proj.nodes.items()):
            if node.children is not None:
                containers[key] = node
            elif not node.parent_path or "/" not in node.parent_path:
                plain.append(node)

        if plain:
            print("  Nodes at root level:")
            for node in plain:
                inp = f" \u2190 {list(node.inputs.values())[0]}" if node.inputs else ""
                print(f"    {node.name:<30} {node.type}{inp}")

        if containers:
            print(f"\n  Containers:")
            for key, node in sorted(containers.items()):
                n_children = len(node.children) if node.children else 0
                print(f"    {key:<30} {node.type}  ({n_children} children)")

        proj.cleanup()
        return 0
    except Exception as e:
        error(str(e))
        return 1


def cli_list_types(args) -> int:
    """Handler for 'tact --list-types'."""
    try:
        print("\n  Available TouchDesigner node types")
        print(f"  {'=' * 40}")
        print_node_types(getattr(args, 'type_info', None))
        print()
        return 0
    except Exception as e:
        error(str(e))
        return 1


def cli_type_info(args) -> int:
    """Handler for 'tact --type-info <type>'."""
    if not args.type_info:
        error("Usage: tact --type-info <type>")
        error("  Examples: --type-info 'POP:null'   --type-info 'glsl'   --type-info 'TOP'")
        return 1
    try:
        type_str = args.type_info
        # If it's just a family name, list types in that family
        if type_str.upper() in _FAMILY_NAMES:
            print_node_types(type_str.upper())
            return 0
        if print_type_info(type_str):
            return 0
        # Try searching by family prefix
        for fam in _FAMILY_NAMES:
            if print_type_info(f"{fam}:{type_str}"):
                return 0
        error(f"Type '{type_str}' not found. Use --list-types to see all types.")
        return 1
    except Exception as e:
        error(str(e))
        return 1
