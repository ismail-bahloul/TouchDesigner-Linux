"""
TouchDesigner node type discovery and reference.

Provides auto-discovery of all available node types from the installed
TouchDesigner (via OPSnippets), plus parameter hints for common types.
"""

from __future__ import annotations

import os
import struct

from td_lib.utils import TD_BASE_DIR, error, info, success, warning
from td_lib.wine import WINE_PREFIX

_FAMILY_NAMES = {"POP", "TOP", "CHOP", "SOP", "DAT", "MAT", "COMP"}
"""The seven TouchDesigner operator families."""

_TEXT_HEADER_SIZE = 32
""".text files have a 32-byte binary header before the content."""


# ── .text file helpers ───────────────────────────────────────────────────────


def _build_text_header() -> bytes:
    """Build a minimal .text file header for new DAT nodes (32 bytes)."""
    header = bytearray(32)
    header[0:2] = b"2\n"              # UTF-8 text indicator
    header[2] = 0x2A                   # type flag '*' (42)
    header[6] = 1                      # flags (five 1s)
    header[10] = 1
    header[14] = 1
    header[18] = 1
    header[22] = 1
    header[26] = 2                     # string type
    header[30] = 4                     # sub-type / encoding
    return bytes(header)


def _parse_text_file(data: bytes) -> tuple[int, bytes]:
    """Parse a .text file. Returns (encoding_type_hint, text_content_bytes).

    The binary header is exactly 32 bytes.  We return the text portion.
    """
    if len(data) < 2:
        return (2, data)

    type_indicator = 2 if data[0:1] == b"2" else 0
    text_data = data[_TEXT_HEADER_SIZE:] if len(data) > _TEXT_HEADER_SIZE else b""
    return (type_indicator, text_data)


def _write_text_file(original: bytes, text: str) -> bytes:
    """Write a .text file from original binary data and new text content.

    Preserves the 32-byte binary header and replaces the text part.
    """
    if len(original) >= _TEXT_HEADER_SIZE:
        return original[:_TEXT_HEADER_SIZE] + text.encode("utf-8")
    elif original:
        return original.ljust(_TEXT_HEADER_SIZE, b"\0") + text.encode("utf-8")
    else:
        return _build_text_header() + text.encode("utf-8")


# ── Type discovery ───────────────────────────────────────────────────────────


def discover_types() -> dict[str, list[str]]:
    """Discover all available node types from the installed TouchDesigner.

    Scans the built-in OPSnippets directory. Returns a dict mapping
    family names to lists of subtype strings, sorted alphabetically.

    Returns:
        {"POP": ["null", "glsl", "sort", ...],
         "TOP": ["constant", "out", "render", ...],
         ...}
    """
    # Find TD installation directory in the Wine prefix
    program_files = os.path.join(WINE_PREFIX, "drive_c", "Program Files")
    if not os.path.isdir(program_files):
        raise RuntimeError(
            f"Program Files not found in Wine prefix ({program_files}).\n"
            "Run 'tact install' first."
        )

    td_dir = None
    for entry in sorted(os.listdir(program_files), reverse=True):
        if entry.startswith("TouchDesigner"):
            candidate = os.path.join(program_files, entry)
            if os.path.isdir(candidate):
                td_dir = candidate
                break

    if not td_dir:
        raise RuntimeError(
            "TouchDesigner installation not found in Wine prefix.\n"
            "Run 'tact install' first."
        )

    # Scan OPSnippets directory
    snippets_dir = os.path.join(td_dir, "Samples", "Learn", "OPSnippets", "Snippets")
    if not os.path.isdir(snippets_dir):
        raise RuntimeError(f"OPSnippets not found at {snippets_dir}")

    types: dict[str, list[str]] = {}
    for family in sorted(os.listdir(snippets_dir)):
        family_dir = os.path.join(snippets_dir, family)
        if not os.path.isdir(family_dir):
            continue
        if family not in _FAMILY_NAMES:
            continue

        subtypes: list[str] = []
        for fname in sorted(os.listdir(family_dir)):
            if not fname.endswith(".tox"):
                continue
            basename = fname[:-4]  # remove .tox
            if basename.upper().endswith(family.upper()):
                subtype = basename[:-len(family)]
            else:
                subtype = basename
            if subtype:
                subtypes.append(subtype)

        if subtypes:
            types[family] = subtypes

    return types


