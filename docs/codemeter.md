# CodeMeter dongles & network-shared licenses

TouchDesigner's licensing runs on **Wibu-Systems CodeMeter** (USB license
dongles, CmActLicenses, floating cloud licenses). This page explains how
dongle licenses can be used with the Wine setup, and what the
`td-install --codemeter` command does.

> **Status (2026-09): the service blocker is solved on Wine 11.** Under the
> project's Wine 9.0 TkG/Soda runner, `CodeMeter.exe` still stalls during
> startup (single thread, never opens port 22350). Under Wine 11
> (`DAW-GE-Proton11-6c` via UMU), runtime **7.60d** starts, runs with 12
> threads and **listens on port 22350** (the WebAdmin answers on
> `127.0.0.1`). See "Update (2026-09)" below.
>
> The **server side works** (native Linux / Docker / Windows / macOS
> CodeMeter instances serve licenses over the LAN). On the **client side**,
> the runtime installs without msiexec (`td-install --codemeter install`),
> and `cpsrt.dll` loads under Wine 9.0 with runtime 7.60d (the `c000007b`
> loader failure only affects runtimes 8.41a and 9.10). A full license
> checkout against a license server has not been verified yet.

---

## How licensing works on Windows

The TouchDesigner installer has an **"Install Runtime for Dongle Licensing"**
option (checked by default). It installs the *CodeMeter Runtime*, a background
service (`CodeMeter.exe`) that:

- talks to a plugged-in USB dongle (or a software/cloud license),
- acts as a **network client** that finds license servers on the LAN and
  borrows licenses from them,
- can act as a **network server** that shares its own license(s) with other
  machines.

The CodeMeter network protocol uses **UDP/TCP port 22350** (discovery is a UDP
broadcast; license access is TCP). Both the "Sharing Licenses Over a Network"
server and client machines need the CodeMeter Runtime installed.

---

## What works under Wine (test results)

| Capability | Under Wine | Notes |
| --- | --- | --- |
| Software licenses (`ins*.dat`) | ✅ | TD reads them without any runtime installed |
| Runtime detection / config CLI | ✅ | `td-install --codemeter status\|servers\|add-server` work |
| Runtime CLI tools (`cmu.exe`/`cmu32.exe`) | ✅ | Version output works; used for server-list management |
| Runtime **installation** | ✅ | `td-install --codemeter install <path>` extracts natively (innoextract/7z) — no msiexec |
| Network **server** (share a license) | ✅ via native Linux/Docker | Validated with the official `wibusystems/codemeter` container |
| CodeMeter **service** (`CodeMeter.exe`) | ⚠️ Wine 11 ✅ / Wine 9 ❌ | Wine 9: 8.41a/9.10 fail on `cpsrt.dll` (`c000007b`), 7.60d stalls during init (1 thread, no port 22350). Wine 11: 7.60d starts, 12 threads, listens on 22350 |
| Network **client** under Wine (borrow) | ⚠️ not verified end-to-end | The service now starts on Wine 11. A full license checkout still needs a license server or dongle |
| USB dongle plugged into this machine | ❌ | Needs Wine USB passthrough (`winusb`/`libusb`); not supported |

Three problems were found, one of which is now solved:

1. **The Wibu MSI doesn't install under Wine.** `msiexec` hangs in
   `-Embedding` mode for 20+ minutes (tested with the official
   `CodeMeterRuntime` 8.41a/9.10 downloads). **Solved:**
   `td-install --codemeter install <path>` extracts the installer natively
   on the host (innoextract for Inno setups, `7z` for WiX/MSI bundles — the
   official 7.60d download is a WiX bundle that innoextract rejects but 7z
   unwraps) and lifts the files into the prefix, no msiexec involved.
