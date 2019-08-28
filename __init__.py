from trytond.pool import Pool
from . import work
from . import production
from . import bom
from . import purchase


def register():
    Pool.register(
        work.Work,
        work.WorkBOM,
        work.WorkProduction,
        module='project_bom',
        type_='model',
        depends=[
            'production',
            'purchase',
            'purchase_request',
        ])
    Pool.register(
        bom.BOM,
        module='project_bom',
        type_='model',
        depends=['production', 'purchase_request',])
    Pool.register(
        purchase.PurchaseRequest,
        purchase.Purchase,
        module='project_bom',
        type_='model',
        depends=['purchase', 'purchase_request']
    )
