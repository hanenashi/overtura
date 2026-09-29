#!/bin/sh
set -eu
mkdir -p /run/sshd
ssh-keygen -A >/dev/null
exec /usr/sbin/sshd -D -e -f /etc/ssh/overtura_lab_config
