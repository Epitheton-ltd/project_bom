"""
class Book:
    __name__ = 'library.book'
    renter = fields.Many2One('party.party',
                             'Renter',
                             required=False)

class User:
    __name__ = 'party.party'
    rented_books = fields.One2Many('library.book',
                                   'renter',
                                   'Rented Books')
"""
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

__all__ = ['Work', 'WorkBOM', 'WorkPurchase', 'WorkPurchaseRequest']


class Work(metaclass=PoolMeta):

    __name__ = 'project.work'
    purchase_requests = fields.One2Many(
        model_name='purchase.request',
        field='project',
        string='Purchase Requests'
    )
    purchases = fields.One2Many(
        model_name='purchase.purchase',
        field='project',
        string='Purchases'
    )
    boms = fields.Many2Many(
        relation_name='project.work.bom',
        origin='work',
        target='bom',
        string='BOMs'
    )
    productions = fields.Many2Many(
        relation_name='project.work.production',
        origin='work',  # origin
        target='production',  # target
        string='Productions'
    )

    assembly_date = fields.Function(fields.Date('Assembly Date'), 'get_assembly_date')
    delivery_date = fields.Function(fields.Date('Delivery Date'), 'get_delivery_date')

    def get_assembly_date(self, *args):
        if self.productions:
            for p in self.productions:
                for w in p.works:
                    if w.operation.name == 'ASSEMBLY':
                        return w.timesheet_works[0].timesheet_start_date
        return None

    def get_delivery_date(self, *args) -> date:
        if self.productions:
            return self.productions[0].planned_date
        return None

    def has_product(self, product_id):
        for bom in p.boms:
            if product_id in bom.inputs:
                return True
        return False

    def all_missing_products(self) -> 'product.product':
        """ generator over all products """
        for bom in self.boms:
            for _ in bom.inputs:
                if _.product not in self.ordered_products():
                    yield _.product

    def quoting_products(self):
        """ generator over all products """
        for p in self.purchases:
            if p.state in ('quotation',):
                for _ in p.lines:
                    yield _.product

    def purchased_products(self):
        """ generator over all products """
        for p in self.purchases:
            if p.state in ('done',):
                for _ in p.lines:
                    yield _.product

    def ordered_products(self):
        """ generator over all products """
        for p in self.purchases:
            if p.state in ('confirmed', 'processing'):
                for _ in p.lines:
                    yield _.product

    def all_products(self, filter=None) -> tuple:
        """ generator over all products via productions """
        for production in self.productions:
            if production.bom:
                for _ in production.bom.inputs:
                    yield _.product, _.quantity, production.bom.id, production.id

    def all_purchases_cost(self, filter=None) -> tuple:
        """ generator over all products via productions """
        x = []
        for purchase in self.purchases:
            for line in purchase.lines:
                x.append(line.quantity * float(line.unit_price))
        return x

    def product_purchase(self, product, quantity=None) -> 'purchase':
        """
        Get the list of purchase per product
        """
        for purchase in self.purchases:
            for line in purchase.lines:
                if not line.product:
                    continue
                if line.product.id == product.id:
                    if quantity:  # checking also for quantity
                        if line.quantity == quantity:
                            return purchase
                    else:
                        return purchase
        return None

    def product_supplier(self, product, quantity=None) -> 'purchase.party':
        """
        Get the list of purchase party per product
        """
        for purchase in self.purchases:
            for line in purchase.lines:
                if not line.product:
                    continue   # FIXME@mzimen!!!!
                if line.product.id == product.id:
                    if quantity:  # checking also for quantity
                        if line.quantity == quantity:
                            return purchase.delivery_date
                    else:
                        return purchase.party
        return None

    def product_delivery_date(self, product, quantity=None) -> date:
        """
        delivery_date for particular product
        """
        for purchase in self.purchases:
            for line in purchase.lines:
                if not line.product:  #FIXME@mzimen: (temporarily workaround due to
                    continue
                if line.product.id == product.id:
                    if quantity:  # checking also for quantity
                        if line.quantity == quantity:
                            return purchase.delivery_date
                    else:
                        return purchase.delivery_date
        return None

    def get_missing_orders(self) -> 'product.product':
        for p in self.productions:
            if p.bom:
                for p in p.bom.inputs:
                    if p.product in self.all_missing_products():
                        yield p

    def total_product_cost(self) -> float:
        return round(sum([p for p in self.all_purchases_cost()]), 2)

    def get_today_hours(self) -> float:
        for tw in self.timesheet_works:
            for tl in tw.timesheet_lines:
                if tl.date == date.today():
                    return tl.duration.total_seconds() / 3600
        return 0

    def total_hours(self) -> float:
        total = 0
        for tw in self.timesheet_works:
            for tl in tw.timesheet_lines:
                total += tl.duration.total_seconds()
        return round(total/3600, 2)

    def amount_of_missing_products(self) -> int:
        return len([p for p in self.all_missing_products()])
    amount_of_missing_purchase_requests = amount_of_missing_products

    def create_purchase_requests_from_bom(self, boms):
        'This task should be run from scheduler'
        create_pr = Wizard('stock.supply')
        create_pr.execute('create_')


class WorkBOM(ModelSQL):
    """ Relation between Project and BOMs """
    __name__ = 'project.work.bom'

    work = fields.Many2One('project.work', 'Project')
    bom = fields.Many2One('production.bom', 'BOM')


class WorkProduction(ModelSQL):
    """
        Relation between Project and Production
        One project can have multiple (unique) productions
    """
    __name__ = 'project.work.production'

    work = fields.Many2One('project.work', 'Project')
    production = fields.Many2One('production', 'Production')
