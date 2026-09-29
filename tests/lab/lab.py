#!/usr/bin/env python3
"""Disposable rootless Debian lab. Never mounts the host workspace or home."""

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
NAME = "overtura-lab-debian13"
IMAGE = "localhost/overtura-lab:debian13"
LABEL = "io.overtura.disposable-lab"
PORT = 22222
STATE = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "overtura/lab"
FILES = (
    "overtura.py", "install.py", "tests/test_cli.py",
    "tests/lab/Containerfile", "tests/lab/sshd_config", "tests/lab/start-sshd.sh",
    "tests/fixtures/protocol-v1/capabilities.json",
    "tests/fixtures/protocol-v1/doctor-ok.json", "tests/fixtures/protocol-v1/doctor-failed.json",
    "tests/fixtures/protocol-v1/sessions.json", "tests/fixtures/protocol-v1/sessions-empty.json",
    "tests/fixtures/protocol-v1/dependency-error.json",
)


class LabError(Exception):
    pass


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, text=True, **kwargs)


def container():
    found = subprocess.run(
        ["podman", "container", "exists", NAME], capture_output=True
    )
    if found.returncode == 1:
        return None
    if found.returncode:
        raise LabError("Podman cannot inspect the lab; check rootless Podman setup")
    info = json.loads(run(["podman", "container", "inspect", NAME], capture_output=True).stdout)[0]
    if (info["Config"].get("Labels") or {}).get(LABEL) != "1":
        raise LabError("refusing to change an existing container without the lab ownership label")
    return info


def build():
    # Only an explicit source allowlist enters the build context, never .git,
    # user configuration, private keys, or unrelated files in the checkout.
    with tempfile.TemporaryDirectory(prefix="overtura-build-") as temporary:
        context = Path(temporary)
        for name in FILES:
            destination = context / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        run(["podman", "build", "--label", LABEL + "=1", "--tag", IMAGE,
             "--file", str(context / "tests/lab/Containerfile"), str(context)])


def ssh_base(tty=False):
    if not (STATE / "ssh_config").is_file():
        raise LabError("lab SSH configuration missing; run lab.py up first")
    return ["ssh", "-F", str(STATE / "ssh_config"), "-tt" if tty else "-T", "overtura-lab"]


def ssh(*argv, **kwargs):
    return run(ssh_base() + [shlex.join(argv)], **kwargs)


def up():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = STATE / "id_ed25519"
    if not key.exists():
        run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "disposable-overtura-lab", "-f", str(key)], stdout=subprocess.DEVNULL)
    if not key.with_suffix(".pub").is_file():
        raise LabError("lab public key missing; repair the dedicated lab key pair")
    info = container()
    if info is None:
        build()
        run(["podman", "run", "--detach", "--name", NAME, "--label", LABEL + "=1",
             "--memory", "512m", "--cpus", "1", "--pids-limit", "128",
             "--publish", f"127.0.0.1:{PORT}:22", IMAGE], stdout=subprocess.DEVNULL)
    elif not info["State"]["Running"]:
        run(["podman", "start", NAME], stdout=subprocess.DEVNULL)
    run(["podman", "cp", str(key.with_suffix(".pub")), NAME + ":/home/tester/.ssh/authorized_keys"])
    run(["podman", "exec", NAME, "chown", "tester:tester", "/home/tester/.ssh/authorized_keys"])
    run(["podman", "exec", NAME, "chmod", "600", "/home/tester/.ssh/authorized_keys"])
    public_host_key = None
    for _ in range(50):
        result = subprocess.run(["podman", "exec", NAME, "cat", "/etc/ssh/ssh_host_ed25519_key.pub"], capture_output=True, text=True)
        if result.returncode == 0:
            public_host_key = result.stdout.strip()
            break
        time.sleep(0.1)
    if not public_host_key:
        raise LabError("lab SSH host key was not created")
    # Trust comes from our container control channel, not an unauthenticated scan.
    (STATE / "known_hosts").write_text(f"[127.0.0.1]:{PORT} {public_host_key}\n")
    (STATE / "ssh_config").write_text(
        "Host overtura-lab\n"
        f"  HostName 127.0.0.1\n  Port {PORT}\n  User tester\n"
        f'  IdentityFile "{key}"\n  UserKnownHostsFile "{STATE / "known_hosts"}"\n'
        "  IdentitiesOnly yes\n  IdentityAgent none\n  BatchMode yes\n"
        "  StrictHostKeyChecking yes\n  ForwardAgent no\n  ConnectTimeout 5\n"
    )
    (STATE / "ssh_config").chmod(0o600)
    for _ in range(20):
        result = subprocess.run(ssh_base() + ["true"], capture_output=True)
        if result.returncode == 0:
            print(f"Debian lab ready at 127.0.0.1:{PORT}. Use lab.py shell or lab.py check.")
            return
        time.sleep(0.2)
    raise LabError("SSH is not ready; inspect the lab with podman logs " + NAME)


