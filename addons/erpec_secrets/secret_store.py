"""Cifrado en reposo de secretos (certificado .p12, contraseñas y tokens) con rotación de clave.

La clave maestra NUNCA se guarda en la base de datos. Clave VIGENTE, en este orden: variable de entorno
ERPEC_SECRET_KEY, opción `erpec_secret_key` de odoo.conf o archivo `erpec_secret.key` (se genera una sola vez en el
directorio de datos, data_dir). Claves ANTERIORES (solo para descifrar durante una rotación): ERPEC_SECRET_KEY_PREVIOUS
(separadas por coma), opción `erpec_secret_key_previous` o el archivo `erpec_secret.previous` (una por línea).

Formato del texto cifrado: `v2:<id de clave>:<token Fernet>`; el id (8 hex de SHA-256 de la clave maestra) permite saber con
qué clave se cifró sin descifrar. Se leen también los `v1:` antiguos (sin id: se prueban todas las claves conocidas).
De cada clave maestra se deriva (HKDF-SHA256) una clave por contexto (registro y campo): un texto cifrado copiado a otro
registro no se descifra. Fernet (AES-128-CBC + HMAC-SHA256) autentica: cualquier alteración se detecta.

Rotación: (1) definir una clave nueva como vigente y conservar la anterior como PREVIOUS (o `rotate_key_file()` lo hace
con el archivo), (2) re-cifrar todo con la vigente (asistente Ajustes > Técnico > Rotación de claves de secretos o
scripts/rotate-secret-key.py), (3) comprobar que no queda nada con la clave anterior y recién entonces retirarla.

Límite honesto: no protege contra alguien con acceso al servidor en ejecución. Si se pierden TODAS las claves con las que
se cifró un secreto, no se puede recuperar y hay que volver a cargarlo."""
import base64
import hashlib
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from odoo.tools import config

LEGACY_PREFIX = 'v1:'
PREFIX = 'v2:'
KEY_FILE = 'erpec_secret.key'
PREVIOUS_FILE = 'erpec_secret.previous'
MIN_KEY_LENGTH = 32

# Campos cifrados registrados por los módulos: (modelo, campo) -> función(registro) que da el contexto de cifrado.
REGISTRY = {}


class SecretError(ValueError):
    pass


def register(model, field, context):
    """Declara un campo cifrado para que la rotación pueda re-cifrarlo. `context(registro)` devuelve el contexto."""
    REGISTRY[(model, field)] = context


def generate_key():
    return base64.urlsafe_b64encode(os.urandom(48)).decode('ascii')


def _directory():
    directory = Path(config['data_dir'])
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _validated(value):
    value = (value or '').strip()
    if len(value) < MIN_KEY_LENGTH:
        raise SecretError('Una clave maestra debe tener al menos %d caracteres.' % MIN_KEY_LENGTH)
    return value.encode('utf-8')


def key_source():
    if os.environ.get('ERPEC_SECRET_KEY'):
        return 'variable de entorno ERPEC_SECRET_KEY'
    if config.get('erpec_secret_key'):
        return 'odoo.conf (erpec_secret_key)'
    return 'archivo %s' % KEY_FILE


def _master_key():
    """Clave maestra vigente (bytes)."""
    value = os.environ.get('ERPEC_SECRET_KEY') or config.get('erpec_secret_key')
    if value:
        return _validated(value)
    path = _directory() / KEY_FILE
    if not path.exists():
        path.write_text(generate_key(), encoding='ascii')
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return path.read_text(encoding='ascii').strip().encode('ascii')


def _previous_keys():
    values = []
    for raw in (os.environ.get('ERPEC_SECRET_KEY_PREVIOUS'), config.get('erpec_secret_key_previous')):
        values += [item for item in (raw or '').split(',') if item.strip()]
    path = _directory() / PREVIOUS_FILE
    if path.exists():
        values += [line for line in path.read_text(encoding='ascii').splitlines() if line.strip()]
    return [_validated(item) for item in values]


def key_id(master):
    return hashlib.sha256(master).hexdigest()[:8]


def current_key_id():
    return key_id(_master_key())


def known_keys():
    """{id: clave} de la vigente y las anteriores."""
    keys = {}
    for master in [_master_key()] + _previous_keys():
        keys.setdefault(key_id(master), master)
    return keys


def _fernet(context, master=None):
    derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=b'erpec-secret-store-v1',
                   info=context.encode('utf-8')).derive(master or _master_key())
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt(plain, context):
    """`plain`: bytes. `context`: texto que ata el secreto a su registro y campo (p. ej. 'cert:7:p12')."""
    master = _master_key()
    return '%s%s:%s' % (PREFIX, key_id(master), _fernet(context, master).encrypt(plain).decode('ascii'))


def token_key_id(token):
    """Id de la clave con la que se cifró ('v1' para el formato antiguo sin id), o None si no es un secreto válido."""
    if token and token.startswith(PREFIX):
        return token[len(PREFIX):].split(':', 1)[0]
    if token and token.startswith(LEGACY_PREFIX):
        return 'v1'
    return None


def decrypt(token, context):
    kid = token_key_id(token)
    if not kid:
        raise SecretError('El secreto guardado no tiene un formato válido.')
    keys = known_keys()
    if kid == 'v1':
        candidates, body = list(keys.values()), token[len(LEGACY_PREFIX):]
    else:
        if kid not in keys:
            raise SecretError('El secreto se cifró con la clave %s, que este servidor no tiene. Configúrala como ERPEC_SECRET_KEY_PREVIOUS '
                              'o vuelve a cargar el secreto.' % kid)
        candidates, body = [keys[kid]], token[len(PREFIX) + len(kid) + 1:]
    for master in candidates:
        try:
            return _fernet(context, master).decrypt(body.encode('ascii'))
        except InvalidToken:
            continue
    raise SecretError('No se pudo descifrar el secreto: la clave del servidor cambió o el dato fue alterado. Vuelve a cargar el certificado.')


def rotate_key_file():
    """Genera una clave nueva en el archivo y conserva la anterior en erpec_secret.previous. Solo si la clave vigente vive en el
    archivo (con variable de entorno u odoo.conf la rotación la hace el operador). Después hay que re-cifrar todo."""
    if os.environ.get('ERPEC_SECRET_KEY') or config.get('erpec_secret_key'):
        raise SecretError('La clave vigente se define en %s: genera una nueva, pasa la actual a ERPEC_SECRET_KEY_PREVIOUS, reinicia '
                          'y re-cifra desde el asistente.' % key_source())
    old = _master_key().decode('ascii')
    directory = _directory()
    previous = directory / PREVIOUS_FILE
    with open(previous, 'a', encoding='ascii') as handle:
        handle.write(old + '\n')
    try:
        os.chmod(previous, 0o600)
    except OSError:
        pass
    (directory / KEY_FILE).write_text(generate_key(), encoding='ascii')
    return current_key_id()


def p12_bytes(value):
    """Bytes reales de un .p12 (DER, empieza con 0x30). Las columnas binarias de Odoo guardan el valor en base64 (texto):
    si llega así se decodifica; si ya son los bytes del archivo se devuelven igual."""
    value = bytes(value)
    if value[:1] == b'\x30':
        return value
    return base64.b64decode(value, validate=True)
