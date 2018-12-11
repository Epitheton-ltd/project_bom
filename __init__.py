# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.pool import Pool
from . import work
from . import production
from . import bom


def register():
    Pool.register(
        work.Work,
        module='project_bom', type_='model')
    Pool.register(
        work.WorkBOM,
        module='project_bom', type_='model',
        depends=['production',])
    Pool.register(
        bom.BOM,
        module='project_bom', type_='model',
        depends=['production', 'purchase_request',])
