#!/usr/bin/env python3
"""Recover the wineserver request enum order from a wineserver binary.

wineserver has `static const char * const req_names[REQ_NB_REQUESTS]`, an array
of pointers (R_X86_64_RELATIVE relocations in a PIE) to the request name
strings, in enum order. We find the run of consecutive 8-byte relocations whose
targets are request-name strings, starting at "new_process".
Usage: req_numbers.py <wineserver> [name ...]
"""
import re
import subprocess
import sys

path = sys.argv[1]
wanted = sys.argv[2:]
data = open(path, "rb").read()

# section headers -> map vaddr to file offset
secs = []
out = subprocess.run(["readelf", "-SW", path], capture_output=True, text=True).stdout
for line in out.splitlines():
    m = re.match(r"\s*\[\s*\d+\]\s+(\S+)\s+\S+\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)", line)
    if m:
        secs.append((m.group(1), int(m.group(2), 16), int(m.group(3), 16), int(m.group(4), 16)))


def cstr_at(vaddr):
    for _, addr, off, size in secs:
        if addr and addr <= vaddr < addr + size:
            o = off + (vaddr - addr)
            end = data.index(b"\0", o)
            return data[o:end].decode("ascii", "replace")
    return None


relocs = {}
out = subprocess.run(["readelf", "-rW", path], capture_output=True, text=True).stdout
for line in out.splitlines():
    m = re.match(r"([0-9a-f]+)\s+[0-9a-f]+\s+R_X86_64_RELATIVE\s+([0-9a-f]+)", line)
    if m:
        relocs[int(m.group(1), 16)] = int(m.group(2), 16)

start = None
for off, target in relocs.items():
    if cstr_at(target) == "new_process" and cstr_at(relocs.get(off + 8, 0)) == "get_new_process_info":
        start = off
        break
if start is None:
    sys.exit("req_names table not found")

names = []
off = start
while off in relocs:
    s = cstr_at(relocs[off])
    if not s or not re.fullmatch(r"[a-z0-9_]+", s):
        break
    names.append(s)
    off += 8

print(f"REQ_NB_REQUESTS = {len(names)}")
for n in wanted or names:
    print(f"REQ_{n} = {names.index(n) if n in names else 'MISSING'}")
