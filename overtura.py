#!/usr/bin/env python3
# overtura-managed-cli-v1
"""A small, dependency-free front end to durable tmux sessions."""

import argparse
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

if sys.version_info < (3, 11):
    sys.exit("overtura: Python 3.11 or newer is required")

import tomllib

VERSION = "0.1.0"
DEFAULT_CONFIG = '''version = 1

[host]
workspace = "~"

[workloads.shell]
command = ["/bin/sh"]

# Install and authenticate an agent separately, then enable its workload:
# [workloads.agent]
# command = ["your-agent-command"]
'''


class Error(Exception):
    pass


def identifier(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value):
        raise argparse.ArgumentTypeError(
            "use 1–64 letters, digits, underscores or hyphens; start with a letter or digit"
        )
    return value


def config_path():
    root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return root / "overtura" / "config.toml"


def read_config(path):
    try:
        with path.open("rb") as stream:
            data = tomllib.load(stream)
    except FileNotFoundError:
        raise Error("configuration missing; run overtura setup") from None
    except tomllib.TOMLDecodeError:
        # Parser diagnostics can contain values from private configuration.
        raise Error("invalid TOML configuration; check syntax locally") from None
    except OSError:
        raise Error("cannot read configuration; check file permissions") from None
    if set(data) - {"version", "host", "workloads"}:
        raise Error("unknown top-level configuration field")
    if type(data.get("version")) is not int or data["version"] != 1:
        raise Error("configuration version must be 1")
    host = data.get("host")
    if not isinstance(host, dict) or set(host) != {"workspace"}:
        raise Error("host must contain only workspace")
    if not isinstance(host["workspace"], str) or not host["workspace"] or "\0" in host["workspace"]:
        raise Error("host.workspace must be a nonempty path")
    try:
        workspace = Path(host["workspace"]).expanduser()
    except RuntimeError:
        raise Error("cannot expand host.workspace home directory") from None
    if not workspace.is_absolute():
        raise Error("host.workspace must be absolute or start with ~")
    workloads = data.get("workloads")
    if not isinstance(workloads, dict) or not workloads:
        raise Error("configure at least one workload")
    for name, workload in workloads.items():
        try:
            identifier(name)
        except argparse.ArgumentTypeError:
            raise Error("invalid workload name") from None
        if not isinstance(workload, dict) or set(workload) != {"command"}:
            raise Error("each workload must contain only command")
        command = workload["command"]
        if not isinstance(command, list) or not command or any(
            not isinstance(arg, str) or "\0" in arg for arg in command
        ) or not command[0]:
            raise Error("workload command must be an argument array with a nonempty executable")
    return workspace, workloads


def executable(command):
    expanded = os.path.expanduser(command)
    if "/" in expanded and not Path(expanded).is_absolute():
        raise Error("workload executable must be an absolute path or a name on PATH")
    found = shutil.which(expanded)
    # Preserve symlinks: resolving a virtualenv's Python selects the base runtime.
    return os.path.abspath(found) if found else None


