"""Respalda la demo detenida y prueba fabricación en una copia sin conexiones externas."""
from pathlib import Path
import configparser, datetime, hashlib, json, os, shutil, subprocess, sys, uuid
import psutil, psycopg2
from psycopg2 import sql
ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache/windows'
DEMO = STATE / 'demo'
SOURCE = ROOT / '.cache/odoo-community'
PG = Path('C:/Program Files/PostgreSQL/17/bin')

def write(path, value):
    text = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    assert text.encode('utf-8').decode('utf-8') == text
    path.write_text(text, encoding='utf-8', newline='\n')

def hashes():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'addons/erpec_manufacturing').rglob('*') if p.is_file() and p.suffix in ('.py', '.xml')}

def main():
    config = configparser.ConfigParser(interpolation=None)
    config.read(DEMO/'odoo.conf', encoding='utf-8')
    options = config['options']
    assert options['db_name'] == 'erpec_demo' and options['http_port'] == '8369'
    name = 'ec_manufacturing_' + uuid.uuid4().hex[:10]
    backup = STATE/'manufacturing-tests'/name
    backup.mkdir(parents=True)
    environment = {**os.environ, 'PGPASSWORD': options['db_password']}
    pid = int((DEMO/'pid').read_text())
    if psutil.pid_exists(pid):
        process = psutil.Process(pid)
        assert str(DEMO/'odoo.conf') in process.cmdline(), 'El proceso no corresponde a la demo'
        process.terminate()
        process.wait(30)
    else:
        print('La demo ya está detenida; se respalda antes de iniciarla', flush=True)
    try:
        subprocess.run([str(PG/'pg_dump.exe'), '-h', options['db_host'], '-p', options['db_port'], '-U', options['db_user'], '-d', options['db_name'], '-Fc', '-f', str(backup/'database.dump')], env=environment, check=True)
        shutil.copytree(DEMO/'data/filestore'/options['db_name'], backup/'filestore')
        shutil.copytree(DEMO/'addons', backup/'addons', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    finally:
        running = subprocess.Popen([sys.executable, str(SOURCE/'odoo-bin'), '-c', str(DEMO/'odoo.conf')], cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW)
        (DEMO/'pid').write_text(str(running.pid), encoding='utf-8')
    private = json.loads((STATE/'credentials.json').read_text(encoding='utf-8'))
    connection = psycopg2.connect(host='127.0.0.1', port=55487, user='postgres', password=private['postgres'], dbname='postgres')
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL('CREATE DATABASE {} OWNER {} TEMPLATE template0').format(sql.Identifier(name), sql.Identifier(options['db_user'])))
            cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(name)))
    finally:
        connection.close()
    subprocess.run([str(PG/'pg_restore.exe'), '-h', options['db_host'], '-p', options['db_port'], '-U', options['db_user'], '-d', name, '--exit-on-error', str(backup/'database.dump')], env=environment, check=True)
    shutil.copytree(backup/'filestore', backup/'data/filestore'/name)
    options.update({'db_name': name, 'dbfilter': '^'+name+'$', 'data_dir': str(backup/'data'), 'addons_path': ','.join(map(str, [SOURCE/'addons', SOURCE/'odoo/addons', ROOT/'addons'])), 'logfile': str(backup/'tests.log'), 'max_cron_threads': '0', 'http_port': '8469'})
    import io
    stream = io.StringIO()
    config.write(stream)
    text = stream.getvalue()
    assert text.encode('utf-8').decode('utf-8') == text
    (backup/'odoo.conf').write_text(text, encoding='utf-8', newline='\n')
    result = subprocess.run([sys.executable, str(SOURCE/'odoo-bin'), '-c', str(backup/'odoo.conf'), '-i', 'erpec_manufacturing', '--test-enable', '--test-tags', '/erpec_manufacturing', '--stop-after-init', '--no-http'])
    report = {'database': name, 'exitCode': result.returncode, 'backup': str(backup), 'testedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'scope': 'Copia aislada de demo sintética; sin emisión, pagos ni nube', 'fileHashes': hashes()}
    write(STATE/'manufacturing-test-result.json', report)
    print(json.dumps(report), flush=True)
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()
