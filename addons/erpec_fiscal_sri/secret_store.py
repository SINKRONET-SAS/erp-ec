"""Compatibilidad: el almacén de secretos vive ahora en el módulo compartido erpec_secrets."""
from odoo.addons.erpec_secrets.secret_store import *  # noqa: F401,F403
from odoo.addons.erpec_secrets.secret_store import _fernet, _master_key  # noqa: F401
