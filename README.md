# Overtura

Durable shell and agent sessions on a Debian host, using ordinary SSH and tmux.
Start a session, disconnect your terminal, and attach again later.

This is an early v0. Python 3.11+ and tmux are required (Debian 12+). Agents,
Tailscale, desktop sharing, and Android tools are optional and installed separately.

## Install

If dependencies are missing, install the distribution packages:

```sh
sudo apt-get install python3 tmux
```

From this checkout, install as your regular user:

```sh
python3 install.py
export PATH="$HOME/.local/bin:$PATH"
overtura setup
overtura doctor
```

The installer copies the standalone CLI to `~/.local/bin/overtura`; it does not
need sudo, edit shell startup files, install agents, or enable services. Add the
PATH setting to your shell configuration if needed. The checkout can be moved
after installation. Use `python3 install.py --upgrade` after updating the source.

## Sessions

```sh
overtura session create work
```

This creates and attaches a shell session. Press **Ctrl+b, then d** to detach.
The shell and its running processes remain on the host.

```sh
overtura session list
overtura session attach work
overtura session create another --cwd "$HOME" --detach
```

Names are explicit: different sessions can use the same directory. Creating an
existing name fails rather than silently attaching to a different workload.
`--detach` is required when creating without an interactive terminal or from
inside another tmux session. To attach, open a separate terminal or detach first.

Exit the shell normally to end its session. Agent sessions end when the agent
command exits. A network disconnect leaves the session running, but a host reboot
does not preserve processes. There is no automatic boot or agent transcript resume.

## Machine-readable interface

CLI 0.2.0 supports `--json` for capabilities, doctor, session listing, and
creation with `--detach`. See the [v1 protocol boundary](docs/protocol-v1.md)
for fields, exit codes, errors, privacy, and the Android consumer contract.

```sh
overtura --json capabilities
overtura --json doctor
overtura --json session list
```

## Private configuration

`overtura setup` creates `~/.config/overtura/config.toml` with mode `0600` and
refuses to overwrite an existing file. `XDG_CONFIG_HOME` is respected. To use
another file, put `--config /path/to/config.toml` before the subcommand.

```toml
version = 1

[host]
workspace = "~"

[workloads.shell]
command = ["/bin/sh"]

# Enable after installing and authenticating your preferred agent:
# [workloads.agent]
# command = ["your-agent-command", "--your-option"]
```

`host.workspace` is an existing absolute directory or a path starting with `~`.
`--cwd` overrides it per session and also accepts paths relative to your terminal.
The default shell starts in your home directory.

Workload commands are argument arrays, not shell expressions. Pipes, `$VARIABLE`,
and `$(command)` are passed literally. Use an executable on PATH or an absolute
path; `~` is supported in the executable path. For advanced shell behavior, make
a local wrapper script and configure its absolute path.

```sh
overtura session create agent-work --workload agent
```

The workload inherits the tmux server's environment, with tmux's normal client
environment updates. Overtura resolves the executable from the invoking PATH,
but does not synchronize all environment variables into an already-running
server. Use a local wrapper when a workload needs a specific environment.
Keep credentials in the agent's own authentication mechanism.

`doctor` reports all core checks and exits nonzero for missing tmux, invalid or
missing configuration, or a missing workspace. Missing optional workload
executables produce warnings. It does not authenticate agents or test an SSH
server, and never starts a tmux server or prints configured command arguments.

## SSH and recovery

Install Overtura on the Debian host. Use your existing SSH configuration from
any client, including Termux. Here `my-node` means your own SSH alias:

```sh
ssh -t my-node '~/.local/bin/overtura session create work'
ssh -t my-node '~/.local/bin/overtura session attach work'
```

SSH keys, addresses and jump hosts stay in `~/.ssh/config`. Remote SSH access
itself must already work; Overtura does not install or configure an SSH server.
Noninteractive SSH often has a smaller PATH. Configure an absolute agent path
if needed, or invoke a local wrapper that prepares its runtime.

Sessions use an independent tmux server named `overtura`, initialized with tmux
defaults rather than `~/.tmux.conf`. Your existing tmux server is unaffected.
If the CLI is unavailable, use:

```sh
tmux -L overtura list-sessions
tmux -L overtura attach-session -t '=work'
```

Tmux's default prefix is Ctrl+b. Normal window and pane controls work. To change
how multiple clients share a window, use ordinary tmux settings, for example:

```sh
tmux -L overtura set-window-option -t '=work:' window-size smallest
```

There is no automatic terminal-size policy in v0. `--socket NAME`, before the
subcommand, selects another independent server when needed. Always use the same
socket when listing, attaching, or recovering those sessions.

## Uninstall and development

```sh
python3 install.py --uninstall
```

Removal preserves private configuration and running sessions. Unmanaged files
and symlinks are never overwritten or removed. `--prefix DIR` selects another
installation prefix; use the same prefix for upgrades and uninstalling.

Run from source and execute the standard-library tests:

```sh
python3 overtura.py --help
python3 -m unittest discover -s tests -v
```

Integration tests require tmux and use temporary directories and dedicated,
randomly named servers. They never connect to real hosts or agent accounts.

For fresh Debian installation and real SSH reconnect tests, use the
[disposable Podman lab](tests/lab/README.md).

See [the initial architecture note](docs/architecture.md) and
[the original battle plan](battleplan.md). Browser, VNC, Android/ADB, clipboard,
boot services and additional platforms remain future work.

The [Pixel companion app](android/README.md) provides offline [TL;DR](docs/mobile/tldr.md),
[FAQ](docs/mobile/faq.md), [installation guidance](docs/mobile/install.md), and
session commands to copy into Termux. The current source also adds opt-in live
Doctor and session-list queries. See its [scope and next steps](docs/android-app.md).
Android device automation remains separate from this companion app.
