"""Comprueba escritura de sesiones antes de arrancar o reinstalar la demo."""
import os,uuid
from pathlib import Path

def verify_session_access(directory):
    folder=Path(directory)/'data/sessions'
    if not folder.is_dir():
        raise RuntimeError('Falta la carpeta de sesiones de la demo; revisar su configuración.')
    probe=folder/('erpec-access-check-'+uuid.uuid4().hex)
    try:
        descriptor=os.open(probe,os.O_CREAT|os.O_EXCL|os.O_RDWR,0o600)
    except PermissionError as error:
        raise RuntimeError('El usuario de Windows no puede escribir sesiones. Ejecutar el servicio con el propietario de la carpeta; no cambiar la contraseña de Odoo ni ampliar permisos de la carpeta.') from error
    else:
        os.close(descriptor)
        probe.unlink()