2. **Runtimes 8.41a/9.10 crash on load.** The AxProtector-protected
   `cpsrt.dll` intermittently fails to map (`c000007b` / "section .text,
   file probably truncated"). **Avoided by using runtime 7.60d**, whose
   `cpsrt.dll` loads cleanly under Wine 9.0.
3. **`CodeMeter.exe` stalls during startup under Wine 9.0.** Even with
   7.60d, the service process stays alive with a single thread, never
   creates its `ProgramData/WIBU-SYSTEMS` config, and never opens port
   22350. **Solved on Wine 11** (2026-09): the process runs with 12 threads
   and listens on 22350, so it was indeed Wine-version dependent.

---

## What still works today

### Server side (fully working)

Put the dongle on any machine on your LAN and enable the network server:

- **Windows / macOS server:** CodeMeter Control Center → WebAdmin →
  *Configuration → Server → Server Access* → enable **Network Server**.
  Under *License Access Permissions*, add the client's IP. Restart the
  CodeMeter service.
- **Linux server (native daemon):** install the `codemeter` package, plug the
  dongle in, and set `IsNetworkServer=1` in
  `/etc/wibu/CodeMeter/Server.ini`, then restart the `codemeter` service.
- **Containerized server (validated):** run Wibu's official
  [`docker-codemeter`](https://github.com/wibu-systems/docker-codemeter)
  image with the network server enabled, a good fit for the
  containerized/distrobox plans:
  ```bash
  # Server.ini in /etc/wibu/CodeMeter/Server.ini inside the container:
  printf '[Global]\nIsNetworkServer=1\n' > Server.ini
  docker run -d --name cm-server --network host \
      -v "$PWD/Server.ini:/etc/wibu/CodeMeter/Server.ini" \
      wibusystems/codemeter
  # verify:  ss -ltn | grep 22350   → "Server ready" in the logs
  ```
- **Firewall:** allow UDP/TCP **22350** on the server.

### Diagnostics, installation & configuration (working)

```bash
td-install --codemeter status            # report: installed? running? servers?
td-install --codemeter install <path>    # install a runtime without msiexec (see below)
td-install --codemeter setup             # start the runtime + show next steps
td-install --codemeter start             # start CodeMeter.exe now
td-install --codemeter add-server <ip>   # add a license server to the search list
td-install --codemeter remove-server <ip>
td-install --codemeter servers           # show the current search list
```

Behind the scenes:

- The **Server Search List** on the Windows client lives in
  `HKLM\SOFTWARE\WIBU-SYSTEMS\CodeMeter\Server\CurrentVersion\ServerSearchList`
  (`Server1`, `Server2`, … each with a REG_SZ `Address`). `add-server` uses
  Wibu's official `cmu32 --add-server` tool when available (also works with
  `cmu.exe` in 64-bit runtimes), with a direct `reg add` fallback.
- The **WebAdmin** UI is served by the runtime at `http://127.0.0.1:22350`
  once `CodeMeter.exe` is running; you can also configure everything there
  from your normal browser.

### Installing the runtime without msiexec

`td-install --codemeter install <path>` extracts a CodeMeter Runtime
installer natively on the host and lays the files into the Wine prefix at
the locations a Windows install would use. It accepts either format:

- `CodeMeterRuntime*.exe` (Inno Setup — extracted with `innoextract`),
- `CodeMeterRuntime*.msi` (extracted with `7z` or `msiextract`).

The runtime installers are downloaded from Wibu-Systems
(https://www.wibu.com → Downloads → CodeMeter Runtime; the 32-bit and
64-bit variants are separate). There is no need for Wine to install
anything — `msiexec` is never invoked. The launcher also auto-starts
`CodeMeter.exe` when a runtime is detected.

**CodeMeter is never installed automatically.** The installer never runs
TouchDesigner's "Install Runtime for Dongle Licensing" option (TD is
extracted, not executed), and the AUR package does not ship the runtime
either. It only ever appears in the prefix when you run
`td-install --codemeter install <path>` explicitly, and
`td-install --codemeter remove` removes it again. This keeps the default
setup free of the runtime's startup cost (the "Checking CodeMeter
licenses..." splash and its delay, which is long while the service cannot
start under Wine 9.0).

