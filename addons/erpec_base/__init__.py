from . import models


def post_init_hook(env):
    env['res.company']._ec_apply_locale_defaults()
