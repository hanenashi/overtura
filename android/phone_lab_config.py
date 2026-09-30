"""Manage only the dedicated lab SSH block/files, executed inside Termux."""
import json
import os
from pathlib import Path
import shutil
import sys

ALIAS = 'overtura-phone-lab'
BEGIN = '# BEGIN OVERTURA PHONE LAB\n'
END = '# END OVERTURA PHONE LAB\n'
MARKER = 'Overtura disposable phone SSH lab v1\n'


def configure(home, payload):
    ssh = home / '.ssh'
    directory = ssh / ALIAS
    marker = directory / 'owner'
    config = ssh / 'config'
    if directory.is_symlink() or (directory.exists() and
            (not marker.is_file() or marker.read_text() != MARKER)):
        raise ValueError('Dedicated lab directory exists without our marker')
    original = config.read_bytes().decode('utf-8') if config.exists() else ''
    if BEGIN in original or END in original:
        if original.count(BEGIN) != 1 or original.count(END) != 1 or not original.startswith(BEGIN):
            raise ValueError('Lab SSH block changed; inspect it before retrying')
        if not marker.is_file():
            raise ValueError('Lab SSH block has no ownership marker')
        remainder = original.split(END, 1)[1]
    else:
        remainder = original
        # Conservative collision check, including mentions inside Include paths.
        if ALIAS in original:
            raise ValueError('Lab alias already appears in unrelated SSH configuration')
    if payload['action'] == 'remove':
        if original != remainder:
            config.write_bytes(remainder.encode('utf-8'))
        if directory.exists():
            shutil.rmtree(directory)
        return
    if not directory.exists():
        directory.mkdir(parents=True, mode=0o700)
        marker.write_text(MARKER)
    for name in ['key', 'known_hosts']:
        path = directory / name
        if path.is_symlink():
            raise ValueError('Refusing a symlink inside the owned lab directory')
        path.write_text(payload[name])
        path.chmod(0o600)
    block = (BEGIN + 'Host ' + ALIAS + '\n'
        '    HostName 127.0.0.1\n    Port 22333\n    User tester\n'
        '    IdentityFile ~/.ssh/' + ALIAS + '/key\n'
        '    UserKnownHostsFile ~/.ssh/' + ALIAS + '/known_hosts\n'
        '    IdentitiesOnly yes\n    IdentityAgent none\n'
        '    StrictHostKeyChecking yes\n    ForwardAgent no\n'
        '    ClearAllForwardings yes\n    PermitLocalCommand no\n'
        '    ControlMaster no\n    ControlPath none\n    RemoteCommand none\n'
        '    ProxyCommand none\n    ProxyJump none\n    ConnectTimeout 5\n'
        'Host *\n' + END)
    # Follow an existing config symlink and retain its mode. Preserve unrelated
    # UTF-8 text, including its original line endings.
    config.write_bytes((block + remainder).encode('utf-8'))


if __name__ == '__main__':
    os.umask(0o077)
    try:
        configure(Path.home(), json.load(sys.stdin))
        print('Dedicated phone lab SSH configuration ready.')
    except (ValueError, OSError):
        print('Phone lab configuration refused; inspect its owned block/files.', file=sys.stderr)
        sys.exit(1)
