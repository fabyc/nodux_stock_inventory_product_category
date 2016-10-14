# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelView, fields
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.report import Report

__all__ = ['Inventory', 'InventoryReport']
__metaclass__ = PoolMeta


class Inventory:
    __name__ = 'stock.inventory'
    product_category = fields.Many2One('product.category', 'Category', states={
            'readonly': Eval('state') != 'draft',
            },
        depends=['state'])

    @staticmethod
    def grouping():
        return ('product',)

    @classmethod
    @ModelView.button
    def complete_lines(cls, inventories):
        '''
        Complete or update the inventories
        '''
        pool = Pool()
        Category = pool.get('product.category')
        Line = pool.get('stock.inventory.line')
        Product = pool.get('product.product')

        grouping = cls.grouping()
        to_create = []
        for inventory in inventories:
            # Compute product quantities
            product_ids = None
            if inventory.product_category:
                categories = Category.search([
                        ('parent', 'child_of',
                            [inventory.product_category.id]),
                        ])
                products = Product.search([('category', 'in', categories)])
                product_ids = [p.id for p in products]

            with Transaction().set_context(stock_date_end=inventory.date):
                pbl = Product.products_by_location(
                    [inventory.location.id], product_ids=product_ids,
                    grouping=grouping)

            # Index some data
            product2type = {}
            product2consumable = {}
            product2uom = {}

            product_qty = {}
            for product in Product.browse([line[1] for line in pbl]):
                product2uom[product.id] = product.default_uom.id

            for (location, product), quantity in pbl.iteritems():
                product_qty[product] = (quantity, product2uom[product])

            for product in Product.browse([line[1] for line in pbl]):
                product2type[product.id] = product.type
                product2consumable[product.id] = product.consumable

            # Update existing lines
            for line in inventory.lines:
                if not (line.product.active and
                        line.product.type == 'goods'
                        and not line.product.consumable):
                    Line.delete([line])
                    continue

                if inventory.product_category and line.product not in products:
                    Line.delete([line])
                    continue

                key = (inventory.location.id,) + line.unique_key
                if key in pbl:
                    quantity = pbl.pop(key)
                else:
                    quantity = 0.0
                values = line.update_values4complete(quantity)
                if values:
                    Line.write([line], values)

            # Create lines if needed
            for key, quantity in pbl.iteritems():
                product_id = key[grouping.index('product') + 1]

                quantity2, uom_id = product_qty[product_id]

                if (product2type[product_id] != 'goods'
                        or product2consumable[product_id]):
                    continue
                if not quantity:
                    continue

                #values = Line.create_values4complete(inventory, quantity)
                values = Line.create_values4complete(product_id, inventory,
                    quantity, uom_id)


                for i, fname in enumerate(grouping, 1):
                    values[fname] = key[i]
                to_create.append(values)
        if to_create:
            Line.create(to_create)

class InventoryReport(Report):
    __name__ = 'nodux_stock_inventory_product_category.inventory_report'

    @classmethod
    def parse(cls, report, records, data, localcontext):
        pool = Pool()
        User = pool.get('res.user')
        inventory = records[0]
        user = User(Transaction().user)

        localcontext['inventory'] = inventory

        return super(InventoryReport, cls).parse(report, records, data,
                localcontext=localcontext)
