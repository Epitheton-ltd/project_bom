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
    purchase_requests = fields.Many2Many(
        'project.work.purchase_request',  # relation-name -> ref to WorKBOM
        'work',  # origin
        'purchase_request',  # target
        'PurchaseRequests'
    )
    purchases = fields.Many2Many(
        'project.work.purchase',  # relation-name -> ref to WorkPurchase
        'work',  # origin
        'purchase',  # target
        'Purchases'
    )
    boms = fields.Many2Many(
        'project.work.bom',  # relation-name -> ref to WorkBOM
        'work',  # origin
        'bom',  # target
        'BOMs'
    )
    productions = fields.Many2Many(
        'project.work.production',  # relation-name -> ref to WorkProduction
        'work',  # origin
        'production',  # target
        'Productions'
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
        ''' generator over all products '''
        for bom in self.boms:
            for _ in bom.inputs:
                if _.product not in self.ordered_products():
                    yield _.product

    def quoting_products(self):
        ''' generator over all products '''
        for p in self.purchases:
            if p.state in ('quotation',):
                for _ in p.lines:
                    yield _.product

    def purchased_products(self):
        ''' generator over all products '''
        for p in self.purchases:
            if p.state in ('done',):
                for _ in p.lines:
                    yield _.product

    def ordered_products(self):
        ''' generator over all products '''
        for p in self.purchases:
            if p.state in ('confirmed', 'processing'):
                for _ in p.lines:
                    yield _.product

    def all_products(self, filter=None) -> tuple:
        ''' generator over all products via productions '''
        for production in self.productions:
            for _ in production.bom.inputs:
                yield _.product, _.quantity, production.bom.id, production.id

    def all_purchases_cost(self, filter=None) -> tuple:
        ''' generator over all products via productions '''
        x = []
        for purchase in self.purchases:
            for line in purchase.lines:
                x.append(line.quantity * float(line.unit_price))
        return x

    def product_purchase(self, product, quantity=None) -> 'purchase':
        for purchase in self.purchases:
            for line in purchase.lines:
                if line.product.id == product.id:
                    if quantity:  # checking also for quantity
                        if line.quantity == quantity:
                            return purchase
                    else:
                        return purchase
        return None

    def product_supplier(self, product, quantity=None) -> 'purchase.party':
        for purchase in self.purchases:
            for line in purchase.lines:
                if line.product.id == product.id:
                    if quantity:  # checking also for quantity
                        if line.quantity == quantity:
                            return purchase.delivery_date
                    else:
                        return purchase.party
        return None

    def product_delivery_date(self, product, quantity=None) -> date:
        '''
        delivery_date for particular product
        '''
        for purchase in self.purchases:
            for line in purchase.lines:
                if line.product.id == product.id:
                    if quantity:  # checking also for quantity
                        if line.quantity == quantity:
                            return purchase.delivery_date
                    else:
                        return purchase.delivery_date
        return None

    def get_missing_orders(self) -> 'product.product':
        for p in self.productions:
            for p in p.bom.inputs:
                if p.product in self.all_missing_products():
                    yield p

    def total_product_cost(self) -> float:
        return round(sum([p for p in self.all_purchases_cost()]),2)

    def amount_of_missing_products(self) -> int:
        return len([p for p in self.all_missing_products()])

    def create_purchase_requests_from_bom(self, boms):
        'This task should be run from scheduler'
        create_pr = Wizard('stock.supply')
        create_pr.execute('create_')


class WorkPurchaseRequest(ModelSQL):
    ''' Relation between Project and BOMs '''
    __name__ = 'project.work.purchase_request'

    work = fields.Many2One('project.work', 'Project')
    purchase_request = fields.Many2One('purchase.request', 'PurchaseRequest')


class WorkPurchase(ModelSQL):
    ''' Relation between Project and Purchase '''
    __name__ = 'project.work.purchase'

    work = fields.Many2One('project.work', 'Project')
    purchase = fields.Many2One('purchase.purchase', 'Purchase')


class WorkBOM(ModelSQL):
    ''' Relation between Project and BOMs '''
    __name__ = 'project.work.bom'

    work = fields.Many2One('project.work', 'Project')
    bom = fields.Many2One('production.bom', 'BOM')


class WorkProduction(ModelSQL):
    '''
        Relation between Project and Production
        One project can have multiple (unique) productions
    '''
    __name__ = 'project.work.production'

    work = fields.Many2One('project.work', 'Project')
    production = fields.Many2One('production', 'Production')
