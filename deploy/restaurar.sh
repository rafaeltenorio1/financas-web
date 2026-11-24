#!/usr/bin/env bash
set -euo pipefail
umask 077

uso() {
	cat >&2 <<'FIM'
Uso: deploy/restaurar.sh --chave ARQUIVO_DA_CHAVE [--substituir] ORIGEM

ORIGEM  caminho de um arquivo .dump.age, "ultimo" (o mais recente no R2)
        ou o nome de um arquivo no R2.

Sem --substituir, restaura numa base separada (financas_restauracao) e mostra
um resumo para conferência; o banco em uso não é tocado.
Com --substituir, troca o banco em uso pela restauração e guarda o atual
como financas_antigo_<data>.
FIM
	exit 2
}

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHAVE=""
SUBSTITUIR=0
ORIGEM=""
while (( $# )); do
	case "$1" in
		--chave) CHAVE="${2:-}"; shift 2 ;;
		--substituir) SUBSTITUIR=1; shift ;;
		-h|--help) uso ;;
		*) [[ -z "$ORIGEM" ]] || uso; ORIGEM="$1"; shift ;;
	esac
done
[[ -n "$CHAVE" && -n "$ORIGEM" ]] || uso
[[ -f "$CHAVE" ]] || { echo "Chave não encontrada: $CHAVE" >&2; exit 1; }

compose() {
	docker compose -f "$RAIZ/docker-compose.yml" --project-directory "$RAIZ" "$@"
}

sql() {
	compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$1" -v ON_ERROR_STOP=1 -tA' _ "$1"
}

BASE_TEMP="financas_restauracao"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

if [[ -f "$ORIGEM" ]]; then
	ARQUIVO="$ORIGEM"
else
	[[ -f "$RAIZ/deploy/.env" ]] && { set -a; source "$RAIZ/deploy/.env"; set +a; }
	: "${RCLONE_DESTINO:?defina RCLONE_DESTINO em deploy/.env para baixar do R2}"
	if [[ "$ORIGEM" == "ultimo" ]]; then
		ORIGEM="$(rclone lsf "$RCLONE_DESTINO" --s3-no-check-bucket --include 'financas-*.dump.age' | sort | tail -n 1)"
		[[ -n "$ORIGEM" ]] || { echo "Nenhum backup encontrado em $RCLONE_DESTINO." >&2; exit 1; }
	fi
	echo "==> Baixando $ORIGEM"
	rclone copyto "$RCLONE_DESTINO/$ORIGEM" "$TEMP_DIR/$ORIGEM" --s3-no-check-bucket
	ARQUIVO="$TEMP_DIR/$ORIGEM"
fi

BANCO="$(compose exec -T db printenv POSTGRES_DB | tr -d '\r')"

echo "==> Recriando a base $BASE_TEMP"
sql postgres <<< "DROP DATABASE IF EXISTS $BASE_TEMP WITH (FORCE); CREATE DATABASE $BASE_TEMP;" >/dev/null

echo "==> Restaurando $(basename "$ARQUIVO")"
age --decrypt --identity "$CHAVE" "$ARQUIVO" \
	| compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$1" --no-owner --exit-on-error' _ "$BASE_TEMP"

echo "==> Conferindo"
sql "$BASE_TEMP" <<'FIM'
SELECT 'versão do alembic: ' || version_num FROM alembic_version;
SELECT 'usuários: ' || count(*) FROM usuario;
SELECT 'transações: ' || count(*) FROM transacao;
SELECT 'categorias: ' || count(*) FROM categoria;
SELECT 'contas recorrentes: ' || count(*) FROM conta_recorrente;
SELECT 'transação mais recente: ' || coalesce(max(data_hora)::text, '-') FROM transacao;
FIM

if (( ! SUBSTITUIR )); then
	echo "==> Restauração conferida em $BASE_TEMP. O banco em uso ($BANCO) não foi alterado."
	echo "    Para apagar a base de conferência: DROP DATABASE $BASE_TEMP;"
	exit 0
fi

ANTIGO="${BANCO}_antigo_$(date -u +%Y%m%d%H%M%S)"
echo
echo "ATENÇÃO: o banco em uso ($BANCO) vai ser trocado por esta restauração."
echo "O atual fica guardado como $ANTIGO."
read -r -p "Digite o nome do banco ($BANCO) para confirmar: " CONFIRMACAO
[[ "$CONFIRMACAO" == "$BANCO" ]] || { echo "Cancelado." >&2; exit 1; }

echo "==> Parando a API"
compose stop api

echo "==> Trocando os bancos"
if ! sql postgres <<FIM >/dev/null
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$BANCO' AND pid <> pg_backend_pid();
BEGIN;
ALTER DATABASE "$BANCO" RENAME TO "$ANTIGO";
ALTER DATABASE $BASE_TEMP RENAME TO "$BANCO";
COMMIT;
FIM
then
	echo "Falha ao trocar os bancos. Subindo a API com o banco anterior." >&2
	compose up -d api
	exit 1
fi

echo "==> Subindo a API"
compose up -d --wait --wait-timeout 120 api

echo "==> Restauração aplicada. Banco anterior guardado como $ANTIGO."
