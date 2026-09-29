#!/usr/bin/env bash
# Suite sobre los módulos empaquetados, sin montar fuentes desde el anfitrión.
set -euo pipefail
cd "$(dirname "$0")/../.."
export MSYS_NO_PATHCONV=1
IMAGE="${ERPEC_TEST_IMAGE:-erpec-lock-test:local}"
NET="erpec-net-$$"
PG="erpec-pg-$$"
if [ "$#" -gt 0 ]; then
  MODULES=("$@")
else
  mapfile -t MODULES < <(find addons -mindepth 1 -maxdepth 1 -type d -name 'erpec_*' -printf '%f\n' | sort)
fi
[ "${#MODULES[@]}" -gt 0 ] || { echo "No hay módulos para probar"; exit 1; }
INSTALL=$(IFS=,; echo "${MODULES[*]}")
TAGS=$(printf '/%s,' "${MODULES[@]}"); TAGS="${TAGS%,}"
[ -n "${ERPEC_SKIP_BUILD:-}" ] || docker build -f deployment/linux/Dockerfile -t "$IMAGE" .
cleanup() {
  docker rm -f "$PG" >/dev/null 2>&1 || echo "Revisar limpieza del contenedor de ensayo $PG" >&2
  docker network rm "$NET" >/dev/null 2>&1 || echo "Revisar limpieza de la red de ensayo $NET" >&2
}
trap cleanup EXIT
docker network create "$NET" >/dev/null
docker run -d --name "$PG" --network "$NET" -e POSTGRES_PASSWORD=test -e POSTGRES_USER=odoo postgres:17 >/dev/null
READY=0
for _ in $(seq 1 30); do
  if docker exec "$PG" pg_isready -h 127.0.0.1 -U odoo >/dev/null 2>&1; then READY=1; break; fi
  sleep 2
done
[ "$READY" -eq 1 ] || { echo "PostgreSQL no inició"; exit 1; }
LOG="$(mktemp)"
set +e
docker run --rm --network "$NET" --entrypoint python "$IMAGE" \
  /opt/odoo/odoo-bin --db_host "$PG" --db_user odoo --db_password test -d linux_test \
  --addons-path /opt/odoo/addons,/opt/odoo/odoo/addons,/opt/erpec/addons --without-demo=all \
  -i "$INSTALL" --test-tags "$TAGS" --stop-after-init --no-http 2>&1 | tee "$LOG"
CODES=("${PIPESTATUS[@]}")
set -e
[ "${CODES[0]}" -eq 0 ] && [ "${CODES[1]}" -eq 0 ] || { echo "Falló Docker o la captura del registro: $LOG"; exit 1; }
RESULT=$(grep -E "odoo.tests.result" "$LOG" | tail -1 || true)
echo "$RESULT"
echo "$RESULT" | grep -qE ": 0 failed, 0 error\(s\) of [1-9][0-9]* tests" || { echo "Resumen ausente, vacío o fallido: $LOG"; exit 1; }
for MODULE in "${MODULES[@]}"; do
  grep -qE "odoo.tests.stats: ${MODULE}: [1-9][0-9]* tests" "$LOG" || { echo "Faltan pruebas del módulo $MODULE"; exit 1; }
done