---

## Unblocking the client

### Update (2026-09): solved on Wine 11

Tested on CachyOS + NVIDIA, using the Wine 11 setup from
[`docs/runners.md`](runners.md) (`DAW-GE-Proton11-6c` via UMU) instead of
Soda 9.0. Runtime **7.60d** was extracted with the project's own tooling
(`_extract_installer` + `_copy_payload` + `_copy_system_dlls`) and copied
into the UMU prefix's `drive_c`, then started with `umu-run CodeMeter.exe`:

- the process runs with **12 threads** (not a single-thread stall)
- it opens **port 22350**, and the WebAdmin answers on `127.0.0.1:22350`
  (301 redirect to `:22352`)
- stable, observed for over 2 minutes

The Wine 9.0 stall was indeed Wine-version dependent. This removes the
documented blocker for the network client. **Still unverified:** a real
license checkout against a license server (no server or dongle was available
in the test).

### Older findings (tested 2026-08 on Wine 9.0 TkG/Soda)

- **8.41a / 9.10** — the protected `cpsrt.dll` fails to map (`c000007b` /
  "section .text, file probably truncated") and `CodeMeter.exe` never comes
  up.
- **7.60d** (the version Derivative recommends and older TD installers
  bundled) — `cpsrt.dll` loads cleanly, `cmu32.exe` works, but
  `CodeMeter.exe` **stalls during startup**: the process stays alive with a
  single thread, never creates its `ProgramData\WIBU-SYSTEMS` config, and
  never opens port 22350.

Things worth trying, in order:

1. **A different Wine build.** ✅ Done (2026-09): a newer Wine (11) gets it
   past startup, see the update above. The project is still pinned to
   Soda/TkG 9.0 as its default runner, so in practice the CodeMeter client
   only works with a Wine 11 runner.
2. **A different runtime version.** Thanks to `--codemeter install <path>`,
   each trial is now a 30-second operation:

   ```bash
   td-install --codemeter install ~/Downloads/CodeMeterRuntime_*.exe
   td-install --codemeter start
   td-install --codemeter status        # expect: Running: yes
   ss -ltn | grep 22350                 # expect: CodeMeter.exe listening
   ```

   A runtime that stays up and opens port 22350 is the green light to do
   the full network round-trip below.
3. **Reporting upstream.** The 7.60d stall is a clean repro (CodeMeter
   Runtime 7.60d + `wine64 CodeMeter.exe`; process stays single-threaded,
   no port) — a good WineHQ bug report, as is the 9.10 `cpsrt.dll` loader
   failure.

If you have a dongle and a compatible runtime setup, the round-trip to test
is: `td-install --codemeter install <runtime>`, `td-install --codemeter
status` (expect `Running: yes`), `td-install --codemeter add-server
<server-ip>`, then launch TD and check the Key Manager. The license server
can be any machine on the LAN with the dongle plugged in and its network
server enabled — or a second machine running the native Linux/Docker
server above.

---

## Troubleshooting

- **`status` shows "not running" after `start`** → on Wine 9.0 (Soda) this
  is the known service blocker (see above), not a configuration mistake:
  with 8.41a/9.10 the DLL won't load, with 7.60d the process stays
  single-threaded and never opens port 22350. On Wine 11 the service starts
  normally (see the update above).
- **Client can't find the server** → check the server's firewall (port
  22350 TCP/UDP), verify the client can ping it, then
  `td-install --codemeter add-server <ip>`. Look at the **Events** tab in the
  CodeMeter WebAdmin for clues.
- **CmDust log** (for support): plug in / configure, run TouchDesigner once,
  then run `cmu32.exe --cmdust` from
  `C:\Program Files (x86)\CodeMeter\Runtime\bin\` inside the prefix.
