#!/usr/bin/env python3
"""Install or remove the standalone CLI in a user-owned prefix."""

import argparse
import os
from pathlib import Path
import tempfile
import sys

MARKER = b"#!/usr/bin/env python3\n# overtura-managed-cli-v1\n"


def main():
    if sys.version_info < (3, 11):
        sys.exit("Overtura requires Python 3.11 or newer.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, default=Path.home() / ".local")
    parser.add_argument("--upgrade", action="store_true", help="replace an existing Overtura installation")
    parser.add_argument("--uninstall", action="store_true", help="remove CLI; keep config and sessions")
    args = parser.parse_args()
    target = args.prefix.expanduser().resolve() / "bin" / "overtura"
    try:
        exists = target.exists() or target.is_symlink()
        if exists and (target.is_symlink() or not target.is_file() or not target.read_bytes().startswith(MARKER)):
            parser.exit(1, "Refusing to change an unmanaged file or symlink.\n")
        if args.uninstall:
            if exists:
                target.unlink()
            print("CLI removed. Private configuration and running tmux sessions were preserved.")
            return
        if exists and not args.upgrade:
            parser.exit(1, "Already installed; use --upgrade to replace the CLI.\n")
        source = Path(__file__).resolve().with_name("overtura.py").read_bytes()
        if not source.startswith(MARKER):
            parser.exit(1, "Source CLI is not recognized.\n")
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".overtura-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(source)
                os.fchmod(stream.fileno(), 0o755)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        print(f"Installed {target}")
        print(f"Ensure {target.parent} is on PATH, then run overtura setup.")
    except OSError:
        parser.exit(1, "Install failed; check prefix permissions. No sudo is needed for the default prefix.\n")


if __name__ == "__main__":
    main()
