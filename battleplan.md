# Overtura Battleplan

## What Overtura Is

Overtura is the public, reusable offspring of the private Overture setup.

The private `overture` repository stays private and remains the live, messy, real-world deployment: actual machines, addresses, hostnames, experiments, shortcuts, and personal infrastructure.

`overtura` should become the generic system that someone else can install and use without inheriting any of that private topology.

The guiding relationship is:

```text
Overtura = reusable machinery
Overture = Stan's private deployment of that machinery
```

Do not try to sanitize and publish the existing Overture repository or its history.

## Core Principles

- Public by design, not sanitized after the fact.
- No real hostnames, IPs, Tailnet names, usernames, SSIDs, keys, device IDs, or personal paths.
- Prefer roles and configuration over hard-coded machine names.
- Keep the CLI useful without requiring a future Android app.
- Keep SSH + tmux as the dependable fallback path.
- Treat Codex as one supported workload, not the entire architecture.
- Keep optional features optional: browser, GUI/VNC, Android/ADB, clipboard, etc.
- Debian/Linux should be the first-class initial host target.
- Prefer small boring components over a large daemon unless real use proves a daemon is needed.
- Do not prematurely generalize every private Overture experiment.

## Near-Term Shape

A plausible first public shape is:

```text
overtura
├── CLI / helpers
├── config schema + examples
├── host/session abstraction
├── tmux-backed durable sessions
├── doctor / capability detection
├── install/bootstrap for Debian
└── optional feature modules
    ├── browser
    ├── desktop/VNC
    ├── Android/ADB
    └── clipboard/files
```

Names and exact layout are intentionally not fixed yet.

The user-facing direction should eventually feel more like:

```sh
overtura doctor
overtura setup
overtura host ...
overtura session ...
```

rather than a collection of machine-specific aliases.

## Packaging Direction

Longer term, a fresh Debian machine should be able to become an Overtura node with a straightforward installer and eventually a Debian package.

Start simple. Do not build a full package ecosystem immediately.

A future progression might be:

```text
bootstrap/install script
        ->
clean versioned CLI + config
        ->
Debian package
        ->
optional packaged feature profiles
```

The package should install Overtura's own code and configuration, while external tools such as SSH, tmux, Tailscale, Node/Playwright, Chromium, ADB, and VNC remain normal system dependencies or optional integrations.

## Privacy Boundary

Assume the private Overture repository contains information that must never enter Overtura.

Public extraction should eventually work from an explicit allowlist or independently maintained generic implementations, not by copying the private repository and trying to scrub secrets afterward.

Private Overture may consume Overtura later, but Overtura must never depend on private data.

## First Mission For Codex

Do not start by copying files.

First inspect both repositories and produce a short architecture/migration note based on the real current contents.

For useful pieces in private Overture, classify them roughly as:

- **PUBLIC** — already generic enough to reuse with little change.
- **PARAMETERIZE** — useful logic currently tied to private machine names/topology.
- **PRIVATE** — deployment notes, live inventory, personal shortcuts, or experiments that should remain only in Overture.
- **LATER** — interesting but not needed for the first usable Overtura release.

Pay special attention to the reusable ideas around:

- durable tmux/agent sessions;
- SSH host routing;
- capability/health checks;
- browser/headed-browser support;
- secure VNC tunneling;
- Android/ADB routing;
- clipboard/file helpers;
- Debian/systemd/bootstrap setup.

Do not migrate or rewrite everything in this first pass.

Instead, use the real code and history to propose the smallest coherent **v0** that another person could install on one Debian machine and understand.

## Definition Of A Good First Milestone

A first useful Overtura milestone does not need the entire Overture feature set.

It is enough if a stranger can:

1. install it on a clean Debian machine;
2. configure a host without editing source code;
3. run `overtura doctor`;
4. create/attach a durable tmux-backed agent or shell session;
5. use ordinary SSH/tmux directly if Overtura breaks;
6. understand where private/local configuration belongs.

Everything beyond that can grow from actual use.

## For Now

Keep this repository clean and generic.

Before implementing major architecture, inspect Overture, challenge this plan where the real code disagrees, and leave room for another design pass.

The goal is not to clone Overture.

The goal is to discover the reusable system that Overture accidentally became.
