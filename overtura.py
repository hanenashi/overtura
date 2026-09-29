#!/usr/bin/env python3
# overtura-managed-cli-v1
"""A small, dependency-free front end to durable tmux sessions."""

import argparse
import json
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

VERSION = "0.2.0"
SCHEMA_VERSION = 1
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
    def __init__(self, message, code="operation_failed"):
        super().__init__(message)
        self.code = code


def envelope(command, data=None, error=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "cli_version": VERSION,
        "command": command,
        "ok": error is None,
        "data": data,
        "error": None if error is None else {"code": error.code, "message": str(error)},
    }


def emit(command, data=None, error=None):
    print(json.dumps(envelope(command, data, error), ensure_ascii=True), flush=True)


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        if "--json" in sys.argv[1:]:
            emit(None, error=Error("invalid arguments; see overtura --help", "invalid_arguments"))
            raise SystemExit(2)
        super().error(message)


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
        raise Error("configuration missing; run overtura setup", "config_missing") from None
    except tomllib.TOMLDecodeError:
        # Parser diagnostics can contain values from private configuration.
        raise Error("invalid TOML configuration; check syntax locally", "config_invalid") from None
    except OSError:
        raise Error("cannot read configuration; check file permissions", "config_unreadable") from None
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
        raise Error("tmux is missing; install the Debian tmux package", "dependency_missing")
    # An independent server and configuration keep ordinary tmux sessions intact.
    return [binary, "-u", "-L", args.socket, "-f", "/dev/null"]


def tmux(args, *command):
    try:
        return subprocess.run(
            tmux_base(args) + list(command), text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=8,
        )
    except subprocess.TimeoutExpired:
        raise Error("tmux did not respond before the timeout", "tmux_timeout") from None


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
        raise Error("unknown workload; check workloads in your configuration", "workload_unknown")
    try:
        cwd = Path(args.cwd).expanduser().resolve() if args.cwd else workspace
    except RuntimeError:
        raise Error("cannot resolve the requested working directory") from None
    if not cwd.is_dir():
        raise Error("working directory does not exist or is not a directory", "directory_missing")
    argv = workloads[args.workload]["command"].copy()
    resolved = executable(argv[0])
    if not resolved:
        raise Error("workload executable unavailable; install it or fix its configured path", "workload_unavailable")
    argv[0] = resolved
    # tmux runs a shell command: quote EVERY argument, never interpolate raw config.
    result = tmux(args, "new-session", "-d", "-P", "-F", "#{session_id}", "-s", args.name, "-c", str(cwd),
                  "exec " + shlex.join(argv))
    if result.returncode:
        if "duplicate session:" in result.stderr:
            raise Error("session already exists; use session attach with its name", "session_exists")
        raise Error("tmux could not create the session; check tmux and socket permissions", "tmux_failure")
    if args.json:
        emit("session.create", {"session": {
            "id": result.stdout.strip(), "name": args.name, "workload": args.workload,
        }})
    else:
        print(f"Created session {args.name}.", flush=True)
    if not args.detach:
        attach(args)


def no_server(stderr):
    return any(message in stderr for message in ("no server running", "No such file or directory", "no sessions"))


def session_records(args):
    # Native tmux names need not obey our identifier rules. Fetch their display
    # form separately by stable ID so names cannot be mistaken for delimiters.
    result = tmux(args, "list-sessions", "-F", "#{session_id}|#{session_windows}|#{session_attached}")
    if result.returncode:
        if no_server(result.stderr):
            return []
        raise Error("cannot list sessions; check tmux socket permissions", "tmux_failure")
    sessions = []
    seen = set()
    for row in result.stdout.splitlines():
        fields = row.split("|")
        if len(fields) != 3 or not re.fullmatch(r"\$\d+", fields[0]) or not all(re.fullmatch(r"[0-9]{1,10}", v) for v in fields[1:]):
            raise Error("tmux returned an invalid session record", "tmux_failure")
        session_id, windows, attached = fields
        if session_id in seen or not 1 <= int(windows) <= 2147483647 or int(attached) > 2147483647:
            raise Error("tmux returned an invalid session record", "tmux_failure")
        seen.add(session_id)
        name_result = tmux(args, "display-message", "-p", "-t", session_id + ":", "#{session_name}")
        if name_result.returncode:
            if no_server(name_result.stderr) or "can't find session" in name_result.stderr:
                continue  # A session can end between the two read-only queries.
            raise Error("cannot read session details", "tmux_failure")
        name = name_result.stdout.removesuffix("\n")
        if not name:
            continue
        sessions.append({
            "id": session_id, "name": name, "windows": int(windows),
            "attached_clients": int(attached),
            "attachable": re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", name) is not None,
        })
    return sessions


