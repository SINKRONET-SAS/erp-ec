"""Control de visitas/asistencia de vendedores por zona (geocerca), inspirado en el patrón
RouteSite/RouteDay/RouteStop/RouteVisitMark/RouteException confirmado de forma independiente
en sinkroniq-mobile (backend/prisma/schema.prisma) y en nuevo_nomina (routeVisitService.js) --
ver docs/PLAN_HAIKY_NOMINA_VISITAS.md, fase B1-B2. Adaptado a modelos Odoo (hr.employee/
res.partner en vez de tablas propias de vendedor/cliente); sin app móvil nativa en este
alcance -- se opera desde la interfaz web. Una marca fuera de geocerca o con precisión GPS
baja se guarda igual (no se bloquea de forma dura) pero genera una excepción revisable --
mismo comportamiento que la referencia."""
import math

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_INTERNAL = object()
EARTH_RADIUS_M = 6371000.0


def haversine_meters(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RouteSite(models.Model):
    _name = 'erpec.route.site'
    _description = 'Sitio de visita con geocerca'
    _check_company_auto = True

    name = fields.Char(required=True, string='Nombre')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, string='Empresa')
    partner_id = fields.Many2one('res.partner', string='Cliente/contacto', check_company=True)
    latitude = fields.Float('Latitud', digits=(10, 7), required=True)
    longitude = fields.Float('Longitud', digits=(10, 7), required=True)
    radius_meters = fields.Float('Radio de geocerca (m)', default=150.0, required=True)
    min_accuracy_meters = fields.Float('Precisión GPS mínima exigida (m)', default=80.0, required=True)
    active = fields.Boolean(default=True, string='Activo')

    @api.constrains('latitude', 'longitude')
    def _check_coordinates(self):
        for site in self:
            if not -90 <= site.latitude <= 90 or not -180 <= site.longitude <= 180:
                raise ValidationError('Latitud/longitud fuera de rango.')

    @api.constrains('radius_meters', 'min_accuracy_meters')
    def _check_positive(self):
        for site in self:
            if site.radius_meters <= 0 or site.min_accuracy_meters <= 0:
                raise ValidationError('El radio de geocerca y la precisión mínima deben ser positivos.')


