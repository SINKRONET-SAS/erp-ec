"""DI26-B.4, DI26-E.5 y DI26-E.6 sobre la demo local (nunca sobre fundador ni los pilotos).

1. Marca como empresa de ensayo la empresa ficticia de la demo (DI26-12) y le quita el RUC real de SINKRONET: pasa a un
   RUC de ensayo visiblemente sintético (dígito verificador válido, como exige el DIMM). Sus anexos salen con el prefijo
   ENSAYO-NO-PRESENTAR, su certificado autofirmado de ensayo se regenera para el RUC nuevo y el ATS se reconstruye.
2. Retira de la demo las aplicaciones ajenas al producto aprovisionado (DI26-16) sin tocar nada de lo que necesita un
   módulo erpec_*: se calcula el cierre de dependencias descendentes y se aborta si alcanzaría a un módulo propio.
3. Desactiva el usuario de ensayo que seguía activo (P3).

Respalda la base con pg_dump antes de cambiar nada. Requiere que la demo ya tenga los módulos erpec_* actualizados
(scripts/update-instance.py demo).

Uso:
    python scripts/align-demo-di26.py [--dry-run]
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.cache' / 'windows'
PYTHON = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
ODOO = ROOT / '.cache' / 'odoo-community' / 'odoo-bin'
PG_DUMP = Path('C:/Program Files/PostgreSQL/17/bin/pg_dump.exe')
INSTANCE = 'demo'
REAL_VAT = '1793235327001'  # SINKRONET S.A.S. (fundador); nunca en una empresa de ensayo
TEST_COMPANY_VAT = '1799999990001'  # sintético: 17 + 9 + 9999999 + dígito verificador + 001
TEST_COMPANY_NAME = 'Empresa autoservicio ensayo'
TEST_USERS = ['selfservice_test_2']
# Aplicaciones raíz ajenas al producto; Odoo desinstala también lo que depende de ellas.
FOREIGN_ROOTS = ['crm', 'fleet', 'im_livechat', 'website_blog', 'website_forum', 'mass_mailing', 'gamification', 'project']

SHELL = r'''
import json
dry = %(dry)s
Module = env['ir.module.module']
roots = Module.search([('name', 'in', %(roots)r), ('state', '=', 'installed')])
removed = roots | roots.downstream_dependencies()
own = removed.filtered(lambda m: m.name.startswith('erpec_'))
assert not own, 'Retirar %%s alcanzaría módulos propios: %%s' %% (roots.mapped('name'), own.mapped('name'))
import base64, secrets
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, pkcs12
from cryptography.x509.oid import NameOID
companies = env['res.company'].with_context(active_test=False).search([('name', '=', %(name)r)])
assert len(companies) == 1, 'Se esperaba una sola empresa de ensayo llamada %%s' %% %(name)r
fundador_like = companies.filtered(lambda c: 'ensayo' not in (c.name or '').lower())
company = companies
Certificate = env['erpec.fiscal.certificate'].sudo()
certificate = Certificate.search([('company_id', '=', company.id)], limit=1)
cert_ok = bool(certificate and %(vat)r in (certificate.subject_summary or ''))
reports = env['erpec.ats.report'].sudo().search([('company_id', '=', company.id)])
users = env['res.users'].with_context(active_test=False).search([('login', 'in', %(users)r), ('active', '=', True)])
result = {'retirar': sorted(removed.mapped('name')), 'empresasEnsayo': companies.mapped('name'), 'rucAnterior': company.vat, 'rucNuevo': %(vat)r,
          'certificadoRegenerado': not cert_ok, 'atsReconstruidos': len(reports),
          'empresasSinPalabraEnsayo': fundador_like.mapped('name'), 'usuariosDesactivados': users.mapped('login')}
if not dry:
    companies.write({'ec_test_company': True, 'vat': %(vat)r})
    assert company.partner_id.vat == %(vat)r and not env['res.partner'].with_context(active_test=False).search_count(
        [('vat', '=', %(real)r), ('id', 'child_of', company.partner_id.id)])
    if not cert_ok:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, company.name), x509.NameAttribute(NameOID.SERIAL_NUMBER, %(vat)r)])
        now = datetime.utcnow()
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=365))
                .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=True, key_encipherment=False, data_encipherment=False,
                                             key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
                .sign(key, hashes.SHA256()))
        password = secrets.token_urlsafe(24)
        p12 = pkcs12.serialize_key_and_certificates(b'ensayo', key, cert, None, BestAvailableEncryption(password.encode()))
        values = {'p12_file': base64.b64encode(p12), 'p12_password': password}
        if certificate:
            certificate.write(dict(values, verify_attempts=0, verify_window_start=False))
        else:
            certificate = Certificate.create(dict(values, company_id=company.id))
        certificate.with_company(company).action_verify()
        assert certificate.verified, certificate.notice
        certificate.with_company(company).action_test_signature()
        assert certificate.signature_tested, certificate.notice
    for report in reports:
        report.with_company(company).action_reset()
        report.with_company(company).action_build()
    result['certificado'] = certificate.subject_summary
    result['ats'] = reports.mapped('xml_filename')
    users.write({'active': False})
    env.cr.commit()
    if roots:
        roots.button_immediate_uninstall()
    env.cr.commit()
print('RESULTADO ' + json.dumps(result, ensure_ascii=False))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    conf = STATE / INSTANCE / 'odoo.conf'
    password = json.loads((STATE / 'credentials.json').read_text(encoding='utf-8'))['postgres']
    backup = None
    if not args.dry_run:
        backup = STATE / 'backups' / ('align-demo-di26-%s' % time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
        backup.mkdir(parents=True, exist_ok=False)
        subprocess.run([str(PG_DUMP), '-h', '127.0.0.1', '-p', '55487', '-U', 'postgres', '-Fc', '-f', str(backup / 'erpec_demo.dump'),
                        'erpec_demo'], env={**os.environ, 'PGPASSWORD': password}, check=True)
    code = SHELL % {'dry': args.dry_run, 'roots': FOREIGN_ROOTS, 'vat': TEST_COMPANY_VAT, 'real': REAL_VAT, 'name': TEST_COMPANY_NAME, 'users': TEST_USERS}
    result = subprocess.run([str(PYTHON), str(ODOO), 'shell', '-c', str(conf), '--no-http', '--log-level=warn'], input=code,
                            capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(ROOT),
                            env={**os.environ, 'PYTHONUTF8': '1'})
    line = next((l for l in result.stdout.splitlines() if l.startswith('RESULTADO ')), None)
    if result.returncode != 0 or not line:
        print(result.stdout[-2000:], result.stderr[-3000:], file=sys.stderr)
        return 1
    outcome = json.loads(line[len('RESULTADO '):])
    outcome['respaldo'] = backup and str(backup.relative_to(ROOT)).replace('\\', '/')
    outcome['simulacion'] = args.dry_run
    print(json.dumps(outcome, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
