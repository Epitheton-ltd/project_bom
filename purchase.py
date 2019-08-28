# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from decimal import Decimal
from collections import defaultdict
from datetime import date

from sql.aggregate import Sum
from sql.operators import Concat

from trytond.model import (
    ModelView, ModelSQL, Model, UnionMixin, DeactivableMixin, fields)
from trytond.model import fields
from trytond.pyson import Eval, Id
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.tools import reduce_ids, grouped_slice


__all__ = ['PurchaseRequestProject', 'PurchaseProject']

class PurchaseRequest(metaclass=PoolMeta):
    """
    A purchase_request can have only one project => one-to-one
    """
    __name__ = 'purchase.request'

    project = fields.Many2One(
        'project.work',
        'Project',
        required=False,
    )


class Purchase(metaclass=PoolMeta):
    """
    A purchase_request can have only one project => one-to-one
    """
    __name__ = 'purchase.purchase'

    project = fields.Many2One(
        'project.work',
        'Project',
        required=False,
    )