def discover_type_names() -> list[str]:
    """Discover all types and return them as 'FAMILY:subtype' strings."""
    result: list[str] = []
    for family, subtypes in sorted(discover_types().items()):
        for sub in subtypes:
            result.append(f"{family}:{sub}")
    return result


def print_node_types(family: str | None = None) -> None:
    """Print all available node types to stdout."""
    types = discover_types()

    for fam in sorted(types):
        if family and fam.upper() != family.upper():
            continue
        subtypes = types[fam]
        print(f"\n  {fam}  ({len(subtypes)} types)")
        print(f"  {'─' * (len(fam) + 20)}")

        # Print in columns
        cols = 4
        col_width = max(len(s) for s in subtypes) + 3
        for i in range(0, len(subtypes), cols):
            row = subtypes[i:i + cols]
            line = "  " + "".join(f"{s:<{col_width}}" for s in row)
            print(line)


def print_type_info(type_str: str) -> bool:
    """Print detailed info about a specific type. Returns False if not found."""
    if ":" not in type_str:
        # Try to find the type in any family
        types = discover_types()
        found = False
        for fam, subtypes in types.items():
            if type_str in subtypes:
                type_str = f"{fam}:{type_str}"
                found = True
                break
        if not found:
            return False

    parts = type_str.split(":", 1)
    family = parts[0].upper()
    subtype = parts[1]

    types = discover_types()
    if family not in types:
        error(f"Unknown family '{family}'. Valid: {', '.join(sorted(types))}")
        return False

    if subtype not in types[family]:
        error(f"Unknown type '{subtype}' in family '{family}'")
        return False

    print(f"\n  Type: {family}:{subtype}")
    print(f"  Family: {family}")
    print(f"  Full name: {subtype.capitalize()} {family}")
    print(f"  Keywords: {subtype}, {family.lower()}, {family.lower()}{subtype.capitalize()}")

    # Add parameter hints based on common patterns
    _print_param_hints(family, subtype)
    return True


def _print_param_hints(family: str, subtype: str) -> None:
    """Print common parameter hints for a node type."""
    print(f"  ── Common parameters ──")
    print(f"    tile x y w h        Position and size in network")
    print(f"    color r g b         Node color (0-1)")
    print(f"    flags = ...         Node flags")
    print(f"    inputs {{ 0 src }}    Input connections")

    # Family-specific hints
    hints = {
        "POP": {
            "null":       "  No specific params (passthrough)",
            "glsl":       "  glsl.parm: computedat, numthreadsmode, threadsinput, numelems",
            "sort":       "  sort.parm: ptmethod, pointattr, pointuint, pointseed",
            "pointgen":   "  pointgen.parm: (number of points, distribution)",
        },
        "TOP": {
            "null":       "  No specific params (passthrough)",
            "out":        "  out.parm: (display output settings)",
            "constant":   "  constant.parm: top (output), pageindex",
            "render":     "  render.parm: camera, resolution, etc.",
        },
        "CHOP": {
            "null":       "  No specific params (passthrough)",
            "lfo":        "  lfo.parm: frequency, amplitude, offset, phase",
            "constant":   "  constant.parm: value, channel count",
            "math":       "  math.parm: operation, inputs",
        },
        "DAT": {
            "text":       "  text.text: raw script/shader content (GLSL/Python)",
            "execute":    "  execute.text: Python callbacks (onCook, etc.)",
            "table":      "  table.table: tabular data",
        },
        "COMP": {
            "container":  "  Container: holds children, no special params",
            "base":       "  Similar to container, can be tox/top",
            "null":       "  Null COMP: passthrough container",
            "cam":        "  Camera COMP: lookat, resolution, etc.",
        },
        "SOP": {
            "null":       "  No specific params (passthrough)",
            "circle":     "  circle.parm: radius, divisions, etc.",
            "box":        "  box.parm: size, divisions, etc.",
        },
        "MAT": {
            "pbr":        "  pbr.parm: albedo, roughness, metallic, etc.",
            "phong":      "  phong.parm: diffuse, specular, etc.",
        },
    }
    fam_hints = hints.get(family)
    if fam_hints:
        hint = fam_hints.get(subtype)
        if hint:
            print(f"  ── Specific hints ──")
            print(f"    {hint}")
