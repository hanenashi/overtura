#!/usr/bin/env python3
"""Run opt-in Pixel transport checks; needs ADB, phone SSH, and local sshd.

Uses a debug APK already installed on the selected device. Temporarily changes
its alias and Termux permission, and prepends an isolated SSH alias on the phone.
Restores them in finally. Never reads terminal contents or production SSH keys.
"""
import argparse
import getpass
import os
from pathlib import Path
import re
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET

PACKAGE = 'io.github.hanenashi.overtura'
PERMISSION = 'com.termux.permission.RUN_COMMAND'
PREFS = 'shared_prefs/local_host.xml'


def run(argv, **kwargs):
    result = subprocess.run(argv, capture_output=True, timeout=30, **kwargs)
    if result.returncode:
        # Do not echo command output: it may contain device or configuration data.
        raise RuntimeError(f'{Path(argv[0]).name} failed with exit {result.returncode}')
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--phone-ssh', required=True, help='Existing SSH alias into this same phone')
    args = parser.parse_args()
    adb = ['adb', '-s', args.serial]
    remote = ['ssh', '-o', 'BatchMode=yes', args.phone_ssh, 'sh -s']
    suffix = uuid.uuid4().hex[:12]
    alias = 'overtura-qa-' + suffix
    phone_dir = '$HOME/.ssh/' + alias
    backup = '$HOME/.ssh/.' + alias + '-config'

    def shell(*words):
        return run(adb + ['shell', shlex.join(words)], text=True).strip()

    def phone(script):
        return run(remote, input=script, text=True)

    def screen():
        # Check before dumping so we cannot accidentally capture a terminal.
        active = shell('dumpsys', 'activity', 'activities')
        resumed = '\n'.join(s for s in active.splitlines() if 'ResumedActivity' in s)
        assert PACKAGE in resumed or 'permissioncontroller' in resumed, 'Unexpected foreground app'
        shell('uiautomator', 'dump', '/data/local/tmp/' + alias + '.xml')
        xml = shell('cat', '/data/local/tmp/' + alias + '.xml')
        return list(ET.fromstring(xml).iter('node'))

    def find(label, nodes=None):
        return next((n for n in (screen() if nodes is None else nodes)
                     if n.get('text', '').casefold() == label.casefold()), None)

    def point(node):
        assert node is not None, 'Missing control'
        x1, y1, x2, y2 = map(int, re.findall(r'\d+', node.get('bounds', '')))
        return (x1 + x2) // 2, (y1 + y2) // 2

    def tap_node(node):
        x, y = point(node)
        shell('input', 'tap', str(x), str(y))
        time.sleep(.3)

    def tap(label):
        tap_node(find(label))

    def wait_text(label, timeout=25):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if find(label) is not None:
                return
            time.sleep(.2)
        raise AssertionError('Missing expected state: ' + label)

    def launch():
        shell('am', 'start', '-W', '-n', PACKAGE + '/.MainActivity')
        time.sleep(.4)

    def scroll_to(label):
        for _ in range(16):
            ns = screen()
            node = find(label, ns)
            if node is not None:
                return node
            viewport = next(n for n in ns if n.get('class') == 'android.widget.ScrollView')
            x1,y1,x2,y2 = map(int,re.findall(r'\d+',viewport.get('bounds')))
            shell('input','swipe',str((x1+x2)//2),str(y2-80),str((x1+x2)//2),str(y1+100),'250')
        raise AssertionError('Cannot scroll to ' + label)

    permission_dump = shell('dumpsys', 'package', PACKAGE)
    granted = bool(re.search(re.escape(PERMISSION) + r': granted=true', permission_dump))
    permission_line = next(s for s in permission_dump.splitlines() if PERMISSION + ': granted=' in s)
    flags = [f for f in ('user-set','user-fixed') if f.upper().replace('-','_') in permission_line]
    shell('am', 'force-stop', PACKAGE)
    original_prefs = run(adb + ['exec-out', 'run-as', PACKAGE, 'cat', PREFS])
    prefs_backup = 'files/' + alias + '-preferences.xml'
    shell('run-as', PACKAGE, 'mkdir', '-p', 'files')
    shell('run-as', PACKAGE, 'cp', '-p', PREFS, prefs_backup)
    # This runner intentionally requires an existing prefs file; no first-install mutation.
    reverse_added = False
    server = None
    with tempfile.TemporaryDirectory(prefix='overtura-reliability-') as temp:
        work = Path(temp)
        try:
            for name in ('host', 'client'):
                run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(work/name)])
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            fixtures = Path(__file__).resolve().parents[1] / 'tests/fixtures/protocol-v1'
            for name in ('doctor-ok.json','doctor-failed.json'):
                (work/name).write_bytes((fixtures/name).read_bytes())
            (work/'mode').write_text('ok')
            (work/'serve.py').write_text('''import os, sys, time
from pathlib import Path
p=Path(__file__).parent
mode=(p/'mode').read_text().strip()
with (p/'requests').open('a') as out: out.write(mode+'\\n')
if not os.environ.get('SSH_ORIGINAL_COMMAND','').endswith('--json doctor'):
    sys.exit(2)
if mode=='old':
    print('unrecognized argument: --json',file=sys.stderr)
    sys.exit(2)
if mode=='timeout': time.sleep(35)
if mode=='delayed': time.sleep(8)
failed=mode=='failed'
print((p/('doctor-failed.json' if failed else 'doctor-ok.json')).read_text(),end='')
sys.exit(1 if failed else 0)
''')
            key=(work/'client.pub').read_text().strip()
            (work/'authorized_keys').write_text(f'restrict,command="{sys.executable} {work}/serve.py" {key}\n')
            config = f'''Port {port}
ListenAddress 127.0.0.1
HostKey {work}/host
PidFile {work}/sshd.pid
AuthorizedKeysFile {work}/authorized_keys
StrictModes no
UsePAM no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AllowUsers {getpass.getuser()}
AllowTcpForwarding no
PermitTTY no
LogLevel ERROR
'''
            (work/'sshd_config').write_text(config)
            log=(work/'sshd.log').open('wb')
            server=subprocess.Popen(['/usr/sbin/sshd','-D','-e','-f',str(work/'sshd_config')],
                                    stdout=log,stderr=log,start_new_session=True)
            time.sleep(.5)
            assert server.poll() is None, 'Temporary sshd did not start'
            run(adb+['reverse',f'tcp:{port}',f'tcp:{port}'])
            reverse_added=True
            phone(f'mkdir -p "{phone_dir}"\nchmod 700 "{phone_dir}"\n')
            # Transfer only throwaway test keys through stdin; never print them.
            run(['ssh','-o','BatchMode=yes',args.phone_ssh,
                 f'umask 077; cat > "{phone_dir}/key"'], input=(work/'client').read_bytes())
            host_key=(work/'host.pub').read_text().split()[:2]
            phone(f'printf "%s\\n" {shlex.quote(f"[127.0.0.1]:{port} " + " ".join(host_key))} > "{phone_dir}/known_hosts"\n')
            block=f'''Host {alias}
    HostName 127.0.0.1
    Port {port}
    User {getpass.getuser()}
    IdentityFile ~/.ssh/{alias}/key
    IdentitiesOnly yes
    UserKnownHostsFile ~/.ssh/{alias}/known_hosts
    StrictHostKeyChecking yes
    ProxyCommand none
    ProxyJump none

'''
            # Move the original in the same directory, preserving symlinks and metadata.
            phone(f'''set -eu
if [ -e "$HOME/.ssh/config" ] || [ -L "$HOME/.ssh/config" ]; then
    mv "$HOME/.ssh/config" "{backup}"
else
    touch "{phone_dir}/no-original-config"
fi
umask 077
printf '%s' {shlex.quote(block)} > "$HOME/.ssh/config"
if [ -e "{backup}" ]; then cat "{backup}" >> "$HOME/.ssh/config"; fi
''')
            # Confirm the path reaches the isolated server before touching app permissions.
            output=phone(f'ssh -T -o BatchMode=yes {shlex.quote(alias)} "exec \\"\\$HOME/.local/bin/overtura\\" --json doctor"\n')
            assert 'schema_version' in output, 'Fixture connection failed'
            (work/'requests').unlink()
            prefs=ET.fromstring(original_prefs)
            host=next((n for n in prefs if n.get('name')=='host'),None)
            if host is None: host=ET.SubElement(prefs,'string',name='host')
            host.text=alias
            run(adb+['shell','run-as',PACKAGE,'sh','-c',shlex.quote('cat > '+PREFS)],
                input=ET.tostring(prefs,encoding='utf-8',xml_declaration=True))
            shell('pm','revoke',PACKAGE,PERMISSION)
            shell('pm','clear-permission-flags',PACKAGE,PERMISSION,'user-set','user-fixed')
            launch(); tap('Install'); tap_node(scroll_to('Check host now'))
            ns=screen()
            deny=next(n for n in ns if n.get('resource-id','').endswith('/permission_deny_button'))
            tap_node(deny); wait_text('Permission needed'); tap('OK')
            assert not (work/'requests').exists(), 'Denied permission still reached SSH'
            # Manual command preview remains available after denying the live permission.
            tap('Sessions'); tap_node(scroll_to('List sessions'))
            wait_text('List host sessions'); tap('Cancel'); tap('Install')
            print('PASS: denied permission, no SSH request, manual fallback',flush=True)
            shell('pm','grant',PACKAGE,PERMISSION)

            for mode,expected in (
                ('failed','Host needs attention'),
                ('old','Update the host CLI or check its installation in Termux.'),
                ('timeout','The request timed out. Previous results may be out of date.'),
                ('ok','Updated just now')):
                (work/'mode').write_text(mode)
                before=point(find('Check host now'))[1]
                started=time.monotonic(); tap('Check host now'); wait_text(expected)
                elapsed=time.monotonic()-started
                assert abs(point(find('Check host now'))[1]-before)<20, 'Query reset scroll'
                assert mode in (work/'requests').read_text().splitlines(), 'Fixture was not reached'
                if mode=='timeout': assert 15 <= elapsed < 28, 'Timeout outside expected bound'
                print('PASS:',mode,'reply and preserved scroll',flush=True)

            (work/'mode').write_text('delayed')
            tap('Check host now')
            shell('input','keyevent','KEYCODE_HOME'); time.sleep(.6); launch()
            time.sleep(9)
            ns=screen()
            assert find('Updated just now',ns) is None and find('Checking…',ns) is None
            assert find('Previous result · out of date',ns) is not None
            print('PASS: background cancellation ignores late callback',flush=True)

            before=point(find('Check host now'))[1]
            old_pid=shell('pidof',PACKAGE)
            shell('input','keyevent','KEYCODE_HOME'); time.sleep(.6)
            shell('am','kill',PACKAGE); time.sleep(.5)
            launch()
            assert shell('pidof',PACKAGE)!=old_pid, 'App process did not restart'
            assert abs(point(find('Check host now'))[1]-before)<20, 'Process recreation reset scroll'
            assert find('Updated just now') is None
            print('PASS: process recreation restores tab/scroll without fresh host claims',flush=True)
        finally:
            cleanup_errors = []

            def clean(label, action):
                try:
                    action()
                except Exception:
                    cleanup_errors.append(label)

            def restore_app():
                shell('am', 'force-stop', PACKAGE)
                shell('run-as', PACKAGE, 'cp', '-p', prefs_backup, PREFS)
                assert run(adb + ['exec-out', 'run-as', PACKAGE, 'cat', PREFS]) == original_prefs
                shell('run-as', PACKAGE, 'rm', prefs_backup)

            def restore_permission():
                shell('pm', 'grant' if granted else 'revoke', PACKAGE, PERMISSION)
                shell('pm', 'clear-permission-flags', PACKAGE, PERMISSION, 'user-set', 'user-fixed')
                if flags:
                    shell('pm', 'set-permission-flags', PACKAGE, PERMISSION, *flags)

            def restore_phone():
                phone(f'''set -eu
if [ -e "{backup}" ] || [ -L "{backup}" ]; then
    rm -f "$HOME/.ssh/config"
    mv "{backup}" "$HOME/.ssh/config"
elif [ -e "{phone_dir}/no-original-config" ]; then
    rm -f "$HOME/.ssh/config"
fi
rm -rf "{phone_dir}"
''')

            def stop_server():
                if server is not None and server.poll() is None:
                    os.killpg(server.pid, signal.SIGTERM)
                    server.wait(timeout=5)

            clean('app preferences (backup: ' + prefs_backup + ')', restore_app)
            clean('Termux permission', restore_permission)
            clean('Termux config (backup: ' + backup + ')', restore_phone)
            if reverse_added:
                clean('ADB reverse', lambda: run(adb + ['reverse', '--remove', f'tcp:{port}']))
            clean('temporary SSH server', stop_server)
            clean('UI dump', lambda: shell('rm', '-f', '/data/local/tmp/' + alias + '.xml'))
            if cleanup_errors:
                raise RuntimeError('Cleanup needs attention: ' + ', '.join(cleanup_errors))
            launch()
            print('Restored app preferences, permission flags, and Termux SSH configuration.',flush=True)


if __name__=='__main__':
    main()
