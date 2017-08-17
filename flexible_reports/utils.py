# -*- encoding: utf-8 -*-

from . import constants


def get_shortcuts(model):
    return getattr(model, constants.SHORTCUTS_ATTR_NAME, {})
