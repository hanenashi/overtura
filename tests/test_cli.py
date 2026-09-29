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
        self.assertEqual(version.stdout.strip(), "overtura 0.2.0")
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


class JsonHarness(CliHarness):
    def fixture(self, name):
        return json.loads((ROOT / "tests/fixtures/protocol-v1" / (name + ".json")).read_text())

    def parse(self, result, command, success):
        self.assertEqual(result.stderr, "")
        data = json.loads(result.stdout)
        self.assertEqual(set(data), {"schema_version", "cli_version", "command", "ok", "data", "error"})
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["command"], command)
        self.assertIs(data["ok"], success)
        self.assertEqual(result.returncode == 0, success)
        self.assertNotIn(str(self.home), result.stdout)
        return data


class JsonTests(JsonHarness):
    def test_capabilities_without_dependencies_or_config(self):
        result = self.run_cli("--json", "capabilities", env=dict(self.env, PATH=""))
        reply = self.parse(result, "capabilities", True)
        self.assertEqual(reply, self.fixture("capabilities"))
        data = reply["data"]
        self.assertEqual(data["schema_versions"], [1])
        self.assertIn("session.list", data["json_commands"])
        self.assertTrue(data["session_create_requires_detach"])

    def test_doctor_failure_is_a_complete_structured_report(self):
        result = self.run_cli("doctor", "--json", env=dict(self.env, PATH=""))
        data = self.parse(result, "doctor", False)
        self.assertEqual(data, self.fixture("doctor-failed"))
        self.assertEqual(data["error"]["code"], "doctor_failed")
        checks = {row["id"]: row for row in data["data"]["checks"]}
        self.assertEqual(checks["tmux"]["status"], "fail")
        self.assertEqual(checks["config"]["status"], "fail")
        self.assertEqual(checks["ssh"]["status"], "warn")
        self.assertFalse(data["data"]["ready"])

    def test_invalid_arguments_never_echo_private_values(self):
        for command in [("--json", "unknown-private-value"), ("session", "create", "bad;private-value", "--json"), ("--json", "--socket", "bad:private-value", "session", "list")]:
            result = self.run_cli(*command)
            data = self.parse(result, None, False)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(data["error"]["code"], "invalid_arguments")
            self.assertNotIn("private-value", result.stdout)

    def test_json_rejects_interactive_and_setup_before_side_effects(self):
        for command, operation in [("setup", ("setup",)), ("session.attach", ("session", "attach", "test")), ("session.create", ("session", "create", "test"))]:
            data = self.parse(self.run_cli("--json", *operation), command, False)
            self.assertEqual(data["error"]["code"], "unsupported_operation")
        self.assertFalse(self.config.exists())

    def test_missing_tmux_is_not_an_empty_session_list(self):
        result = self.run_cli("session", "list", "--json", env=dict(self.env, PATH=""))
        data = self.parse(result, "session.list", False)
        self.assertIsNone(data["data"])
        self.assertEqual(data, self.fixture("dependency-error"))
        self.assertEqual(data["error"]["code"], "dependency_missing")

    def test_tmux_error_is_not_empty_or_raw_stderr(self):
        fake = self.home / "tmux"
        fake.write_text("#!/bin/sh\nprintf 'private-test-value: Permission denied' >&2\nexit 1\n")
        fake.chmod(0o755)
        result = self.run_cli("--json", "session", "list", env=dict(self.env, PATH=str(self.home)))
        data = self.parse(result, "session.list", False)
        self.assertEqual(data["error"]["code"], "tmux_failure")
        self.assertNotIn("private-test-value", result.stdout)

    def test_tmux_timeout_is_a_structured_error(self):
        fake = self.home / "tmux"
        fake.write_text("#!/bin/sh\nexec /bin/sleep 20\n")
        fake.chmod(0o755)
        reply = self.parse(self.run_cli("--json", "session", "list", env=dict(self.env, PATH=str(self.home))), "session.list", False)
        self.assertEqual(reply["error"]["code"], "tmux_timeout")

    def test_invalid_tmux_record_is_a_failure(self):
        fake = self.home / "tmux"
        for record in ["bad|1|0", "$0|0|0", "$0|1|-1", "$0|1|0|extra"]:
            fake.write_text("#!/bin/sh\nprintf '%s\\n' '" + record + "'\n")
            fake.chmod(0o755)
            reply = self.parse(self.run_cli("--json", "session", "list", env=dict(self.env, PATH=str(self.home))), "session.list", False)
            self.assertEqual(reply["error"]["code"], "tmux_failure")

    def test_session_disappearing_during_listing_is_omitted(self):
        fake = self.home / "tmux"
        fake.write_text("#!/bin/sh\nif [ \"$6\" = list-sessions ]; then printf '$0|1|0\\n'; else printf \"can't find session: private-value\\n\" >&2; exit 1; fi\n")
        fake.chmod(0o755)
        reply = self.parse(self.run_cli("--json", "session", "list", env=dict(self.env, PATH=str(self.home))), "session.list", True)
        self.assertEqual(reply["data"], {"sessions": []})


