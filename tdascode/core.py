"""
Core engine for TouchDesigner as-code manipulation.

Provides expand/collapse, TDNode, TDProject, and all file format parsers.
"""

from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Import tact infrastructure
from td_lib.utils import TD_BASE_DIR, error, info, success, warning
from td_lib.wine import WINE_PREFIX, RUNNER_DIR

# ── Wine helpers ─────────────────────────────────────────────────────────────


def _find_toe_tool(name: str) -> Optional[str]:
    """Find toeexpand.exe or toecollapse.exe in the Wine prefix."""
    try:
        result = subprocess.run(
            ["find", WINE_PREFIX, "-type", "f", "-iname", f"{name}.exe"],
            capture_output=True, text=True, timeout=30,
        )
        paths = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
        return str(Path(paths[0])) if paths else None
    except Exception:
        return None


def _wine_path(linux_path: str) -> str:
    """Convert a Linux path to a Wine-style Z: path."""
    return f"z:{linux_path}"


def _run_wine(exe_path: str, args: list[str]) -> subprocess.CompletedProcess:
    """Run a Windows exe via the tact Wine runner."""
    wine64 = os.path.join(RUNNER_DIR, "bin", "wine64")
    if not os.path.isfile(wine64):
        raise RuntimeError(f"wine64 not found at {wine64}")
    cmd = [wine64, exe_path] + args
    env = {**os.environ, "WINEPREFIX": WINE_PREFIX}
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)


# ── Core API: expand / collapse ──────────────────────────────────────────────


def expand(toe_path: str) -> "TDProject":
    """Expand a .toe file into a .dir folder, parse it, return a TDProject.

    The caller should call project.cleanup() after collapse() to remove
    the temporary .dir folder, or call project.close() to do both.
    """
    toe_path = str(Path(toe_path).resolve())

    if not toe_path.endswith(".toe") and not toe_path.endswith(".tox"):
        raise ValueError(f"Expected a .toe or .tox file, got: {toe_path}")
    if not os.path.isfile(toe_path):
        raise FileNotFoundError(f"File not found: {toe_path}")

    toe_expand = _find_toe_tool("toeexpand")
    if not toe_expand:
        raise RuntimeError(
            "toeexpand.exe not found in Wine prefix.\n"
            "Is TouchDesigner installed? (run 'tact install')"
        )

    dir_path = toe_path + ".dir"
    toc_path = toe_path + ".toc"

    # Clean previous expansion
    shutil.rmtree(dir_path, ignore_errors=True)
    Path(toc_path).unlink(missing_ok=True)

    info(f"Expanding {Path(toe_path).name} ...")
    result = _run_wine(toe_expand, [_wine_path(toe_path)])

    if not os.path.isdir(dir_path):
        err = result.stderr.strip() or "unknown error"
        raise RuntimeError(f"toeexpand failed: {err}")

    success(f"Expanded \u2192 {Path(toe_path).name}.dir/  ({len(os.listdir(dir_path))} items)")
    return TDProject.from_dir(dir_path, toc_path)


def collapse(toe_path: str) -> None:
    """Collapse a .dir folder back into a .toe file.

    The .dir folder must exist alongside the .toe (produced by expand()).
    The .toe will be rebuilt. A backup of the old .toe is created automatically
    by toecollapse (named .bkpN).
    """
    toe_path = str(Path(toe_path).resolve())

    if not toe_path.endswith(".toe") and not toe_path.endswith(".tox"):
        raise ValueError(f"Expected a .toe or .tox file, got: {toe_path}")

    dir_path = toe_path + ".dir"
    if not os.path.isdir(dir_path):
        raise FileNotFoundError(
            f"No .dir folder found at {dir_path}. "
            "Run expand() first, or make sure the .dir exists."
        )

    toe_collapse = _find_toe_tool("toecollapse")
    if not toe_collapse:
        raise RuntimeError(
            "toecollapse.exe not found in Wine prefix.\n"
            "Is TouchDesigner installed? (run 'tact install')"
        )

    info(f"Collapsing {Path(toe_path).name}.dir/ \u2192 {Path(toe_path).name} ...")
    result = _run_wine(toe_collapse, [_wine_path(toe_path)])

    if not os.path.isfile(toe_path):
        err = result.stderr.strip() or "unknown error"
        raise RuntimeError(f"toecollapse failed: {err}")

    success(f"Collapsed \u2192 {Path(toe_path).name}")


# ── .n file parser / writer ──────────────────────────────────────────────────


def _parse_n_file(content: str) -> dict:
    """Parse a .n file into a structured dict."""
    node: dict = {}
    node["inputs"] = {}
    node["flags"] = ""
    node["color"] = (0.67, 0.67, 0.67)
    node["view"] = ""
    node["opview"] = ""
    node["children"] = None  # None = not a COMP container

    lines = content.strip().split("\n")
    if not lines:
        return node

    # First line: TYPE:subtype
    first = lines[0].strip()
    if ":" in first:
        node["type"] = first
    else:
        node["type"] = first

    i = 1
    while i < len(lines):
        line = lines[i].rstrip()
        if line == "end":
            break
        if line.startswith("tile "):
            parts = line.split()
            node["tile"] = (float(parts[1]), float(parts[2]),
                            float(parts[3]), float(parts[4]))
        elif line.startswith("v "):
            parts = line.split()
            node["v"] = (float(parts[1]), float(parts[2]), float(parts[3]))
        elif line.startswith("flags ="):
            node["flags"] = line[len("flags ="):].strip()
        elif line.startswith("color "):
            parts = line.split()
            node["color"] = (float(parts[1]), float(parts[2]), float(parts[3]))
        elif line.startswith("view "):
            node["view"] = line
        elif line.startswith("opview "):
            node["opview"] = line
        elif line == "inputs":
            # Parse inputs block
            i += 1
            while i < len(lines):
                inp_line = lines[i].strip()
                if inp_line == "}":
                    break
                parts = inp_line.split(None, 1)
                if len(parts) >= 1 and parts[0].isdigit():
                    idx = int(parts[0])
                    name = parts[1].strip() if len(parts) > 1 else ""
                    node["inputs"][idx] = name
                i += 1
        elif line == "children":
            # Parse children block (COMPs)
            node["children"] = []
            i += 1
            while i < len(lines):
                child_line = lines[i].strip()
                if child_line == "}":
                    break
                if child_line:
                    node["children"].append(child_line)
                i += 1
        elif line == "end":
            break
        i += 1

    return node


def _write_n_file(node_info: dict) -> str:
    """Write a .n file from a structured dict."""
    lines = []
    lines.append(node_info.get("type", "POP:null"))
    if "v" in node_info:
        v = node_info["v"]
        lines.append(f"v {v[0]} {v[1]} {v[2]}")
    t = node_info.get("tile", (-100, -100, 130, 90))
    lines.append(f"tile {t[0]} {t[1]} {t[2]} {t[3]}")
    flags = node_info.get("flags", "")
    if flags:
        lines.append(f"flags = {flags}")
    inputs = node_info.get("inputs", {})
    if inputs:
        lines.append("inputs")
        lines.append("{")
        for idx in sorted(inputs.keys()):
            lines.append(f"{idx} \t{inputs[idx]}")
        lines.append("}")
    color = node_info.get("color", (0.67, 0.67, 0.67))
    lines.append(f"color {color[0]} {color[1]} {color[2]}")
    if node_info.get("view"):
        lines.append(node_info["view"])
    if node_info.get("opview"):
        lines.append(node_info["opview"])
    if node_info.get("children") is not None:
        lines.append("children")
        lines.append("{")
        for c in node_info["children"]:
            lines.append(c)
        lines.append("}")
    lines.append("end")
    return "\n".join(lines) + "\n"


def _parse_toc(toc_path: str) -> list[str]:
    """Read the .toc (table of contents) file, return list of file paths."""
    if not os.path.isfile(toc_path):
        return []
    with open(toc_path) as f:
        return [line.strip() for line in f if line.strip()]


def _write_toc(toc_path: str, entries: list[str]) -> None:
    """Write the .toc file."""
    with open(toc_path, "w") as f:
        for entry in entries:
            f.write(entry + "\n")


# ── .parm file parser / writer ───────────────────────────────────────────────


def _parse_parm_file(content: str) -> list[dict]:
    """Parse a .parm file into a list of param dicts.

    Format:
    ?
    pageindex 0 1
    name flags value [expression]
    ?
    """
    params: list[dict] = []
    if not content or content.strip() == "":
        return params

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line or line == "?":
            continue
        parts = line.split(None, 2)
        if len(parts) == 3:
            params.append({
                "name": parts[0],
                "flags": int(parts[1]),
                "value": parts[2],
            })
        elif len(parts) == 2:
            params.append({
                "name": parts[0],
                "flags": int(parts[1]),
                "value": "",
            })
        elif len(parts) == 1:
            if parts[0].startswith("pageindex"):
                params.append({"name": parts[0], "flags": 0, "value": ""})
            else:
                params.append({"name": parts[0], "flags": 0, "value": ""})

    return params


def _write_parm_file(params: list[dict]) -> str:
    """Write a .parm file from a list of param dicts."""
    if not params:
        return ""
    lines = ["?"]
    for p in params:
        name = p["name"]
        flags = p.get("flags", 0)
        value = p.get("value", "")
        expression = p.get("expression")
        if expression is not None:
            lines.append(f"{name} {flags} {value} {expression}")
        elif value is not None:
            lines.append(f"{name} {flags} {value}")
        else:
            lines.append(f"{name} {flags} ")
    lines.append("?")
    return "\n".join(lines) + "\n"


def _set_param_in_list(params: list[dict], name: str, value: str,
                       flags: int = 0, expression: str | None = None) -> bool:
    """Set a parameter value in the list. Returns True if found."""
    for p in params:
        if p["name"] == name:
            p["value"] = value
            p["flags"] = flags
            if expression is not None:
                p["expression"] = expression
            else:
                p.pop("expression", None)
            return True
    return False


# ── TDNode ───────────────────────────────────────────────────────────────────


@dataclass
class TDNode:
    """Represents a single node in an expanded TouchDesigner project."""

    name: str
    """Short name of the node (e.g. 'null1', 'glsl1_compute')."""

    parent_path: str
    """Path relative to project root, excluding own name (e.g. 'Pop_glsl_sort')."""

    type: str = "POP:null"
    """Node type string (e.g. 'POP:null', 'TOP:render', 'COMP:container')."""

    tile: tuple[float, float, float, float] = (-100, -100, 130, 90)
    """Position (x, y) and size (w, h) in the network editor."""

    inputs: dict[int, str] = field(default_factory=dict)
    """Input connections: {input_index: source_node_name}."""

    color: tuple[float, float, float] = (0.67, 0.67, 0.67)
    """Node color as (r, g, b) in 0-1 range."""

    flags: str = ""
    """Node flags string (e.g. 'current on viewer 1 parlanguage 0')."""

    params: list[dict] = field(default_factory=list)
    """List of param dicts: {name, flags, value, expression?}."""

    panel: str = ""
    """Raw .panel file content, if any."""

    cparm: str = ""
    """Raw .cparm file content (custom parameters), if any."""

    text_data: bytes = b""
    """Raw .text file bytes (for DAT nodes), if any."""

    extra_files: dict[str, bytes] = field(default_factory=dict)
    """Other associated files keyed by extension (chop, ts, gnode, feedback, ...)
    stored as raw bytes."""

    children: list[str] | None = None
    """List of child node names if this is a COMP:container, None otherwise."""

    # Internal: parsed .n metadata not exposed as attributes
    _v: tuple[float, float, float] | None = None
    _view: str = ""
    _opview: str = ""

    @property
    def full_path(self) -> str:
        """Full dot-path like 'Pop_glsl_sort.null1'."""
        if self.parent_path:
            return f"{self.parent_path}.{self.name}"
        return self.name

    @property
    def dir_rel_path(self) -> str:
        """Path relative to the .dir folder (e.g. 'Pop_glsl_sort/null1')."""
        if self.parent_path:
            return f"{self.parent_path}/{self.name}"
        return self.name

    def to_n_content(self) -> str:
        """Generate the .n file content for this node."""
        node_info = {
            "type": self.type,
            "tile": self.tile,
            "inputs": self.inputs,
            "color": self.color,
            "flags": self.flags,
            "view": self._view,
            "opview": self._opview,
            "children": self.children,
        }
        if self._v:
            node_info["v"] = self._v
        return _write_n_file(node_info)

    def to_parm_content(self) -> str:
        """Generate the .parm file content."""
        return _write_parm_file(self.params)

    def write_to(self, dir_path: str) -> list[str]:
        """Write all this node's files into dir_path.
        Returns list of relative paths written (for the .toc)."""
        written: list[str] = []
        rel = self.dir_rel_path
        node_dir = os.path.join(dir_path, rel)
        os.makedirs(node_dir, exist_ok=True)

        # .n file
        n_path = os.path.join(dir_path, f"{rel}.n")
        with open(n_path, "w") as f:
            f.write(self.to_n_content())
        written.append(f"{rel}.n")

        # .parm file
        if self.params:
            parm_path = os.path.join(dir_path, f"{rel}.parm")
            with open(parm_path, "w") as f:
                f.write(self.to_parm_content())
            written.append(f"{rel}.parm")

        # .panel file
        if self.panel:
            panel_path = os.path.join(dir_path, f"{rel}.panel")
            with open(panel_path, "w") as f:
                f.write(self.panel)
            written.append(f"{rel}.panel")

        # .cparm file
        if self.cparm:
            cparm_path = os.path.join(dir_path, f"{rel}.cparm")
            with open(cparm_path, "w") as f:
                f.write(self.cparm)
            written.append(f"{rel}.cparm")

        # .text file
        if self.text_data:
            text_path = os.path.join(dir_path, f"{rel}.text")
            with open(text_path, "wb") as f:
                f.write(self.text_data)
            written.append(f"{rel}.text")

        # Extra files
        for ext, data in self.extra_files.items():
            extra_path = os.path.join(dir_path, f"{rel}.{ext}")
            with open(extra_path, "wb") as f:
                f.write(data)
            written.append(f"{rel}.{ext}")

        return written


# ── TDProject ────────────────────────────────────────────────────────────────


