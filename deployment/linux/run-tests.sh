#!/usr/bin/env bash
# Suite integrada dentro de la imagen Linux (mismo Python y lock que producción).
# Uso: deployment/linux/run-tests.sh [modulo ...]   (por defecto, todos los erpec_*)
# Requiere Docker. Sale con código distinto de 0 si hay fallos o errores.
set -euo pipefail
cd "$(dirname "$0")/../.."
export MSYS_NO_PATHCONV=1
IMAGE="${ERPEC_TEST_IMAGE:-erpec-lock-test:local}"
NET="erpec-net-$$"
PG="erpec-pg-$$"
if [ "$#" -gt 0 ]; then MODULES=("$@"); else MODULES=($(ls addons | grep '^erpec_')); fi
INSTALL=$(IFS=,; echo "${MODULES[*]}")
TAGS=$(printf '/%s,' "${MODULES[@]}"); TAGS="${TAGS%,}"
ADDONS_DIR="$(pwd)/addons"; command -v cygpath >/dev/null && ADDONS_DIR="$(cygpath -m "$ADDONS_DIR")"
[ -n "${ERPEC_SKIP_BUILD:-}" ] || docker build -f deployment/linux/Dockerfile -t "$IMAGE" .
cleanup() { docker rm -f "$PG" >/dev/null 2>&1 || true; docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker network create "$NET" >/dev/null
docker run -d --name "$PG" --network "$NET" -e POSTGRES_PASSWORD=test -e POSTGRES_USER=odoo postgres:17 >/dev/null
for _ in $(seq 1 30); do docker exec "$PG" pg_isready -U odoo >/dev/null 2>&1 && break; sleep 2; done
LOG="$(mktemp)"
docker run --rm --network "$NET" --entrypoint python -v "$ADDONS_DIR:/extra:ro" "$IMAGE" \
  /opt/odoo/odoo-bin --db_host "$PG" --db_user odoo --db_password test -d linux_test \
  --addons-path /opt/odoo/addons,/opt/odoo/odoo/addons,/extra --without-demo=all \
  -i "$INSTALL" --test-tags "$TAGS" --stop-after-init --no-http 2>&1 | tee "$LOG" | grep -E "odoo.tests.result|Traceback" || true
RESULT=$(grep -E "odoo.tests.result" "$LOG" | tail -1 || true)
echo "$RESULT"
echo "$RESULT" | grep -qE ": 0 failed, 0 error\(s\)" || { echo "Fallos en la suite Linux (registro: $LOG)"; exit 1; }
