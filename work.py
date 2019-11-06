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
    code = fields.Char('Code', help='The other number assigned to the project.')
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

    def all_missing_orders(self) -> 'product.product':
        """ Generator over all products missing in stock """
        for pr in self.purchase_requests:
            if pr.state in ('processing', 'done'):
                continue
            elif pr.purchase and pr.purchase.state == 'done':
                continue
            yield pr.product

    def all_missing_products(self) -> 'product.product':
        """ Generator over all products missing in stock """
        for pr in self.purchase_requests:
            if pr.state == 'done':
                continue
            elif pr.purchase and pr.purchase.state == 'done':
                continue
            yield pr.product

    def quoting_products(self):
        """ generator over all products """
        for p in self.purchases:
            if p.state in ('quotation',):
                for _ in p.lines:
                    yield _.product

    def purchased_products(self):
        """ Generator over all purchased products """
        for p in self.purchases:
            if p.state in ('purchased', 'processing'):
                for _ in p.lines:
                    yield _.product

    def delivered_products(self) -> 'product.product':
        """ Generator over all delivered products """
        for pr in self.purchase_requests:
            if pr.state == 'done':
                yield pr.product
            elif pr.purchase and pr.purchase.state == 'done':
                yield pr.product

    def ordered_products(self):
        """ generator over all products """
        for p in self.purchases:
            if p.state in ('done', 'processing'):
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

    def get_missing_orders(self) -> 'purchase.purchase_request':
        for pr in self.purchase_requests:
            if pr.state == 'done':
                continue
            elif pr.purchase and pr.purchase.state == 'done':
                continue
            yield pr

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

    #@property
    def amount_of_missing_products(self) -> int:
        return len([p for p in self.all_missing_products()])

    #@property
    def amount_of_missing_orders(self) -> int:
        return len([p for p in self.all_missing_orders()])

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
