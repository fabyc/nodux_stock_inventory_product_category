# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .inventory import *

def register():
    Pool.register(
        Inventory,
        module='nodux_stock_inventory_product_category', type_='model')
    Pool.register(
        InventoryReport,
        module='nodux_stock_inventory_product_category', type_='report')