class TDProject:
    """An expanded TouchDesigner project (.toe \u2192 .dir folder).

    Provides high-level manipulation of nodes, parameters, and connections.
    After modifications, call write() to sync to disk, then collapse() to rebuild.
    """

    def __init__(self, dir_path: str, toc_path: str):
        self.dir_path = str(Path(dir_path).resolve())
        self.toc_path = str(Path(toc_path).resolve())
        self.nodes: dict[str, TDNode] = {}
        self.meta_files: dict[str, str | bytes] = {}
        """Meta files at the .dir root: .build, .start, .root, .parm,
        .application, .grps stored as text (str) or binary (bytes)."""

    # ── Factory ──────────────────────────────────────────────────────────────

    @classmethod
    def from_dir(cls, dir_path: str, toc_path: str) -> "TDProject":
        """Parse an expanded .dir folder into a TDProject."""
        from tdascode.types import _parse_text_file  # avoid circular import

        proj = cls(dir_path, toc_path)
        toc = _parse_toc(toc_path)

        for rel_path in toc:
            abs_path = os.path.join(dir_path, rel_path)
            if not os.path.isfile(abs_path):
                continue

            name, ext = _split_path_ext(rel_path)
            parent = _parent_path(rel_path)
            ext = ext.lstrip(".")

            # Meta files (start with dot, name is the extension)
            if rel_path.startswith(".") and "/" not in rel_path:
                with open(abs_path, "rb") as f:
                    data = f.read()
                try:
                    proj.meta_files[rel_path] = data.decode("utf-8")
                except UnicodeDecodeError:
                    proj.meta_files[rel_path] = data
                continue

            if not name:
                continue

            # Get or create the node
            node_key = f"{parent}/{name}" if parent else name
            if node_key not in proj.nodes:
                proj.nodes[node_key] = TDNode(
                    name=name,
                    parent_path=parent,
                )
            node = proj.nodes[node_key]

            if ext == "n":
                with open(abs_path) as f:
                    node_info = _parse_n_file(f.read())
                node.type = node_info.get("type", node.type)
                node.tile = node_info.get("tile", node.tile)
                node.inputs = node_info.get("inputs", {})
                node.color = node_info.get("color", node.color)
                node.flags = node_info.get("flags", "")
                node._view = node_info.get("view", "")
                node._opview = node_info.get("opview", "")
                node._v = node_info.get("v")
                node.children = node_info.get("children")
            elif ext == "parm":
                with open(abs_path) as f:
                    node.params = _parse_parm_file(f.read())
            elif ext == "panel":
                with open(abs_path) as f:
                    node.panel = f.read()
            elif ext == "cparm":
                with open(abs_path) as f:
                    node.cparm = f.read()
            elif ext == "text":
                with open(abs_path, "rb") as f:
                    node.text_data = f.read()
            else:
                with open(abs_path, "rb") as f:
                    node.extra_files[ext] = f.read()

        return proj

    # ── Node management ──────────────────────────────────────────────────────

    def get_node(self, path: str) -> Optional[TDNode]:
        """Get a node by its full path, e.g. 'Pop_glsl_sort/glsl1' or 'cntrl'."""
        norm = path.replace(".", "/")
        node = self.nodes.get(norm)
        if node:
            return node
        # Try matching by short name
        for n in self.nodes.values():
            if n.name == norm.split("/")[-1]:
                return n
        return None

    def add_node(self, parent_path: str, name: str, *,
                 type: str = "POP:null",
                 tile: tuple[float, float, float, float] = (-100, -100, 130, 90),
                 inputs: dict[int, str] | None = None,
                 color: tuple[float, float, float] = (0.67, 0.67, 0.67),
                 flags: str = "parlanguage 0",
                 params: list[dict] | None = None,
                 panel: str = "",
                 text: str = "",
                 ) -> TDNode:
        """Add a new node to the project."""
        from tdascode.types import _build_text_header  # avoid circular import

        node_key = f"{parent_path}/{name}" if parent_path else name
        if node_key in self.nodes:
            raise ValueError(f"Node {node_key} already exists")

        node = TDNode(
            name=name,
            parent_path=parent_path,
            type=type,
            tile=tile,
            inputs=inputs or {},
            color=color,
            flags=flags,
            params=params or [],
            panel=panel,
        )
        if text:
            node.text_data = _build_text_header() + text.encode("utf-8")

        self.nodes[node_key] = node
        info(f"Added node: {node_key} ({type})")
        return node

    def remove_node(self, path: str) -> bool:
        """Remove a node and all its files from the project."""
        norm = path.replace(".", "/")
        node = self.nodes.pop(norm, None)
        if node is None:
            warning(f"Node not found: {path}")
            return False
        # Also remove any children for COMPs
        prefix = f"{norm}/"
        to_remove = [k for k in self.nodes if k.startswith(prefix)]
        for k in to_remove:
            del self.nodes[k]
        info(f"Removed node: {norm}" + (f" (+ {len(to_remove)} children)" if to_remove else ""))
        return True

    def connect(self, src_path: str, dst_path: str, input_index: int = 0) -> None:
        """Connect src node to dst node at the given input index."""
        src = self.get_node(src_path)
        dst = self.get_node(dst_path)
        if not src:
            raise ValueError(f"Source node not found: {src_path}")
        if not dst:
            raise ValueError(f"Destination node not found: {dst_path}")

        dst.inputs[input_index] = src.name
        info(f"Connected {src_path} \u2192 {dst_path} (input {input_index})")

    def disconnect(self, dst_path: str, input_index: int) -> bool:
        """Remove a connection from the destination node's input."""
        dst = self.get_node(dst_path)
        if not dst:
            raise ValueError(f"Node not found: {dst_path}")
        if input_index in dst.inputs:
            del dst.inputs[input_index]
            info(f"Disconnected input {input_index} from {dst_path}")
            return True
        return False

    def set_param(self, node_path: str, param_name: str, value: str,
                  flags: int = 0, expression: str | None = None) -> bool:
        """Set a parameter value on a node.

        If the parameter doesn't exist, it is appended.
        """
        node = self.get_node(node_path)
        if not node:
            raise ValueError(f"Node not found: {node_path}")

        found = _set_param_in_list(node.params, param_name, str(value), flags, expression)
        if not found:
            entry = {"name": param_name, "flags": flags, "value": str(value)}
            if expression:
                entry["expression"] = expression
            node.params.append(entry)
        info(f"Param {node_path}:{param_name} = {value}")
        return True

    def get_param(self, node_path: str, param_name: str) -> Optional[str]:
        """Get a parameter value from a node."""
        node = self.get_node(node_path)
        if not node:
            return None
        for p in node.params:
            if p["name"] == param_name:
                return p.get("value")
        return None

    def set_text(self, node_path: str, text: str) -> None:
        """Set the text content of a DAT node.

        Preserves the binary header of the .text file.
        """
        from tdascode.types import _parse_text_file, _write_text_file, _build_text_header

        node = self.get_node(node_path)
        if not node:
            raise ValueError(f"Node not found: {node_path}")

        if node.text_data:
            node.text_data = _write_text_file(node.text_data, text)
        else:
            node.text_data = _build_text_header() + text.encode("utf-8")

        info(f"Set text on {node_path} ({len(text)} chars)")

    def get_text(self, node_path: str) -> str:
        """Get the text content of a DAT node."""
        from tdascode.types import _parse_text_file

        node = self.get_node(node_path)
        if not node:
            raise ValueError(f"Node not found: {node_path}")
        if not node.text_data:
            return ""
        _, text = _parse_text_file(node.text_data)
        return text.decode("utf-8", errors="replace")

    # ── Persistence ──────────────────────────────────────────────────────────

    def write(self) -> None:
        """Write all nodes back to the .dir folder and update the .toc."""
        import time

        # Remove all existing files in .dir to avoid stale entries
        for item in os.listdir(self.dir_path):
            item_path = os.path.join(self.dir_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, ignore_errors=True)
            else:
                Path(item_path).unlink(missing_ok=True)

        # Write meta files
        toc_entries: list[str] = []
        for meta_name, data in self.meta_files.items():
            meta_path = os.path.join(self.dir_path, meta_name)
            if isinstance(data, str):
                with open(meta_path, "w") as f:
                    f.write(data)
            else:
                with open(meta_path, "wb") as f:
                    f.write(data)
            if meta_name not in (".build",):
                toc_entries.append(meta_name)

        # Write nodes
        for node_key, node in sorted(self.nodes.items()):
            written = node.write_to(self.dir_path)
            toc_entries.extend(written)

        # Write .toc
        _write_toc(self.toc_path, toc_entries)
        success(f"Written {len(self.nodes)} nodes to {Path(self.dir_path).name}/")

    def cleanup(self) -> None:
        """Remove the .dir folder and .toc file from disk."""
        shutil.rmtree(self.dir_path, ignore_errors=True)
        Path(self.toc_path).unlink(missing_ok=True)
        info("Cleaned up temporary .dir and .toc files")

    def close(self) -> None:
        """Alias for cleanup()."""
        self.cleanup()


# ── Path utilities ───────────────────────────────────────────────────────────


def _split_path_ext(rel_path: str) -> tuple[str, str]:
    """Split 'Pop_glsl_sort/glsl1.parm' \u2192 ('glsl1', '.parm')."""
    basename = os.path.basename(rel_path)
    name, ext = os.path.splitext(basename)
    return name, ext


def _parent_path(rel_path: str) -> str:
    """Split 'Pop_glsl_sort/glsl1.n' \u2192 'Pop_glsl_sort'."""
    return os.path.dirname(rel_path)
