# -*- encoding: utf-8 -*-
##############################################################################
#
#    POS Sale Report module for Odoo
#    Copyright (C) 2015 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields
from openerp import tools


class pos_sale_report(models.Model):
    _name = 'pos.sale.report'
    _description = 'POS orders and Sale orders aggregated report'
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    date = fields.Date(string='Order Date', readonly=True)
    product_id = fields.Many2one(
        'product.product', string='Product Variant', readonly=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', readonly=True)
    owner_id = fields.Many2one(
        'res.partner', string='Owner', readonly=True)
    prodlot_id = fields.Many2one(
        'stock.production.lot', string='Serial Number', readonly=True)


    origin = fields.Char(string='Origin', readonly=True)
    qty = fields.Float(string='Quantity', readonly=True)
    price_unit = fields.Float(string='Unit Price', readonly=True)
    total_sales_amount = fields.Float(string='Total Sales', readonly=True)

    # WARNING : this code doesn't handle uom conversion for the moment
    def _sale_order_select(self):
        select = """SELECT sol.id AS sol_id,
            so.date_order::date AS date,
            sol.product_id AS product_id,
            sloo.lot_id AS prodlot_id,
            sloo.owner_id AS owner_id,
            sol.price_unit AS price_unit,
            (sol.price_unit * sol.product_uos_qty) AS total_sales_amount,
            pp.product_tmpl_id AS product_tmpl_id,
            so.company_id AS company_id,
            'Sale Order' AS origin,
            sum(sol.product_uom_qty) AS qty
            FROM sale_order_line sol
            LEFT JOIN sale_order so ON so.id = sol.order_id
            LEFT JOIN product_product pp ON pp.id = sol.product_id
            LEFT JOIN sale_lot_owner_order sloo ON sloo.sale_order_ln_id=sol.id      
            WHERE so.state NOT IN ('draft', 'sent', 'cancel') and  sloo.lot_id is null
            GROUP BY sol.id, so.date_order, sol.product_id, pp.product_tmpl_id, sloo.lot_id, sloo.owner_id, sol.price_unit, (sol.price_unit * sol.product_uos_qty),
            so.company_id
 union
 SELECT sol.id AS sol_id,
            so.date_order::date AS date,
            sol.product_id AS product_id,
            sloo.lot_id AS prodlot_id,
            sloo.owner_id AS owner_id,
            sol.price_unit AS price_unit,
            (sol.price_unit * 1.0) AS total_sales_amount,
            pp.product_tmpl_id AS product_tmpl_id,
            so.company_id AS company_id,
            'Sale Order' AS origin,
            1 AS qty
            FROM sale_order_line sol
            LEFT JOIN sale_order so ON so.id = sol.order_id
            LEFT JOIN product_product pp ON pp.id = sol.product_id
            LEFT JOIN sale_lot_owner_order sloo ON sloo.sale_order_ln_id=sol.id      
            WHERE so.state NOT IN ('draft', 'sent', 'cancel') and  sloo.lot_id is not null
            GROUP BY sol.id, so.date_order, sol.product_id, pp.product_tmpl_id, sloo.lot_id, sloo.owner_id, sol.price_unit, (sol.price_unit * 1.0),
            so.company_id


        """
        return select

    def _pos_order_select(self):
        select = """SELECT pol.id AS pol_id,
            po.date_order::date AS date,
            pol.product_id AS product_id,
	    pol.prodlot_id AS prodlot_id,
            pol.product_owner_id AS owner_id,
	    pol.price_unit AS price_unit,
	    pol.price_subtotal AS total_sales_amount,
            pp.product_tmpl_id AS product_tmpl_id,
            po.company_id AS company_id,
            'Point of Sale' AS origin,
            sum(pol.qty) AS qty
            FROM pos_order_line pol
            LEFT JOIN pos_order po ON po.id = pol.order_id
            LEFT JOIN product_product pp ON pp.id = pol.product_id
            WHERE po.state IN ('paid', 'done', 'invoiced')
            GROUP BY pol.id, po.date_order, pol.product_id, pp.product_tmpl_id, pol.prodlot_id, pol.product_owner_id, pol.price_unit, pol.price_subtotal, 
            po.company_id
        """
        return select

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        #tools.drop_view_if_exists(cr,"sale_lot_owner_order")
    	cr.execute("""create or replace view sale_lot_owner_order AS select tmp.lot_id, tmp.owner_id, aa.sale_order_ln_id 
    	from (select lot_id, owner_id from public.stock_pack_operation
    	where purchase_order_ln_id in (select id FROM public.purchase_order_line) 
    	and lot_id in(SELECT lot_id FROM public.stock_pack_operation where sale_order_ln_id in(SELECT id FROM public.sale_order_line))) tmp,
    	(select bb.lot_id,bb.sale_order_ln_id from public.stock_pack_operation bb where bb.sale_order_ln_id in(SELECT id FROM public.sale_order_line) ) aa 
    	where tmp.lot_id = aa.lot_id order by lot_id""")
    	#cr.execute("ALTER view sale_lot_owner_order OWNER TO odoo")
    	#cr.execute("grant all on public.sale_lot_owner_order to odoo, postgres")
    	cr.execute("CREATE OR REPLACE VIEW %s AS (select *,row_number() over() as id  from (%s UNION %s) as x)" % (
                self._table, self._sale_order_select(), self._pos_order_select()))
    

	