class RouteDay(models.Model):
    _name = 'erpec.route.day'
    _description = 'Día de ruta planificado para un vendedor'
    _check_company_auto = True
    _order = 'date desc'

    employee_id = fields.Many2one('hr.employee', required=True, check_company=True, string='Vendedor')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, string='Empresa')
    date = fields.Date(required=True, default=fields.Date.context_today, string='Fecha')
    state = fields.Selection([('planned', 'Planificado'), ('in_progress', 'En progreso'),
                               ('completed', 'Completado'), ('cancelled', 'Cancelado')],
                              default='planned', required=True, readonly=True, string='Estado')
    allow_unplanned = fields.Boolean('Permite paradas no planificadas', default=True)
    stop_ids = fields.One2many('erpec.route.stop', 'route_day_id', string='Paradas')
    planned_stop_count = fields.Integer(compute='_compute_metrics', string='Paradas planificadas')
    completed_stop_count = fields.Integer(compute='_compute_metrics', string='Paradas completadas')
    completion_rate = fields.Float('Cumplimiento (%)', compute='_compute_metrics')
    within_geofence_rate = fields.Float('Dentro de geocerca (%)', compute='_compute_metrics')
    _sql_constraints = [('employee_date_unique', 'unique(employee_id, date)',
                          'Ya existe un día de ruta para este vendedor en esta fecha.')]

    @api.depends('stop_ids.state', 'stop_ids.planned', 'stop_ids.checkin_mark_id.within_geofence',
                 'stop_ids.checkout_mark_id.within_geofence')
    def _compute_metrics(self):
        for day in self:
            planned = day.stop_ids.filtered('planned')
            completed = planned.filtered(lambda s: s.state == 'completed')
            day.planned_stop_count = len(planned)
            day.completed_stop_count = len(completed)
            day.completion_rate = (len(completed) / len(planned) * 100) if planned else 0.0
            within = completed.filtered(lambda s: s.checkin_mark_id.within_geofence and s.checkout_mark_id.within_geofence)
            day.within_geofence_rate = (len(within) / len(completed) * 100) if completed else 0.0

    def action_start(self):
        self.write({'state': 'in_progress'})
        return True

    def action_complete(self):
        for day in self:
            if any(stop.state == 'pending' for stop in day.stop_ids.filtered('planned')):
                raise UserError('Completa u omite todas las paradas planificadas antes de cerrar el día.')
        self.write({'state': 'completed'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True

    def action_add_unplanned_stop(self, site_id, reason):
        self.ensure_one()
        if not self.allow_unplanned:
            raise UserError('Este día de ruta no permite paradas no planificadas.')
        if not reason or not reason.strip():
            raise UserError('Indica el motivo de la parada no planificada.')
        next_sequence = (max(self.stop_ids.mapped('sequence')) + 10) if self.stop_ids else 10
        stop = self.env['erpec.route.stop'].with_context(_erpec_routes_token=_INTERNAL).create({
            'route_day_id': self.id, 'site_id': site_id, 'planned': False, 'sequence': next_sequence,
        })
        self.env['erpec.route.exception'].with_context(_erpec_routes_token=_INTERNAL).create({
            'stop_id': stop.id, 'exception_type': 'unplanned_visit', 'reason': reason,
        })
        return stop.id


class RouteStop(models.Model):
    _name = 'erpec.route.stop'
    _description = 'Parada planificada u ocasional dentro de un día de ruta'
    _order = 'route_day_id, sequence'
    _check_company_auto = True

    route_day_id = fields.Many2one('erpec.route.day', required=True, ondelete='cascade', string='Día de ruta')
    company_id = fields.Many2one(related='route_day_id.company_id', store=True, string='Empresa')
    site_id = fields.Many2one('erpec.route.site', required=True, check_company=True, string='Sitio')
    sequence = fields.Integer(default=10, string='Secuencia')
    planned = fields.Boolean(default=True, string='Planificado')
    state = fields.Selection([('pending', 'Pendiente'), ('started', 'Iniciada'),
                               ('completed', 'Completada'), ('omitted', 'Omitida')],
                              default='pending', required=True, readonly=True, string='Estado')
    omission_reason = fields.Text(string='Motivo de la omisión')
    checkin_mark_id = fields.Many2one('erpec.route.visit.mark', readonly=True, copy=False, string='Marca de llegada')
    checkout_mark_id = fields.Many2one('erpec.route.visit.mark', readonly=True, copy=False, string='Marca de salida')

    def action_checkin(self, latitude, longitude, accuracy_meters):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError('Esta parada ya fue iniciada, completada u omitida.')
        mark = self.env['erpec.route.visit.mark'].with_context(_erpec_routes_token=_INTERNAL).create({
            'stop_id': self.id, 'mark_type': 'checkin', 'latitude': latitude, 'longitude': longitude,
            'accuracy_meters': accuracy_meters,
        })
        self.with_context(_erpec_routes_token=_INTERNAL).write({'state': 'started', 'checkin_mark_id': mark.id})
        return mark.id

    def action_checkout(self, latitude, longitude, accuracy_meters):
        self.ensure_one()
        if self.state != 'started':
            raise UserError('Primero registra el ingreso (check-in) de esta parada.')
        mark = self.env['erpec.route.visit.mark'].with_context(_erpec_routes_token=_INTERNAL).create({
            'stop_id': self.id, 'mark_type': 'checkout', 'latitude': latitude, 'longitude': longitude,
            'accuracy_meters': accuracy_meters,
        })
        self.with_context(_erpec_routes_token=_INTERNAL).write({'state': 'completed', 'checkout_mark_id': mark.id})
        return mark.id

    def action_omit(self, reason):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError('Solo se omite una parada que aún no se ha iniciado.')
        if not reason or not reason.strip():
            raise UserError('Indica el motivo de la omisión.')
        self.with_context(_erpec_routes_token=_INTERNAL).write({'state': 'omitted', 'omission_reason': reason})
        self.env['erpec.route.exception'].with_context(_erpec_routes_token=_INTERNAL).create({
            'stop_id': self.id, 'exception_type': 'omitted_visit', 'reason': reason,
        })
        return True

    def write(self, values):
        if self.env.context.get('_erpec_routes_token') is not _INTERNAL and set(values) & {
                'state', 'checkin_mark_id', 'checkout_mark_id'}:
            raise ValidationError(
                'El estado y las marcas de visita solo se generan mediante las acciones de check-in/check-out/omisión.')
        return super().write(values)


class RouteVisitMark(models.Model):
    _name = 'erpec.route.visit.mark'
    _description = 'Marca de check-in/check-out con geolocalización'
    _order = 'timestamp'

    stop_id = fields.Many2one('erpec.route.stop', required=True, ondelete='cascade', string='Parada')
    company_id = fields.Many2one(related='stop_id.company_id', store=True, string='Empresa')
    mark_type = fields.Selection([('checkin', 'Check-in'), ('checkout', 'Check-out')], required=True, string='Tipo de marca')
    timestamp = fields.Datetime(default=fields.Datetime.now, required=True, string='Fecha y hora')
    latitude = fields.Float(digits=(10, 7), required=True, string='Latitud')
    longitude = fields.Float(digits=(10, 7), required=True, string='Longitud')
    accuracy_meters = fields.Float(required=True, string='Precisión (metros)')
    distance_meters = fields.Float(compute='_compute_geofence', store=True, string='Distancia (metros)')
    within_geofence = fields.Boolean(compute='_compute_geofence', store=True, string='Dentro del perímetro')
    low_accuracy = fields.Boolean(compute='_compute_geofence', store=True, string='Precisión baja')

    @api.depends('latitude', 'longitude', 'accuracy_meters', 'stop_id.site_id.latitude',
                 'stop_id.site_id.longitude', 'stop_id.site_id.radius_meters',
                 'stop_id.site_id.min_accuracy_meters')
    def _compute_geofence(self):
        for mark in self:
            site = mark.stop_id.site_id
            if not site:
                mark.distance_meters = 0.0
                mark.within_geofence = False
                mark.low_accuracy = False
                continue
            mark.distance_meters = haversine_meters(mark.latitude, mark.longitude, site.latitude, site.longitude)
            mark.within_geofence = mark.distance_meters <= site.radius_meters
            mark.low_accuracy = mark.accuracy_meters > site.min_accuracy_meters

    @api.model_create_multi
    def create(self, values_list):
        if self.env.context.get('_erpec_routes_token') is not _INTERNAL:
            raise ValidationError('Las marcas de visita solo se generan mediante las acciones de check-in/check-out.')
        records = super().create(values_list)
        for mark in records:
            if not mark.within_geofence:
                self.env['erpec.route.exception'].with_context(_erpec_routes_token=_INTERNAL).create({
                    'mark_id': mark.id, 'exception_type': 'geofence_violation',
                    'reason': 'Marca a %.0f m del sitio (radio permitido %.0f m).' % (
                        mark.distance_meters, mark.stop_id.site_id.radius_meters),
                })
            elif mark.low_accuracy:
                self.env['erpec.route.exception'].with_context(_erpec_routes_token=_INTERNAL).create({
                    'mark_id': mark.id, 'exception_type': 'low_accuracy',
                    'reason': 'Precisión GPS de %.0f m (mínima exigida %.0f m).' % (
                        mark.accuracy_meters, mark.stop_id.site_id.min_accuracy_meters),
                })
        return records

    def write(self, values):
        if self.env.context.get('_erpec_routes_token') is not _INTERNAL:
            raise ValidationError('Las marcas de visita son inmutables.')
        return super().write(values)

    def unlink(self):
        raise ValidationError('Las marcas de visita no se eliminan; conservan la trazabilidad del cumplimiento.')


class RouteException(models.Model):
    _name = 'erpec.route.exception'
    _description = 'Excepción revisable de cumplimiento de visitas'
    _order = 'create_date desc'

    stop_id = fields.Many2one('erpec.route.stop', ondelete='cascade', string='Parada')
    mark_id = fields.Many2one('erpec.route.visit.mark', ondelete='cascade', string='Marca')
    company_id = fields.Many2one('res.company', compute='_compute_company', store=True, string='Empresa')
    exception_type = fields.Selection([
        ('geofence_violation', 'Fuera de geocerca'), ('low_accuracy', 'Precisión GPS baja'),
        ('unplanned_visit', 'Visita no planificada'), ('omitted_visit', 'Visita omitida'),
    ], required=True, string='Tipo de excepción')
    reason = fields.Text(required=True, string='Motivo')
    state = fields.Selection([('pending', 'Pendiente'), ('approved', 'Aprobada'), ('rejected', 'Rechazada')],
                              default='pending', required=True, readonly=True, string='Estado')
    resolution = fields.Text(string='Resolución')
    reviewed_by = fields.Many2one('res.users', readonly=True, copy=False, string='Revisado por')
    reviewed_at = fields.Datetime(readonly=True, copy=False, string='Revisado el')

    @api.depends('stop_id.company_id', 'mark_id.company_id')
    def _compute_company(self):
        for exc in self:
            exc.company_id = exc.stop_id.company_id or exc.mark_id.company_id

    @api.model_create_multi
    def create(self, values_list):
        if self.env.context.get('_erpec_routes_token') is not _INTERNAL:
            raise ValidationError('Las excepciones se generan automáticamente; no se crean a mano.')
        return super().create(values_list)

    def action_approve(self, resolution=''):
        self.write({'state': 'approved', 'resolution': resolution,
                     'reviewed_by': self.env.user.id, 'reviewed_at': fields.Datetime.now()})
        return True

    def action_reject(self, resolution=''):
        if not resolution or not resolution.strip():
            raise UserError('Indica el motivo del rechazo.')
        self.write({'state': 'rejected', 'resolution': resolution,
                     'reviewed_by': self.env.user.id, 'reviewed_at': fields.Datetime.now()})
        return True

    def write(self, values):
        allowed_from_review = {'state', 'resolution', 'reviewed_by', 'reviewed_at'}
        if self.env.context.get('_erpec_routes_token') is not _INTERNAL and set(values) - allowed_from_review:
            raise ValidationError('Solo se revisa el estado y la resolución de una excepción.')
        return super().write(values)

    def unlink(self):
        raise ValidationError('Las excepciones no se eliminan; conservan la trazabilidad del cumplimiento.')


class RouteVisitWizard(models.TransientModel):
    """Sin app móvil en este alcance: un navegador de escritorio no siempre expone GPS, así que
    la latitud/longitud/precisión se capturan aquí manualmente (o pegadas desde un dispositivo
    con GPS) en vez de leerse automáticamente."""
    _name = 'erpec.route.visit.wizard'
    _description = 'Registrar check-in/check-out de una parada'
    stop_id = fields.Many2one('erpec.route.stop', required=True, string='Parada')
    mark_type = fields.Selection([('checkin', 'Check-in'), ('checkout', 'Check-out')], required=True, string='Tipo de marca')
    latitude = fields.Float(digits=(10, 7), required=True, string='Latitud')
    longitude = fields.Float(digits=(10, 7), required=True, string='Longitud')
    accuracy_meters = fields.Float('Precisión GPS (m)', required=True, default=20.0)

    def action_confirm(self):
        self.ensure_one()
        if self.mark_type == 'checkin':
            self.stop_id.action_checkin(self.latitude, self.longitude, self.accuracy_meters)
        else:
            self.stop_id.action_checkout(self.latitude, self.longitude, self.accuracy_meters)
        return {'type': 'ir.actions.act_window_close'}


class RouteOmitWizard(models.TransientModel):
    _name = 'erpec.route.omit.wizard'
    _description = 'Omitir una parada'
    stop_id = fields.Many2one('erpec.route.stop', required=True, string='Parada')
    reason = fields.Text(required=True, string='Motivo')

    def action_confirm(self):
        self.ensure_one()
        self.stop_id.action_omit(self.reason)
        return {'type': 'ir.actions.act_window_close'}


class RouteUnplannedWizard(models.TransientModel):
    _name = 'erpec.route.unplanned.wizard'
    _description = 'Agregar parada no planificada'
    route_day_id = fields.Many2one('erpec.route.day', required=True, string='Día de ruta')
    site_id = fields.Many2one('erpec.route.site', required=True, string='Sitio')
    reason = fields.Text(required=True, string='Motivo')

    def action_confirm(self):
        self.ensure_one()
        self.route_day_id.action_add_unplanned_stop(self.site_id.id, self.reason)
        return {'type': 'ir.actions.act_window_close'}
