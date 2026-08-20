# CodeMeter dongles & network-shared licenses

TouchDesigner's licensing runs on **Wibu-Systems CodeMeter** (USB license
dongles, CmActLicenses, floating cloud licenses). This page explains how
dongle licenses can be used with the Wine setup, and what the
`td-install --codemeter` command does.

> **Status (tested 2026-08):** the **server side works** (native Linux /
> Docker / Windows / macOS CodeMeter instances serve licenses over the LAN).
> The **client side under Wine is currently blocked**: the Windows CodeMeter
> service (`CodeMeter.exe`) does not start under the project's Wine runner
> (Wine 9.0 TkG/Soda) because Wibu's protected `cpsrt.dll` fails to load
> (`c000007b` / "section .text, file probably truncated", tested with runtime
> 8.41a and 9.10). Until that is resolved, TouchDesigner under Wine cannot
> borrow network-shared licenses. The tooling below remains useful for
> detection and configuration, and the server-side setup is fully validated.

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
| Network **server** (share a license) | ✅ via native Linux/Docker | Validated with the official `wibusystems/codemeter` container |
| CodeMeter **service** (`CodeMeter.exe`) | ❌ | Won't start: protected `cpsrt.dll` fails to load under Wine 9.0 (TkG/Soda) |
| Network **client** under Wine (borrow) | ❌ | Blocked by the service issue above |
| USB dongle plugged into this machine | ❌ | Needs Wine USB passthrough (`winusb`/`libusb`); not supported |

Two separate problems combine here:

1. **The Wibu MSI doesn't install under Wine.** `msiexec` hangs in
   `-Embedding` mode for 20+ minutes (tested with the official
   `CodeMeterRuntime` 8.41a/9.10 downloads).
2. **The runtime files don't run even when installed manually.** The
   AxProtector-protected `cpsrt.dll` intermittently fails to map
   (`c000007b`), so `CodeMeter.exe` never comes up and never opens port
   22350.

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

### Diagnostics & configuration (working)

```bash
td-install --codemeter status          # report: installed? running? servers?
td-install --codemeter setup           # start the runtime + show next steps
td-install --codemeter start           # start CodeMeter.exe now
td-install --codemeter add-server <ip> # add a license server to the search list
td-install --codemeter remove-server <ip>
td-install --codemeter servers         # show the current search list
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

---

## Unblocking the client (the open problem)

The one missing piece is getting `CodeMeter.exe` to run under Wine. Things
worth trying, in order:

1. **A different runtime version.** Only 8.41a and 9.10 were tested. An
   older runtime (e.g. 7.60, which Derivative recommends as a minimum and
   which older TD installers bundled) may ship an unprotected `cpsrt.dll`
   that maps fine under Wine.
2. **A different Wine build.** The failure is in Wine's PE loader handling
   of the protected DLL; a newer Wine (10/11) or a classic (non-WoW64) build
   might cope. Note the project is currently pinned to Soda/TkG 9.0.
3. **Reporting upstream.** The `c000007b` / "section .text truncated" on
   `cpsrt.dll` is a reproducible loader bug; a minimal repro (CodeMeter
   Runtime 9.10 + `wine64 CodeMeter.exe`) would be a good WineHQ bug report.

If you have a dongle and a compatible runtime setup, the round-trip to test
is: `td-install --codemeter setup`, `td-install --codemeter status` (expect
`Running: yes`), `td-install --codemeter add-server <server-ip>`, then launch
TD and check the Key Manager.

---

## Troubleshooting

- **`status` shows "not running" after `start`** → this is the known
  `cpsrt.dll` blocker (see above), not a configuration mistake.
- **Client can't find the server** → check the server's firewall (port
  22350 TCP/UDP), verify the client can ping it, then
  `td-install --codemeter add-server <ip>`. Look at the **Events** tab in the
  CodeMeter WebAdmin for clues.
- **CmDust log** (for support): plug in / configure, run TouchDesigner once,
  then run `cmu32.exe --cmdust` from
  `C:\Program Files (x86)\CodeMeter\Runtime\bin\` inside the prefix.
