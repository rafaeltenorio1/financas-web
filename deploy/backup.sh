#!/usr/bin/env bash
set -euo pipefail
umask 077

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$RAIZ/deploy/.env"
LOCAL="${BACKUP_DIR_LOCAL:-$HOME/backups/financas}"
MANTER_LOCAL=3
TAMANHO_MINIMO=1024

if [[ ! -f "$CONFIG" ]]; then
	echo "Falta $CONFIG com AGE_DESTINATARIO e RCLONE_DESTINO." >&2
	exit 1
fi
set -a
source "$CONFIG"
set +a
: "${AGE_DESTINATARIO:?defina AGE_DESTINATARIO em deploy/.env}"
: "${RCLONE_DESTINO:?defina RCLONE_DESTINO em deploy/.env}"

exec 9>"/tmp/financas-backup.lock"
if ! flock -n 9; then
	echo "Já existe um backup em andamento." >&2
	exit 1
fi

mkdir -p "$LOCAL"
NOME="financas-$(date -u +%Y%m%dT%H%M%SZ).dump.age"
PARCIAL="$LOCAL/.$NOME.parcial"
trap 'rm -f "$PARCIAL"' EXIT

echo "==> Gerando $NOME"
docker compose -f "$RAIZ/docker-compose.yml" --project-directory "$RAIZ" exec -T db \
	sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner' \
	| age --recipient "$AGE_DESTINATARIO" > "$PARCIAL"

TAMANHO=$(stat -c %s "$PARCIAL")
if (( TAMANHO < TAMANHO_MINIMO )); then
	echo "Backup suspeito: só $TAMANHO bytes." >&2
	exit 1
fi
mv "$PARCIAL" "$LOCAL/$NOME"

echo "==> Enviando para $RCLONE_DESTINO"
rclone copyto "$LOCAL/$NOME" "$RCLONE_DESTINO/$NOME" --s3-no-check-bucket
rclone lsf "$RCLONE_DESTINO/$NOME" --s3-no-check-bucket | grep -qx "$NOME"

ls -1t "$LOCAL"/financas-*.dump.age | tail -n +$((MANTER_LOCAL + 1)) | xargs -r rm -f

if [[ -n "${BACKUP_PING_URL:-}" ]]; then
	curl -fsS -m 10 --retry 3 "$BACKUP_PING_URL" >/dev/null || echo "Aviso: não consegui avisar o monitor." >&2
fi

echo "==> Backup concluído: $NOME ($TAMANHO bytes)"
