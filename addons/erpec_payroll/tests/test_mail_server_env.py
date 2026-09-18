"""Pruebas de la configuración del servidor SMTP saliente a partir de variables de entorno
(mismo patrón y mismos nombres que sinkroniq-mobile: EMAIL_HOST/EMAIL_PORT/EMAIL_USER/
EMAIL_PASS/EMAIL_FROM/EMAIL_SECURE). Sin esas variables, no debe crear ni tocar nada -- el
correo del rol de pago (A3) debe seguir solo encolándose, nunca enviarse de verdad en este
arnés ni en cualquier entorno sin esos secretos configurados."""
import os
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from ..hooks import MAIL_SERVER_NAME, configure_mail_server_from_env


@tagged('post_install', '-at_install')
class MailServerEnvCase(TransactionCase):
    def test_does_nothing_without_env_vars(self):
        with patch.dict(os.environ, {k: '' for k in ('EMAIL_HOST', 'EMAIL_USER', 'EMAIL_PASS')}):
            configure_mail_server_from_env(self.env)
        self.assertFalse(self.env['ir.mail_server'].search([('name', '=', MAIL_SERVER_NAME)]))

    def test_does_nothing_with_partial_env_vars(self):
        with patch.dict(os.environ, {'EMAIL_HOST': 'smtp.gmail.com', 'EMAIL_USER': 'a@example.com', 'EMAIL_PASS': ''}):
            configure_mail_server_from_env(self.env)
        self.assertFalse(self.env['ir.mail_server'].search([('name', '=', MAIL_SERVER_NAME)]))

    def test_creates_mail_server_with_starttls_by_default(self):
        env_vars = {'EMAIL_HOST': 'smtp.gmail.com', 'EMAIL_PORT': '587', 'EMAIL_USER': 'nomina@sinkronet.com.ec',
                    'EMAIL_PASS': 'ensayo-no-real', 'EMAIL_FROM': 'nomina@sinkronet.com.ec', 'EMAIL_SECURE': 'false'}
        with patch.dict(os.environ, env_vars):
            configure_mail_server_from_env(self.env)
        server = self.env['ir.mail_server'].search([('name', '=', MAIL_SERVER_NAME)])
        self.assertEqual(len(server), 1)
        self.assertEqual(server.smtp_host, 'smtp.gmail.com')
        self.assertEqual(server.smtp_port, 587)
        self.assertEqual(server.smtp_encryption, 'starttls')
        self.assertEqual(server.smtp_user, 'nomina@sinkronet.com.ec')
        self.assertEqual(server.smtp_pass, 'ensayo-no-real')
        self.assertFalse(server.from_filter)
        self.assertEqual(self.env['ir.config_parameter'].sudo().get_param('mail.default.from'), 'nomina@sinkronet.com.ec')

    def test_secure_true_maps_to_ssl_encryption(self):
        env_vars = {'EMAIL_HOST': 'smtp.gmail.com', 'EMAIL_PORT': '465', 'EMAIL_USER': 'a@example.com',
                    'EMAIL_PASS': 'ensayo-no-real', 'EMAIL_SECURE': 'true'}
        with patch.dict(os.environ, env_vars):
            configure_mail_server_from_env(self.env)
        server = self.env['ir.mail_server'].search([('name', '=', MAIL_SERVER_NAME)])
        self.assertEqual(server.smtp_encryption, 'ssl')

    def test_is_idempotent_updates_instead_of_duplicating(self):
        env_vars = {'EMAIL_HOST': 'smtp.gmail.com', 'EMAIL_USER': 'a@example.com', 'EMAIL_PASS': 'primero'}
        with patch.dict(os.environ, env_vars):
            configure_mail_server_from_env(self.env)
        env_vars2 = {'EMAIL_HOST': 'smtp.otro.com', 'EMAIL_USER': 'b@example.com', 'EMAIL_PASS': 'segundo'}
        with patch.dict(os.environ, env_vars2):
            configure_mail_server_from_env(self.env)
        servers = self.env['ir.mail_server'].search([('name', '=', MAIL_SERVER_NAME)])
        self.assertEqual(len(servers), 1)
        self.assertEqual(servers.smtp_host, 'smtp.otro.com')
        self.assertEqual(servers.smtp_user, 'b@example.com')
