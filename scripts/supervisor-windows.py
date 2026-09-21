"""Supervisor local: mantiene PostgreSQL y las instancias Odoo activas.

Cada 30 s comprueba PostgreSQL y el login HTTP de cada instancia; si una cae
(o no responde 3 veces seguidas) la reinicia. Solo gestiona los procesos que
él mismo identifica por su archivo de configuración; no toca otros.

Uso (desde la raíz del repositorio):
    python scripts/supervisor-windows.py            # bucle continuo
    python scripts/supervisor-windows.py --once     # revisa y repara una vez
    python scripts/supervisor-windows.py --status   # solo informa
Instalación al iniciar sesión: scripts/install-supervisor.ps1
"""
import argparse
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache' / 'windows'
PYTHON = ROOT / '.venv' / 'Scripts' / 'python.exe'
ODOO = ROOT / '.cache' / 'odoo-community' / 'odoo-bin'
PG = Path('C:/Program Files/PostgreSQL/17/bin')
INSTANCES = {'fundador': 8199, 'demo': 8369, 'a': 8169, 'b': 8170}
LOG = STATE / 'supervisor.log'
LOCK = STATE / 'supervisor.lock'
FAILURES = {}


def spawn(args, flags, **options):
    """Lanza un proceso que sobrevive al supervisor: Task Scheduler cierra el árbol de la tarea al detenerla
    (p. ej. al reiniciar el supervisor) y sin esto caerían PostgreSQL y las instancias. Si el trabajo no permite
    salirse de él, se reintenta sin esa opción."""
    try:
        return subprocess.Popen(args, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **options)
    except OSError:
        return subprocess.Popen(args, creationflags=flags, **options)


def log(message):
    line = time.strftime('%Y-%m-%d %H:%M:%S ') + message
    print(line, flush=True)
    with LOG.open('a', encoding='utf-8') as handle:
        handle.write(line + '\n')


def postgres_up():
    return subprocess.run([str(PG / 'pg_ctl.exe'), '-D', str(STATE / 'pgdata'), 'status'], capture_output=True,
                          creationflags=subprocess.CREATE_NO_WINDOW).returncode == 0


def ensure_postgres(repair):
    if postgres_up():
        return True
    if not repair:
        return False
    log('PostgreSQL detenido; iniciando')
    # DETACHED_PROCESS: el servidor no hereda ninguna consola (si no, aparece una ventana `pg_ctl.exe` que, al
    # cerrarla, detiene PostgreSQL). Sin tuberías heredadas, para que pg_ctl no espere al servidor.
    process = spawn([str(PG / 'pg_ctl.exe'), '-D', str(STATE / 'pgdata'), '-l', str(STATE / 'postgres.log'), '-w', 'start'],
                    subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    return process.wait() == 0


def instance_processes(name):
    """Procesos odoo-bin cuyo -c apunta al odoo.conf de esta instancia."""
    suffix = '\\windows\\%s\\odoo.conf' % name
    found = []
    for process in psutil.process_iter(['pid', 'cmdline']):
        arguments = [str(a).replace('/', '\\').lower() for a in (process.info['cmdline'] or [])]
        if any(a.endswith('odoo-bin') for a in arguments) and any(a.endswith(suffix) for a in arguments):
            found.append(process)
    return found


def healthy(port):
    try:
        with urllib.request.urlopen('http://127.0.0.1:%d/web/login' % port, timeout=20) as response:
            return response.status == 200
    except Exception:  # noqa: BLE001 - cualquier fallo de conexión cuenta como no saludable
        return False


def stop(name):
    for process in instance_processes(name):
        try:
            process.kill()
        except psutil.Error:
            pass
    time.sleep(3)


def start(name):
    process = spawn([str(PYTHON), str(ODOO), '-c', str(STATE / name / 'odoo.conf')], subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
                    cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (STATE / name / 'pid').write_text(str(process.pid), encoding='ascii')
    log('instancia %s iniciada (pid %d)' % (name, process.pid))


def check(repair):
    report = {}
    report['postgres'] = ensure_postgres(repair)
    for name, port in INSTANCES.items():
        if not (STATE / name / 'odoo.conf').exists():
            continue
        if not report['postgres']:
            report[name] = 'sin base de datos'
            continue
        if healthy(port):
            FAILURES[name] = 0
            report[name] = 'ok'
            continue
        running = bool(instance_processes(name))
        FAILURES[name] = FAILURES.get(name, 0) + 1
        report[name] = 'caida' if not running else 'sin respuesta (%d)' % FAILURES[name]
        if repair and (not running or FAILURES[name] >= 3):
            log('instancia %s: %s; reiniciando' % (name, report[name]))
            stop(name)
            start(name)
            FAILURES[name] = 0
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--interval', type=int, default=30)
    args = parser.parse_args()
    if args.status:
        print(check(repair=False))
        return 0
    if args.once:
        print(check(repair=True))
        return 0
    # Una sola copia del supervisor a la vez.
    if LOCK.exists():
        try:
            if psutil.pid_exists(int(LOCK.read_text())) and 'supervisor-windows' in ' '.join(psutil.Process(int(LOCK.read_text())).cmdline()):
                print('El supervisor ya está en ejecución')
                return 1
        except (ValueError, psutil.Error):
            pass
    LOCK.write_text(str(psutil.Process().pid), encoding='ascii')
    log('supervisor iniciado')
    try:
        while True:
            check(repair=True)
            time.sleep(args.interval)
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == '__main__':
    sys.exit(main())
