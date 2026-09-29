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

## Live read-only queries

The [CLI JSON v1 interface](protocol-v1.md), Android reply reader, and request
state are connected through Termux RUN_COMMAND for explicit live Doctor and
Sessions refreshes. The app requests Termux's permission and tells the user
to enable `allow-external-apps=true`; neither is changed silently. Results are
bounded, validated and labelled when stale. Create and attach keep the manual
Termux handoff. The Install page now covers a fresh Pixel's apps, SSH tools,
key, alias and host preparation.

## Next milestone

Verify the new transport on a Pixel, including permission denial, Termux setup,
successful and failed host replies, an older CLI, timeouts, callback delivery,
and Activity lifecycle changes. Test a fresh install on another Pixel after a
verified APK is published. This build has only local JVM/lint/build validation.

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
