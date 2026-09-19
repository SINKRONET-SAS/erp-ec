"""Cifrado en reposo de secretos (certificado .p12 y su contraseña).

La clave maestra NUNCA se guarda en la base de datos: viene de la variable de entorno ERPEC_SECRET_KEY, de la
opción `erpec_secret_key` de odoo.conf o, si no existen, de un archivo `erpec_secret.key` que se genera una sola
vez en el directorio de datos del servidor (data_dir). Así un respaldo o volcado de la base no basta para leer los
certificados; hace falta además la clave del servidor. De la clave maestra se deriva (HKDF-SHA256) una clave por
contexto (registro y campo), de modo que un texto cifrado copiado a otro registro no se puede descifrar.
Fernet (AES-128-CBC + HMAC-SHA256) autentica: cualquier alteración se detecta.

Límite honesto: no protege contra alguien con acceso al servidor en ejecución (que puede leer la clave). Si se
pierde la clave maestra, los certificados guardados no se pueden recuperar y deben volver a cargarse."""
import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from odoo.tools import config

PREFIX = 'v1:'
KEY_FILE = 'erpec_secret.key'
MIN_KEY_LENGTH = 32


class SecretError(ValueError):
    pass


def _master_key():
    value = os.environ.get('ERPEC_SECRET_KEY') or config.get('erpec_secret_key')
    if value:
        if len(value) < MIN_KEY_LENGTH:
            raise SecretError('La clave maestra ERPEC_SECRET_KEY debe tener al menos %d caracteres.' % MIN_KEY_LENGTH)
        return value.encode('utf-8')
    directory = Path(config['data_dir'])
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / KEY_FILE
    if not path.exists():
        path.write_text(base64.urlsafe_b64encode(os.urandom(48)).decode('ascii'), encoding='ascii')
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return path.read_text(encoding='ascii').strip().encode('ascii')


def _fernet(context):
    derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=b'erpec-secret-store-v1',
                   info=context.encode('utf-8')).derive(_master_key())
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt(plain, context):
    """`plain`: bytes. `context`: texto que ata el secreto a su registro y campo (p. ej. 'cert:7:p12')."""
    return PREFIX + _fernet(context).encrypt(plain).decode('ascii')


def decrypt(token, context):
    if not token or not token.startswith(PREFIX):
        raise SecretError('El secreto guardado no tiene un formato válido.')
    try:
        return _fernet(context).decrypt(token[len(PREFIX):].encode('ascii'))
    except InvalidToken as error:
        raise SecretError('No se pudo descifrar el secreto: la clave del servidor cambió o el dato fue alterado. Vuelve a cargar el certificado.') from error


def p12_bytes(value):
    """Bytes reales de un .p12 (DER, empieza con 0x30). Las columnas binarias de Odoo guardan el valor en base64 (texto):
    si llega así se decodifica; si ya son los bytes del archivo se devuelven igual."""
    value = bytes(value)
    if value[:1] == b'\x30':
        return value
    return base64.b64decode(value, validate=True)
