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

The original handoff copies the chosen command and opens Termux. The user pastes
and runs it. This path needs no SSH keys in the app, Internet permission, Termux
execution permission, account login, or background service. It does not inspect
terminal output; diagnostics and session lists appear in the real terminal.

## Live read-only queries

The [CLI JSON v1 interface](protocol-v1.md), Android reply reader, and request
state are connected through Termux RUN_COMMAND for explicit live Doctor and
Sessions refreshes. The app requests Termux's permission and tells the user
to enable `allow-external-apps=true`; neither is changed silently. Results are
bounded, validated and labelled when stale. Create and attach keep the manual
Termux handoff. The Install page now covers a fresh Pixel's apps, SSH tools,
key, alias and host preparation.

## Pixel verification and next milestone

The 0.2.0 debug APK has passed an initial Pixel smoke test: the user granted
Termux command permission, enabled external commands in Termux, received a
healthy live Doctor report and an existing session list, saw the expected SSH
connection error for an unreachable alias, and recovered by restoring the alias.
Manual Termux handoff and the host's JSON Doctor command also worked. This
verifies successful and connection-error callback delivery on that device.

Next, test permission denial, host check failures, an older CLI, timeouts,
cancellation, and Activity lifecycle changes. A fresh install on another Pixel
is also pending. The APK has not been published as a release asset.

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
