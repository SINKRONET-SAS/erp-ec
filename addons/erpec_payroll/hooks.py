"""Siembra automática de la versión de parámetros legales del año vigente al instalar el
módulo. Motivo: en nuevo_nomina esto se resuelve con una fila global compartida
(`tenant_id IS NULL`, con fallback automático por cliente) porque su multi-tenencia es una
sola base de datos con una columna de cliente. Aquí cada cliente es su propia base de datos
(modelo OP08), así que el equivalente correcto es sembrar la versión al instalar el módulo en
esa base, no duplicar el trabajo de captura manual en cada cliente nuevo.

Solo se siembra con parameters_ec2026.PARAMS (fuente oficial verificada, ver SOURCES) y solo
para el año 2026 exacto -- nunca con demo_parameters.PARAMS (explícitamente sintético) ni para
otro año sin una tabla verificada, para no presentar un valor no verificado como si fuera un
parámetro legal real.

Este módulo también configura el servidor SMTP saliente (para que el envío del rol de pago de
A3 deje de quedar solo encolado) reutilizando el MISMO patrón y los MISMOS nombres de variable
de entorno que ya usa sinkroniq-mobile en producción (EMAIL_HOST/EMAIL_PORT/EMAIL_USER/
EMAIL_PASS/EMAIL_FROM/EMAIL_SECURE, ver sinkroniq-mobile/backend/src/services/
mailTransportConfig.js) -- el titular puede reutilizar exactamente las mismas credenciales/
convención ya usadas allí en Render, sin inventar un esquema nuevo. Sin esas variables
presentes en el entorno del proceso (el caso normal en una máquina de desarrollo o en una
instancia recién aprovisionada sin secretos configurados en la plataforma de despliegue), no
se toca nada -- el correo sigue solo encolándose, nunca se envía de verdad."""
import os

from .parameters_ec2026 import PARAMS, SOURCES

SEED_YEAR = 2026
MAIL_SERVER_NAME = 'SINKRONET (EMAIL_* del entorno)'


def _bracket_commands(brackets):
    return [(0, 0, {
        'sequence': index, 'income_from': bracket['from'], 'income_to': bracket['to'] or 0,
        'open_ended': bracket['to'] is None, 'base_tax': bracket['base'], 'rate': bracket['rate'],
    }) for index, bracket in enumerate(brackets)]


def post_init_hook(env):
    """No referencia ningún diario: se probó (con un error real de llave foránea) que instalar
    erpec_payroll puede ocurrir antes de que el plan de cuentas de la empresa termine de
    cargarse o se reemplace por dependencias posteriores del mismo lote de instalación, y
    referenciar entonces un diario provisional rompe esa carga. Los parámetros legales (ley,
    no contabilidad) no necesitan un diario para existir; erpec.payroll.policy.journal_id ya no
    es required=True por este motivo, y action_activate() sigue exigiéndolo antes de calcular
    nómina real."""
    policy_model = env['erpec.payroll.policy']
    source_lines = '\n'.join('%s: %s' % (key, url) for key, url in SOURCES.items())
    for company in env['res.company'].search([]):
        if policy_model.search_count([('company_id', '=', company.id), ('year', '=', SEED_YEAR)]):
            continue
        policy_model.create({
            'name': 'NACIONAL-%d' % SEED_YEAR, 'company_id': company.id, 'year': SEED_YEAR,
            'minimum_salary': PARAMS['minimum_salary'], 'monthly_hours': PARAMS['monthly_hours'],
            'personal_rate': PARAMS['personal_rate'], 'employer_rate': PARAMS['employer_rate'],
            'employer_other_rate': PARAMS['employer_other_rate'], 'reserve_rate': PARAMS['reserve_rate'],
            'reserve_months': PARAMS['reserve_months'], 'thirteenth_rate': PARAMS['thirteenth_rate'],
            'fourteenth_rate': PARAMS['fourteenth_rate'], 'vacation_rate': PARAMS['vacation_rate'],
            'expense_limit': PARAMS['expense_limit'], 'rebate_rate': PARAMS['rebate_rate'],
            'overtime_50': PARAMS['overtime_50'], 'overtime_100': PARAMS['overtime_100'],
            'night_rate': PARAMS['night_rate'], 'tax_bracket_ids': _bracket_commands(PARAMS['tax_brackets']),
            'authorization': ('Parámetros nacionales de Ecuador %d sembrados automáticamente al instalar '
                'erpec_payroll, para no reconstruirlos desde cero en cada cliente nuevo. Revisar y activar '
                'antes de calcular nómina real; la migración productiva sigue pendiente de equivalencia '
                'integral y revisión laboral (docs/PLAN_HAIKY_ERPEC26.md).' % SEED_YEAR),
            'source_reference': 'Fuentes oficiales verificadas (parameters_ec2026.SOURCES):\n' + source_lines,
        })
    configure_mail_server_from_env(env)


def configure_mail_server_from_env(env):
    """Crea o actualiza el servidor SMTP saliente (ir.mail_server) a partir de EMAIL_HOST/
    EMAIL_PORT/EMAIL_USER/EMAIL_PASS/EMAIL_FROM/EMAIL_SECURE del entorno del proceso. Idempotente
    (busca por nombre fijo y actualiza en vez de duplicar). No registra la contraseña en ningún
    log. `from_filter` se deja vacío a propósito: un servidor sin from_filter queda disponible
    como respaldo universal para cualquier dirección de origen (ver ir_mail_server.py, selección
    de servidor), sin depender de que el correo del remitente coincida exactamente con
    EMAIL_FROM."""
    host = os.environ.get('EMAIL_HOST', '').strip()
    user = os.environ.get('EMAIL_USER', '').strip()
    password = os.environ.get('EMAIL_PASS', '').strip()
    if not host or not user or not password:
        return
    try:
        port = int(os.environ.get('EMAIL_PORT', '587') or '587')
    except ValueError:
        port = 587
    sender = os.environ.get('EMAIL_FROM', '').strip() or user
    secure = os.environ.get('EMAIL_SECURE', 'false').strip().lower() in ('true', '1', 'yes', 'si', 'on')
    values = {
        'name': MAIL_SERVER_NAME, 'smtp_host': host, 'smtp_port': port,
        'smtp_encryption': 'ssl' if secure else 'starttls', 'smtp_authentication': 'login',
        'smtp_user': user, 'smtp_pass': password, 'sequence': 1,
    }
    mail_server = env['ir.mail_server'].sudo()
    existing = mail_server.search([('name', '=', MAIL_SERVER_NAME)], limit=1)
    if existing:
        existing.write(values)
    else:
        mail_server.create(values)
    env['ir.config_parameter'].sudo().set_param('mail.default.from', sender)