def pane(name, field):
    return ssh("tmux", "-L", "overtura", "display-message", "-p", "-t", "=" + name + ":", "#{" + field + "}", capture_output=True).stdout.strip()


def connection_probe(name, abrupt):
    client = subprocess.Popen(ssh_base(tty=True) + [
        shlex.join(["/home/tester/.local/bin/overtura", "session", "attach", name])
    ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=dict(os.environ, TERM="xterm"))
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if pane(name, "session_attached") == "1":
                break
            if client.poll() is not None:
                raise LabError("SSH terminal client exited before attaching")
            time.sleep(0.1)
        else:
            raise LabError("SSH terminal client did not attach")
        if abrupt:
            client.kill()
        else:
            client.stdin.write(b"\x02d")
            client.stdin.flush()
        client.wait(timeout=10)
        if not abrupt and client.returncode:
            raise LabError("normal SSH/tmux detach failed")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if pane(name, "session_attached") == "0":
                return
            time.sleep(0.1)
        raise LabError("SSH client remained attached after connection closed")
    finally:
        if client.poll() is None:
            client.kill()
            client.wait()
        client.stdin.close()


def check():
    info = container()
    if not info or not info["State"]["Running"]:
        raise LabError("start the lab with lab.py up first")
    ssh("python3", "/opt/overtura/install.py", "--upgrade")
    # Setup is intentionally idempotent here without replacing a user's config.
    ssh("sh", "-c", 'test -e "$HOME/.config/overtura/config.toml" || "$HOME/.local/bin/overtura" setup')
    ssh("/home/tester/.local/bin/overtura", "doctor")
    for operation in [("capabilities",), ("doctor",), ("session", "list")]:
        reply = json.loads(ssh("/home/tester/.local/bin/overtura", "--json", *operation, capture_output=True).stdout)
        if reply.get("schema_version") != 1 or reply.get("ok") is not True:
            raise LabError("JSON query failed validation over SSH")
    failed_query = shlex.join(["env", "XDG_CONFIG_HOME=/tmp/overtura-no-config-" + uuid.uuid4().hex,
                              "/home/tester/.local/bin/overtura", "--json", "doctor"])
    failure = subprocess.run(ssh_base() + [failed_query], text=True, capture_output=True, timeout=15)
    report = json.loads(failure.stdout)
    if failure.returncode != 1 or report.get("ok") is not False or report.get("error", {}).get("code") != "doctor_failed":
        raise LabError("failed doctor did not preserve its structured report over SSH")
    print("PASS: versioned JSON success and failed diagnostics round-trip over SSH.")
    ssh("python3", "-m", "unittest", "discover", "-s", "/opt/overtura/tests", "-v")
    name = "ssh-probe-" + uuid.uuid4().hex[:12]
    ssh("/home/tester/.local/bin/overtura", "session", "create", name, "--detach")
    try:
        before = pane(name, "pane_pid")
        if not before.isdigit():
            raise LabError("test shell has no process ID")
        connection_probe(name, abrupt=True)
        connection_probe(name, abrupt=False)
        if pane(name, "pane_pid") != before:
            raise LabError("the shell process changed after SSH reconnection")
        print("PASS: real SSH connection loss and reattachment preserved the shell process.")
    finally:
        ssh("tmux", "-L", "overtura", "kill-session", "-t", "=" + name, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["up", "check", "shell", "status", "down", "reset"])
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.exit(1, "Run this lab as your regular user, never with sudo.\n")
    if not shutil.which("podman"):
        parser.exit(1, "Podman is missing. Install podman, uidmap, passt and fuse-overlayfs first.\n")
    try:
        if args.command in {"down", "reset"}:
            if container():
                run(["podman", "rm", "--force", NAME], stdout=subprocess.DEVNULL)
            print("Lab container removed; image cache and dedicated lab SSH keys retained.")
        if args.command in {"up", "reset"}:
            up()
        elif args.command == "check":
            check()
        elif args.command == "shell":
            command = ssh_base(tty=True)
            os.execvp(command[0], command)
        elif args.command == "status":
            info = container()
            print("not created" if info is None else "running" if info["State"]["Running"] else "stopped")
    except (LabError, OSError, subprocess.SubprocessError) as exc:
        print(f"Lab failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
