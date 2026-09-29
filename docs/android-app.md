# OverturaApp: Pixel companion

Overtura is the Debian CLI. OverturaApp is an Android companion for Pixel users.
The app explains setup and gives users a convenient path into the existing
SSH/tmux workflow. The two live in this repository so their instructions and
commands can evolve together.

## First working version

- Offline TL;DR and FAQ, shared with the documentation in `docs/mobile`.
- A setup guide for Termux, an existing SSH alias, and installation on Debian.
- Locally saved SSH alias and session name, with backups disabled.
- Commands for host diagnostics, listing sessions, creating a shell, and attaching.
- An explicit command preview with copy and open-Termux actions.

The initial handoff copies the chosen command and opens Termux. The user pastes
and runs it. This is deliberate: the first app requires no SSH keys, Internet
permission, Termux execution permission, account login, or background service.
It does not inspect terminal output or claim that a host is healthy. Diagnostics
and session lists appear in the real terminal.

## Next milestone

After testing this flow on a Pixel, consider Termux's documented RUN_COMMAND
interface for opt-in execution. It requires Android permission and Termux's
allow-external-apps setting. Keep manual copy/open as a fallback. Before showing
diagnostics or session state in the app, add a versioned JSON CLI interface and
handle unsupported versions, connection errors and stale results explicitly.

Embedded SSH and a terminal are later choices, not prerequisites for this app.
Credentials should remain in Termux until there is a reason to take ownership
of key storage, host verification and terminal lifecycle.

## Acceptance

1. Install the debug APK on a Pixel and open all four pages.
2. Read the offline guide without networking.
3. Save an SSH alias, generate a command and review it.
4. Copy/open Termux, paste and run doctor on a configured host.
5. Create and reattach a named session using the same handoff.
6. Confirm invalid aliases and names cannot inject shell syntax.

Use the disposable Debian lab for repeatable CLI installation and SSH tests.
Keep device addresses, keys, pairing data, local SDK paths, APKs and screenshots
out of Git. Publish built APKs as release assets when ready for distribution.

References:
- [Android command-line builds](https://developer.android.com/build/building-cmdline)
- [Termux RUN_COMMAND interface](https://github.com/termux/termux-app/wiki/RUN_COMMAND-Intent)
