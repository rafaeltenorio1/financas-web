#!/usr/bin/env bash
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

compose() {
	docker compose -f docker-compose.yml "$@"
}

if ! docker network inspect proxy >/dev/null 2>&1; then
	echo "A rede 'proxy' não existe. Suba o proxy primeiro (deploy/proxy)." >&2
	exit 1
fi

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
	echo "Há alterações locais nos arquivos do repositório. Resolva antes do deploy." >&2
	exit 1
fi

echo "==> Atualizando o código"
git pull --ff-only

echo "==> Construindo a imagem da API"
compose build api

echo "==> Subindo o banco"
compose up -d --wait db

TEM_DADOS="$(compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA' <<< "SELECT to_regclass('public.alembic_version') IS NOT NULL" | tr -d '\r')"
if [[ "$TEM_DADOS" == "t" ]]; then
	echo "==> Backup antes das migrações"
	"$RAIZ/deploy/backup.sh"
else
	echo "==> Banco ainda vazio: primeiro deploy, sem backup"
fi

echo "==> Aplicando migrações"
compose run --rm --no-deps api alembic upgrade head

echo "==> Subindo a API"
compose up -d --wait --wait-timeout 120 api

echo "==> Conferindo a saúde"
compose exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/saude').read().decode())"

docker image prune -f >/dev/null
echo "==> Deploy concluído: $(git log -1 --format='%h %s')"