def list_sessions(args):
    sessions = session_records(args)
    if args.json:
        emit("session.list", {"sessions": sessions})
        return
    if not sessions:
        print("No sessions.")
        return
    print("NAME\tWINDOWS\tATTACHED CLIENTS")
    for session in sessions:
        # Do not let manually created names inject terminal control characters.
        name = "".join(c if c.isprintable() else "?" for c in session["name"])
        print(f'{name}\t{session["windows"]}\t{session["attached_clients"]}')


def doctor(args):
    failures = 0
    checks = []

    def report(check_id, level, message):
        nonlocal failures
        checks.append({"id": check_id, "status": level.lower(), "message": message})
        if not args.json:
            print(f"{level}: {message}")
        failures += level == "FAIL"

    report("python", "OK", "Python 3.11+ available")
    report("tmux", "OK" if shutil.which("tmux") else "FAIL", "tmux available" if shutil.which("tmux") else "tmux missing (install Debian package: tmux)")
    report("ssh", "OK" if shutil.which("ssh") else "WARN", "SSH client available" if shutil.which("ssh") else "SSH client missing (optional for local sessions)")
    try:
        workspace, workloads = read_config(args.config)
        report("config", "OK", "configuration valid")
        report("workspace", "OK" if workspace.is_dir() else "FAIL", "workspace exists" if workspace.is_dir() else "workspace directory missing")
        for name, workload in workloads.items():
            try:
                available = executable(workload["command"][0]) is not None
            except Error:
                available = False
            report("workload." + name, "OK" if available else "WARN", f"workload {name}: " + ("executable available" if available else "executable unavailable (only this workload is affected)"))
    except Error as exc:
        report("config", "FAIL", str(exc))
    report("durability", "INFO", "sessions survive disconnection, not host reboot or workload exit")
    if args.json:
        emit("doctor", {"ready": failures == 0, "checks": checks},
             Error("one or more required checks failed", "doctor_failed") if failures else None)
    return 1 if failures else 0


def capabilities(args):
    data = {"schema_versions": [SCHEMA_VERSION], "config_version": 1,
            "json_commands": ["capabilities", "doctor", "session.list", "session.create"],
            "session_create_requires_detach": True}
    if args.json:
        emit("capabilities", data)
    else:
        print(f"Overtura {VERSION}; JSON schema {SCHEMA_VERSION}")
        print("JSON commands: " + ", ".join(data["json_commands"]))


def json_option(parser):
    parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="emit versioned JSON (create requires --detach)")


def parser():
    result = ArgumentParser(description=__doc__)
    result.set_defaults(json=False)
    json_option(result)
    result.add_argument("--version", action="version", version=f"overtura {VERSION}")
    result.add_argument("--config", type=Path, default=config_path(), help="private TOML config path")
    result.add_argument("--socket", type=identifier, default="overtura", help="tmux server name (default: overtura)")
    commands = result.add_subparsers(dest="command", required=True)
    json_option(commands.add_parser("setup", help="create private config without overwriting"))
    json_option(commands.add_parser("doctor", help="check requirements without changing the system"))
    json_option(commands.add_parser("capabilities", help="describe supported machine interfaces"))
    sessions = commands.add_parser("session", help="manage durable sessions")
    json_option(sessions)
    operations = sessions.add_subparsers(dest="operation", required=True)
    new = operations.add_parser("create", help="create and attach to a new session")
    new.add_argument("name", type=identifier)
    new.add_argument("--workload", type=identifier, default="shell")
    new.add_argument("--cwd", help="working directory (default: host.workspace)")
    new.add_argument("--detach", action="store_true", help="create without attaching")
    json_option(new)
    existing = operations.add_parser("attach", help="attach to an existing session")
    existing.add_argument("name", type=identifier)
    json_option(existing)
    json_option(operations.add_parser("list", help="list sessions, even without configuration"))
    return result


def main():
    args = parser().parse_args()
    command = args.command if args.command != "session" else "session." + args.operation
    try:
        if args.json and (command in {"setup", "session.attach"} or
                          (command == "session.create" and not args.detach)):
            emit(command, error=Error("JSON supports capabilities, doctor, session list and detached creation only", "unsupported_operation"))
            return 2
        if args.command == "setup":
            setup(args.config)
        elif args.command == "doctor":
            return doctor(args)
        elif args.command == "capabilities":
            capabilities(args)
        elif args.operation == "create":
            create(args)
        elif args.operation == "attach":
            attach(args)
        else:
            list_sessions(args)
    except Error as exc:
        if args.json:
            emit(command, error=exc)
        else:
            print(f"overtura: {exc}", file=sys.stderr)
        return 1
    except OSError:
        message = "operating-system error; check file and executable permissions"
        if args.json:
            emit(command, error=Error(message, "os_error"))
        else:
            print("overtura: " + message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
