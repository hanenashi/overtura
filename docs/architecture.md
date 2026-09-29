# Initial architecture and migration note

The private predecessor proves that SSH and tmux provide a useful core. Its
history also shows recurring fixes around noninteractive PATH handling, workload
installation differences, and shared terminal sizing. Those deserve explicit
interfaces and tests before additional integrations.

This is a fresh implementation. No predecessor files or Git history are imported.
Classification below describes ideas and components, not permission to copy a
file without reviewing it.

| Class | Candidates | Treatment |
| --- | --- | --- |
| PUBLIC | Session create/attach primitives, dependency checks, terminal-sizing ideas | Reimplement the small core; review any later extraction individually. |
| PARAMETERIZE | Agent launcher, workspace selection, SSH dispatcher, user service templates | Separate workspace, named sessions, workload argv, and transport. |
| PRIVATE | Inventories, startup prompts, aliases, actual SSH and sudo configuration | Keep outside this repository and its history. |
| LATER | Browser/headed desktop, VNC, Android/ADB, clipboard/files, Windows/WSL, boot resume | Keep independent of the first milestone. |

The existing launcher combines environment discovery, session creation, agent
startup and private instructions. Its shell and agent entry points can select the
same repository-derived session name. Its doctor assumes the agent is installed.
The new CLI uses explicit session names and workload argument arrays, and reports
missing optional workloads without failing core diagnostics.

## v0 boundary

- One Debian 12+ host, Python 3.11+ standard library, tmux, no daemon or pip packages.
- A standalone CLI installed under a user-owned prefix.
- Versioned TOML structure in private XDG configuration, independent of source.
- A dedicated tmux server, using tmux defaults rather than altering user config.
- SSH remains the remote interface. Connect using an existing SSH alias and run
  the CLI on the host; no second address/key/jump-host database.
- A workload is an argument array. Its executable resolves on the invoking PATH
  and is converted to an absolute path before tmux launches it. No agent login,
  approvals, environment files, or prompts are managed by Overtura.
- Durability means surviving client disconnection. Host reboot, command exit,
  and explicit session termination end the running session. Agent transcript
  resume and boot services are separate future features.

Python replaces nested shell quoting with structured argument handling and
testable configuration validation. The one tmux shell boundary quotes each argv
element. The implementation stays small enough to invoke SSH/tmux directly when
the wrapper is unavailable.

## Acceptance evidence

Tests use temporary HOME/config/install directories and unique tmux server names.
They check config protection, missing dependencies, argument preservation, real
session creation and listing, duplicate names, working directories with spaces,
attachment/detachment, abrupt terminal loss and reattachment without losing the pane, and removal of
the CLI while leaving a session usable through tmux. They do not use live SSH
destinations or private agent accounts.

The disposable rootless Podman lab now also verifies installation on fresh Debian
13 userspace, the CLI/protocol tests, JSON replies over SSH, and abrupt loss of a real SSH client followed by
reattachment to the same shell process. Its SSH listener is loopback-only and it
mounts no host directories. See `tests/lab/README.md` for reproduction commands.

A full VM installation, host reboot behavior, and interruption of a physical
network connection remain separate checks. A container shares its host kernel;
killing an SSH client does not reproduce every network failure mode.

The [v1 JSON boundary](protocol-v1.md) adds machine-readable diagnostics and
session metadata to the same CLI. Android consumer/state code is prepared;
Termux callback transport and live status UI remain a separate milestone.