def setup(path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise Error("configuration already exists; setup never overwrites it") from None
    with os.fdopen(fd, "w") as stream:
        stream.write(DEFAULT_CONFIG)
    print(f"Created {path}")
    print("Edit host.workspace and workloads there, then run overtura doctor.")


def tmux_base(args):
    binary = shutil.which("tmux")
    if not binary:
        raise Error("tmux is missing; install the Debian tmux package")
    # An independent server and configuration keep ordinary tmux sessions intact.
    return [binary, "-L", args.socket, "-f", "/dev/null"]


def tmux(args, *command):
    return subprocess.run(
        tmux_base(args) + list(command), text=True, capture_output=True,
    )


def require_tty():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise Error("attachment needs a terminal; use ssh -t, or create with --detach")
    if os.environ.get("TMUX"):
        raise Error("already inside tmux; detach or open another terminal before attaching")


def attach(args):
    require_tty()
    base = tmux_base(args)
    # Exact matching prevents an abbreviation from selecting another session.
    os.execv(base[0], base + ["attach-session", "-t", "=" + args.name])


def create(args):
    if not args.detach:
        require_tty()
    workspace, workloads = read_config(args.config)
    if args.workload not in workloads:
        raise Error("unknown workload; check workloads in your configuration")
    try:
        cwd = Path(args.cwd).expanduser().resolve() if args.cwd else workspace
    except RuntimeError:
        raise Error("cannot resolve the requested working directory") from None
    if not cwd.is_dir():
        raise Error("working directory does not exist or is not a directory")
    argv = workloads[args.workload]["command"].copy()
    resolved = executable(argv[0])
    if not resolved:
        raise Error("workload executable unavailable; install it or fix its configured path")
    argv[0] = resolved
    # tmux runs a shell command: quote EVERY argument, never interpolate raw config.
    result = tmux(args, "new-session", "-d", "-s", args.name, "-c", str(cwd),
                  "exec " + shlex.join(argv))
    if result.returncode:
        if "duplicate session:" in result.stderr:
            raise Error("session already exists; use session attach with its name")
        raise Error("tmux could not create the session; check tmux and socket permissions")
    print(f"Created session {args.name}.", flush=True)
    if not args.detach:
        attach(args)


def list_sessions(args):
    result = tmux(args, "list-sessions", "-F", "#{session_name}\t#{session_windows}\t#{session_attached}")
    if result.returncode:
        if "no server running" in result.stderr or "No such file or directory" in result.stderr:
            print("No sessions.")
            return
        raise Error("cannot list sessions; check tmux socket permissions")
    print("NAME\tWINDOWS\tATTACHED CLIENTS")
    print(result.stdout, end="")


def doctor(args):
    failures = 0

    def report(level, message):
        nonlocal failures
        print(f"{level}: {message}")
        failures += level == "FAIL"

    report("OK", "Python 3.11+ available")
    report("OK" if shutil.which("tmux") else "FAIL", "tmux available" if shutil.which("tmux") else "tmux missing (install Debian package: tmux)")
    report("OK" if shutil.which("ssh") else "WARN", "SSH client available" if shutil.which("ssh") else "SSH client missing (optional for local sessions)")
    try:
        workspace, workloads = read_config(args.config)
        report("OK", "configuration valid")
        report("OK" if workspace.is_dir() else "FAIL", "workspace exists" if workspace.is_dir() else "workspace directory missing")
        for name, workload in workloads.items():
            try:
                available = executable(workload["command"][0]) is not None
            except Error:
                available = False
            report("OK" if available else "WARN", f"workload {name}: " + ("executable available" if available else "executable unavailable (only this workload is affected)"))
    except Error as exc:
        report("FAIL", str(exc))
    report("INFO", "sessions survive disconnection, not host reboot or workload exit")
    return 1 if failures else 0


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--version", action="version", version=f"overtura {VERSION}")
    result.add_argument("--config", type=Path, default=config_path(), help="private TOML config path")
    result.add_argument("--socket", type=identifier, default="overtura", help="tmux server name (default: overtura)")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("setup", help="create private config without overwriting")
    commands.add_parser("doctor", help="check requirements without changing the system")
    sessions = commands.add_parser("session", help="manage durable sessions")
    operations = sessions.add_subparsers(dest="operation", required=True)
    new = operations.add_parser("create", help="create and attach to a new session")
    new.add_argument("name", type=identifier)
    new.add_argument("--workload", type=identifier, default="shell")
    new.add_argument("--cwd", help="working directory (default: host.workspace)")
    new.add_argument("--detach", action="store_true", help="create without attaching")
    existing = operations.add_parser("attach", help="attach to an existing session")
    existing.add_argument("name", type=identifier)
    operations.add_parser("list", help="list sessions, even without configuration")
    return result


def main():
    args = parser().parse_args()
    try:
        if args.command == "setup":
            setup(args.config)
        elif args.command == "doctor":
            return doctor(args)
        elif args.operation == "create":
            create(args)
        elif args.operation == "attach":
            attach(args)
        else:
            list_sessions(args)
    except Error as exc:
        print(f"overtura: {exc}", file=sys.stderr)
        return 1
    except OSError:
        print("overtura: operating-system error; check file and executable permissions", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