@unittest.skipUnless(shutil.which("tmux"), "real tmux required")
class JsonTmuxTests(JsonHarness):
    def setUp(self):
        super().setUp()
        self.addCleanup(lambda: subprocess.run(["tmux", "-L", self.socket, "kill-server"], env=self.env, capture_output=True))

    def test_empty_sessions_are_successful_without_config(self):
        data = self.parse(self.run_cli("--json", "session", "list"), "session.list", True)
        self.assertEqual(data, self.fixture("sessions-empty"))

    def test_create_list_duplicate_and_unusual_names(self):
        self.configure()
        created = self.parse(self.run_cli("session", "create", "work", "--detach", "--json"), "session.create", True)
        self.assertRegex(created["data"]["session"]["id"], r"^\$\d+$")
        duplicate = self.parse(self.run_cli("--json", "session", "create", "work", "--detach"), "session.create", False)
        self.assertEqual(duplicate["error"]["code"], "session_exists")
        unusual = 'odd\tname\n"quoted"'
        displayed = 'odd\\tname\\n"quoted"'
        subprocess.run(["tmux", "-L", self.socket, "new-session", "-d", "-s", unusual, "/bin/sh"], env=self.env, check=True)
        listing = self.parse(self.run_cli("session", "--json", "list"), "session.list", True)
        sessions = {s["name"]: s for s in listing["data"]["sessions"]}
        self.assertIn(displayed, sessions)
        self.assertFalse(sessions[displayed]["attachable"])
        self.assertTrue(sessions["work"]["attachable"])
        self.assertEqual(sessions["work"]["attached_clients"], 0)
        self.assertEqual(sessions["work"]["windows"], 1)
        self.assertEqual(sessions["work"]["id"], created["data"]["session"]["id"])
        expected = self.fixture("sessions")
        expected["data"]["sessions"][0]["attached_clients"] = 0
        listing["data"]["sessions"].sort(key=lambda row: row["id"])
        self.assertEqual(listing, expected)

    def test_healthy_doctor_matches_shared_fixture(self):
        self.configure()
        reply = self.parse(self.run_cli("--json", "doctor"), "doctor", True)
        expected = self.fixture("doctor-ok")
        if not shutil.which("ssh"):
            expected["data"]["checks"][2].update(status="warn", message="SSH client missing (optional for local sessions)")
        self.assertEqual(reply, expected)

    def test_unicode_and_delimiters_in_native_tmux_names(self):
        for name in ["日本語", "a|b", r"a\b", "a b"]:
            result = subprocess.run(["tmux", "-u", "-L", self.socket, "new-session", "-d", "-s", name, "/bin/sh"],
                                    env=dict(self.env, LC_ALL="C.UTF-8"), capture_output=True)
            self.assertEqual(result.returncode, 0)
        for locale in ["C", "C.UTF-8"]:
            reply = self.parse(self.run_cli("--json", "session", "list", env=dict(self.env, LC_ALL=locale)), "session.list", True)
            self.assertEqual({row["name"] for row in reply["data"]["sessions"]}, {"日本語", "a|b", r"a\\b", "a b"})
            self.assertFalse(any(row["attachable"] for row in reply["data"]["sessions"]))

    def test_doctor_optional_workload_stays_ready_and_private(self):
        self.configure(command=["missing-agent", "private-command-argument"])
        data = self.parse(self.run_cli("--json", "doctor"), "doctor", True)
        self.assertTrue(data["data"]["ready"])
        self.assertIsNone(data["error"])
        self.assertNotIn("private-command-argument", json.dumps(data))
        self.assertIn("warn", [check["status"] for check in data["data"]["checks"]])


if __name__ == "__main__":
    unittest.main()
