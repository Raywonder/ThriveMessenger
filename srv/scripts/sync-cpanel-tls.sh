#!/usr/bin/env bash
set -euo pipefail

source_pem=/var/cpanel/ssl/apache_tls/tappedin.fm/combined
target_pem=/home/tappedin/apps/ThriveMessenger/srv/certs/tappedin-current.pem
target_dir=/home/tappedin/apps/ThriveMessenger/srv/certs
service_name=thrive-messenger.service

test "$(id -u)" -eq 0
test -r "$source_pem"
openssl x509 -in "$source_pem" -noout -checkend 86400
openssl x509 -in "$source_pem" -noout -ext subjectAltName | grep -Eq 'DNS:\*\.tappedin\.fm|DNS:tappedin\.fm'
cert_pub="$(openssl x509 -in "$source_pem" -pubkey -noout | openssl sha256)"
key_pub="$(openssl pkey -in "$source_pem" -pubout | openssl sha256)"
test "$cert_pub" = "$key_pub"

if test -r "$target_pem" && cmp -s "$source_pem" "$target_pem"; then
    echo 'Thrive TLS certificate is already current.'
    exit 0
fi

install -d -o tappedin -g tappedin -m 0750 "$target_dir"
temp_pem="$(mktemp "$target_dir/.tappedin-current.pem.XXXXXX")"
trap 'rm -f -- "$temp_pem"' EXIT
install -o tappedin -g tappedin -m 0600 "$source_pem" "$temp_pem"
mv -f -- "$temp_pem" "$target_pem"
trap - EXIT
systemctl restart "$service_name"
systemctl is-active --quiet "$service_name"
echo 'Thrive TLS certificate synchronized and service restarted.'
