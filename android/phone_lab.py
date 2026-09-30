#!/usr/bin/env python3
"""Resettable companion-app lab on a selected phone; production app data is never cleared."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'io.github.hanenashi.overtura.lab'
ACTIVITY = PACKAGE + '/io.github.hanenashi.overtura.MainActivity'
PERMISSION = 'com.termux.permission.RUN_COMMAND'
sys.path.insert(0, str(ROOT / 'tests/lab'))
import lab


def run(argv, **kwargs):
    result = subprocess.run(argv, capture_output=True, timeout=120, **kwargs)
    if result.returncode:
        raise RuntimeError(Path(argv[0]).name + ' failed; no private command output was printed')
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['up', 'connect', 'reset', 'status', 'remove'])
    parser.add_argument('--serial', required=True, help='Explicit ADB transport')
    parser.add_argument('--phone-ssh', help='SSH alias into Termux on the same phone (up/connect/remove)')
    args = parser.parse_args()
    if args.command in {'up', 'connect', 'remove'} and not args.phone_ssh:
        parser.error('--phone-ssh is required for this command')
    adb = ['adb', '-s', args.serial]

    def shell(*words):
        return run(adb + ['shell', shlex.join(words)], text=True).strip()

    def installed():
        return 'package:' + PACKAGE in shell('pm', 'list', 'packages', '--user', '0', PACKAGE).splitlines()

    def phone(payload):
        script = (ROOT / 'android/phone_lab_config.py').read_text()
        run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '--', args.phone_ssh,
             'python -c ' + shlex.quote(script)], input=json.dumps(payload), text=True)

    try:
        if shell('am', 'get-current-user') != '0':
            raise RuntimeError('This lab requires Android primary user 0, like stock Termux.')
        forwards = run(adb + ['reverse', '--list'], text=True).splitlines()
        ours = [line.split() for line in forwards if ' tcp:22333 ' in line]
        if any(row[-1] != 'tcp:22222' for row in ours):
            raise RuntimeError('Phone port 22333 is already forwarded elsewhere; refusing to replace it.')
        if args.command == 'up':
            subprocess.run([str(ROOT / 'android/gradlew'), '--quiet', '-p', str(ROOT / 'android'), 'assembleLab'], check=True)
            run(adb + ['install', '-r', str(ROOT / 'android/app/build/outputs/apk/lab/app-lab.apk')])
        if args.command in {'up', 'connect'}:
            if not installed():
                raise RuntimeError('Install the lab app with up first.')
            lab.up()  # Preserve an existing container and its test sessions.
            lab.ssh('python3', '/opt/overtura/install.py', '--upgrade', capture_output=True)
            lab.ssh('sh', '-c', 'test -e "$HOME/.config/overtura/config.toml" || "$HOME/.local/bin/overtura" setup',
                    capture_output=True)
            known = (lab.STATE / 'known_hosts').read_text().replace('[127.0.0.1]:22222 ', '[127.0.0.1]:22333 ')
            phone({'action': 'up', 'key': (lab.STATE / 'id_ed25519').read_text(), 'known_hosts': known})
            if not ours:
                run(adb + ['reverse', '--no-rebind', 'tcp:22333', 'tcp:22222'])
            output = run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '--', args.phone_ssh,
                          'ssh -T -o BatchMode=yes overtura-phone-lab '
                          + shlex.quote('exec "$HOME/.local/bin/overtura" --json doctor')], text=True)
            if json.loads(output).get('ok') is not True:
                raise RuntimeError('Disposable host Doctor was not healthy.')
            print('PASS: phone SSH reaches the disposable Debian host; Doctor is healthy.')
        elif args.command == 'reset':
            if not installed():
                raise RuntimeError('Lab app is not installed.')
            if shell('pm', 'clear', '--user', '0', PACKAGE) != 'Success':
                raise RuntimeError('Lab app data reset was not confirmed.')
            shell('pm', 'revoke', '--user', '0', PACKAGE, PERMISSION)
            shell('pm', 'clear-permission-flags', '--user', '0', PACKAGE, PERMISSION, 'user-set', 'user-fixed')
            shell('am', 'force-stop', PACKAGE)
            print('Only Overtura Lab preferences and command permission were reset.')
        elif args.command == 'remove':
            phone({'action': 'remove'})
            if ours:
                run(adb + ['reverse', '--remove', 'tcp:22333'])
            if installed():
                run(adb + ['uninstall', PACKAGE])
            print('Lab app, owned phone SSH files/block and forwarding removed. Debian lab retained.')
            return 0
        if args.command != 'status':
            shell('am', 'start', '--user', '0', '-n', ACTIVITY)
        print('Overtura Lab: ' + ('installed' if installed() else 'not installed'))
        print('Test SSH alias: overtura-phone-lab')
        print('Termux tools and external-apps setting are shared with normal use.')
        print('ADB must stay connected for the disposable host route; use connect after reconnecting.')
    except (RuntimeError, lab.LabError) as error:
        print('Phone lab failed: ' + str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError, subprocess.SubprocessError):
        print('Phone lab operation failed. Existing app data was preserved except an explicitly requested lab reset/remove. '
              'Retry connect/up after checking ADB, phone SSH and Podman.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
