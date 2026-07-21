# Advanced tools: toeexpand / toecollapse

TouchDesigner includes two utility programs in its `bin/` directory:

- **`toeexpand`** — expands a `.toe` or `.tox` file into a collection of ASCII-readable files (`.n`, `.parm`, `.panel`, `.table`...). To reverse the expansion process, `toecollapse` will convert the files back into a `.toe` or `.tox` format readable by TouchDesigner.
- **`toecollapse`** — collapses an expanded `.toe` file into a form readable by TouchDesigner. This can only be used on a `.toe` file that has been expanded into a collection of ASCII files using `toeexpand`.

All commands use the launcher's Wine environment:

```bash
TACT_BASE_DIR="$HOME/.local/share/tact"
WINE_PREFIX="$TACT_BASE_DIR/prefix"
WINEPREFIX="$WINE_PREFIX" "$TACT_BASE_DIR/runner/bin/wine64" \
  "$(find "$WINE_PREFIX/drive_c" -name toeexpand.exe -print -quit)" \
  "z:/path/to/file.toe"
```

## Useful workflows

- **Inspect a `.toe` contents** — expand it to inspect or version-control its internal components as plain text files
- **Check if `wine_ui_fixes` is applied** — expand and look for a `wine_ui_fixes/` folder inside the `.dir`
- **Manually patch a single file** — `install.sh --patch-toe /path/to/file.toe`
- **Extract, edit, and re-collapse** — expand, modify the ASCII files, then run `toecollapse` to rebuild the `.toe`

The launcher handles all of this automatically, but these tools are available if you need fine-grained control.
