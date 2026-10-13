#!/usr/bin/env bash
# Run with bash; dump stays private and includes attachments and personal data.
set -euo pipefail
umask 077
deploy_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$deploy_dir/../.." && pwd)"
backup_dir="$project_dir/backups/oci"
mkdir -p -- "$backup_dir"
chmod 700 -- "$backup_dir"
dump_file="$backup_dir/peticas-$(date -u +%Y%m%dT%H%M%SZ)-$$.dump"
partial_file="$dump_file.partial"
compose=(docker compose --env-file "$deploy_dir/.env" -f "$deploy_dir/compose.yaml")
trap 'rm -f -- "$partial_file"' EXIT
"${compose[@]}" exec -T db pg_dump -U peticas -d peticas -Fc > "$partial_file"
# Verify archive structure before considering it a completed backup.
"${compose[@]}" exec -T db pg_restore --list < "$partial_file" > /dev/null
mv -- "$partial_file" "$dump_file"
printf 'Backup criado e validado: %s\n' "$dump_file"
