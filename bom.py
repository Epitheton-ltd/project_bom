"""
 File name: bom.py
 Date:      2018/12/13 13:28
 Author:    mzimen@epitheton.com
"""
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pyson import Eval, Id
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.tools import reduce_ids, grouped_slice

from trytond.modules.product import price_digits


__all__ = ['BOM']

class BOM(metaclass=PoolMeta):
    __name__ = 'production.bom'
    #projects = fields.Many2One('project.work', 'Projects')

# :vim set sw=4 ts=4 fileencoding=utf-8 expandtab:
