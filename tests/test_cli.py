import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
import venv

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "overtura.py"
INSTALLER = ROOT / "install.py"


class CliHarness(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="overtura-test-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = dict(os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / "config"), TERM="xterm", LC_ALL="C")
        self.env.pop("TMUX", None)
        self.socket = "overtura-test-" + uuid.uuid4().hex
        self.config = self.home / "config/overtura/config.toml"

    def run_cli(self, *args, env=None):
        return subprocess.run([sys.executable, str(CLI), "--socket", self.socket, *args], env=env or self.env, text=True, capture_output=True, timeout=10)

    def configure(self, command=None, workspace=None):
        self.assertEqual(self.run_cli("setup").returncode, 0)
        self.config.write_text(
            "version = 1\n[host]\nworkspace = " + json.dumps(str(workspace or self.home))
            + "\n[workloads.shell]\ncommand = " + json.dumps(command or ["/bin/sh"]) + "\n"
        )

    def install(self, *args):
        return subprocess.run([sys.executable, str(INSTALLER), "--prefix", str(self.home / "install space"), *args], env=self.env, capture_output=True, text=True, timeout=10)


class CliTests(CliHarness):
    def test_setup_private_and_no_overwrite(self):
        self.assertEqual(self.run_cli("setup").returncode, 0)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.config.parent.stat().st_mode & 0o777, 0o700)
        self.config.write_text("keep my config")
        self.assertNotEqual(self.run_cli("setup").returncode, 0)
        self.assertEqual(self.config.read_text(), "keep my config")

    def test_setup_refuses_symlink(self):
        self.config.parent.mkdir(parents=True)
        destination = self.home / "private"
        destination.write_text("untouched")
        self.config.symlink_to(destination)
        self.assertNotEqual(self.run_cli("setup").returncode, 0)
        self.assertEqual(destination.read_text(), "untouched")

    def test_doctor_aggregates_failures_without_tmux_or_config(self):
        env = dict(self.env, PATH=str(self.home / "empty"))
        result = self.run_cli("doctor", env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("tmux missing", result.stdout)
        self.assertIn("configuration missing", result.stdout)
        self.assertIn("SSH client missing", result.stdout)

    def test_doctor_does_not_echo_invalid_config(self):
        self.configure()
        self.config.write_text("version = fake-private-value")
        result = self.run_cli("doctor")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("fake-private-value", result.stdout + result.stderr)

    def test_schema_rejects_typos_and_relative_workspace(self):
        self.configure()
        initial = self.config.read_text()
        for text in [initial.replace("version = 1", "version = true"), initial.replace("workspace", "workspce"), initial.replace(json.dumps(str(self.home)), '"relative"'), initial.replace('["/bin/sh"]', '"/bin/sh"')]:
            with self.subTest(config=text):
                self.config.write_text(text)
                self.assertEqual(self.run_cli("doctor").returncode, 1)

    def test_attach_requires_terminal_without_creating_server(self):
        result = self.run_cli("session", "attach", "work")
        self.assertEqual(result.returncode, 1)
        self.assertIn("needs a terminal", result.stderr)

    def test_invalid_session_names(self):
        for name in ["-danger", "a:b", "a.b", "../work", "a;touch", "a" * 65]:
            result = self.run_cli("session", "create", name, "--detach")
            self.assertNotEqual(result.returncode, 0)

    def test_install_upgrade_uninstall_preserves_config(self):
        self.configure()
        before = self.config.read_bytes()
        self.assertEqual(self.install().returncode, 0)
        target = self.home / "install space/bin/overtura"
        self.assertTrue(os.access(target, os.X_OK))
        version = subprocess.run([str(target), "--version"], capture_output=True, text=True, env=self.env)
        self.assertEqual(version.stdout.strip(), "overtura 0.1.0")
        self.assertNotEqual(self.install().returncode, 0)
        self.assertEqual(self.install("--upgrade").returncode, 0)
        self.assertEqual(self.install("--uninstall").returncode, 0)
        self.assertFalse(target.exists())
        self.assertEqual(self.config.read_bytes(), before)

    def test_installer_refuses_unmanaged_file_and_symlink(self):
        target = self.home / "install space/bin/overtura"
        target.parent.mkdir(parents=True)
        target.write_text("do not replace")
        for option in ["--upgrade", "--uninstall"]:
            self.assertNotEqual(self.install(option).returncode, 0)
            self.assertEqual(target.read_text(), "do not replace")
        target.unlink()
        target.symlink_to(CLI)
        self.assertNotEqual(self.install("--upgrade").returncode, 0)
        self.assertNotEqual(self.install("--uninstall").returncode, 0)
        self.assertTrue(target.is_symlink())


@unittest.skipUnless(shutil.which("tmux"), "real tmux required")
class TmuxTests(CliHarness):
    def setUp(self):
        super().setUp()
        self.addCleanup(lambda: self.raw_tmux("kill-server"))

    def raw_tmux(self, *args):
        return subprocess.run(["tmux", "-L", self.socket, *args], env=self.env, capture_output=True, text=True, timeout=5)

    def test_doctor_optional_agent(self):
        self.configure(command=["overtura-nonexistent-agent"])
        result = self.run_cli("doctor")
        self.assertEqual(result.returncode, 0)
        self.assertIn("WARN: workload shell", result.stdout)
        self.assertNotEqual(self.run_cli("session", "create", "work", "--detach").returncode, 0)
        self.assertNotEqual(self.raw_tmux("has-session").returncode, 0)

    def test_missing_workspace_blocks_creation(self):
        self.configure(workspace=self.home / "missing")
        self.assertEqual(self.run_cli("doctor").returncode, 1)
        self.assertEqual(self.run_cli("session", "create", "work", "--detach").returncode, 1)
        self.assertNotEqual(self.raw_tmux("has-session").returncode, 0)

    def test_empty_list_does_not_require_config(self):
        result = self.run_cli("session", "list")
        self.assertEqual(result.returncode, 0)
        self.assertIn("No sessions", result.stdout)

    def test_shell_lifecycle_duplicate_and_uninstall_recovery(self):
        self.configure()
        result = self.run_cli("session", "create", "work", "--detach")
        self.assertEqual(result.returncode, 0, result.stderr)
        pane_pid = self.raw_tmux("display-message", "-p", "-t", "=work:", "#{pane_pid}").stdout.strip()
        self.assertTrue(pane_pid.isdigit())
        result = self.run_cli("session", "create", "work", "--detach")
        self.assertEqual(result.returncode, 1)
        self.assertIn("already exists", result.stderr)
        self.assertEqual(self.run_cli("session", "create", "other", "--detach").returncode, 0)
        self.config.unlink()
        self.assertIn("work", self.run_cli("session", "list").stdout)
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.install("--uninstall").returncode, 0)
        self.assertEqual(self.raw_tmux("display-message", "-p", "-t", "=work:", "#{pane_pid}").stdout.strip(), pane_pid)

    def test_arguments_and_cwd_survive_shell_boundary(self):
        workspace = self.home / "space ' ; $(touch should-not-exist)"
        workspace.mkdir()
        script = self.home / "writer ' script.py"
        output = self.home / "arguments.json"
        script.write_text("import json, os, sys, time\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(json.dumps([os.getcwd(), sys.argv[2:]]))\ntime.sleep(60)\n")
        arguments = ["", "a b", "$(touch should-not-exist)", "'; touch should-not-exist; #", "$HOME", "line\nbreak"]
        self.configure(command=[sys.executable, str(script), str(output), *arguments], workspace=workspace)
        result = self.run_cli("session", "create", "args", "--detach")
        self.assertEqual(result.returncode, 0, result.stderr)
        deadline = time.monotonic() + 5
        while not output.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertEqual(json.loads(output.read_text()), [str(workspace), arguments])
        self.assertFalse((workspace / "should-not-exist").exists())

    def test_workload_preserves_virtualenv_interpreter(self):
        environment = self.home / "agent runtime"
        venv.EnvBuilder(with_pip=False, symlinks=True).create(environment)
        output = self.home / "runtime.txt"
        script = "import pathlib, sys, time; pathlib.Path(sys.argv[1]).write_text(sys.prefix); time.sleep(60)"
        self.configure(command=[str(environment / "bin/python"), "-c", script, str(output)])
        result = self.run_cli("session", "create", "agent", "--detach")
        self.assertEqual(result.returncode, 0, result.stderr)
        deadline = time.monotonic() + 5
        while not output.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertEqual(output.read_text(), str(environment))

    def attach_and_detach(self, abrupt=False):
        pid, fd = pty.fork()
        if pid == 0:
            os.execve(sys.executable, [sys.executable, str(CLI), "--socket", self.socket, "session", "attach", "work"], self.env)
        reaped = False
        try:
            deadline = time.monotonic() + 5
            attached = False
            while time.monotonic() < deadline:
                if select.select([fd], [], [], 0.05)[0]:
                    try:
                        os.read(fd, 65536)
                    except OSError:
                        break
                status = self.raw_tmux("display-message", "-p", "-t", "=work:", "#{session_attached}").stdout.strip()
                if status == "1":
                    attached = True
                    break
            self.assertTrue(attached, "tmux client did not attach to pseudo-terminal")
            if abrupt:
                os.close(fd)
                fd = -1
            else:
                os.write(fd, b"\x02d")
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                child, status = os.waitpid(pid, os.WNOHANG)
                if child:
                    reaped = True
                    if not abrupt:
                        self.assertEqual(os.waitstatus_to_exitcode(status), 0)
                    return
                if fd < 0:
                    time.sleep(0.05)
                elif select.select([fd], [], [], 0.05)[0]:
                    try:
                        os.read(fd, 65536)
                    except OSError:
                        pass
            self.fail("tmux client did not detach")
        finally:
            if fd >= 0:
                os.close(fd)
            if not reaped:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)

    def test_attach_detach_reattach_retains_running_shell(self):
        self.configure()
        self.assertEqual(self.run_cli("session", "create", "work", "--detach").returncode, 0)
        before = self.raw_tmux("display-message", "-p", "-t", "=work:", "#{pane_pid}").stdout
        self.attach_and_detach()
        self.assertEqual(self.raw_tmux("display-message", "-p", "-t", "=work:", "#{session_attached}").stdout.strip(), "0")
        self.attach_and_detach()
        after = self.raw_tmux("display-message", "-p", "-t", "=work:", "#{pane_pid}").stdout
        self.assertEqual(before, after)

    def test_abrupt_terminal_loss_preserves_session(self):
        self.configure()
        self.assertEqual(self.run_cli("session", "create", "work", "--detach").returncode, 0)
        before = self.raw_tmux("display-message", "-p", "-t", "=work:", "#{pane_pid}").stdout
        self.attach_and_detach(abrupt=True)
        self.attach_and_detach()
        after = self.raw_tmux("display-message", "-p", "-t", "=work:", "#{pane_pid}").stdout
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
