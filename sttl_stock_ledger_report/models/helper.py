from collections import defaultdict
from odoo import models, api


class StockLedgerReportHelper(models.AbstractModel):
    _name = 'stock.ledger.report.helper'
    _description = 'Stock Ledger Report Helper'

    @api.model
    def get_report_data(self, data):
        report_by = data.get('report_by')
        location_ids = data.get('location_ids') or []

        report_lines = []
        for loc_id in location_ids:
            single_data = data.copy()
            single_data['location_ids'] = [loc_id]
            single_data['all_location_ids'] = location_ids
            single_data['location_name'] = self.env['stock.location'].browse(loc_id).display_name
            report_lines.extend(self._get_report_data_single_location(single_data))

        # Sort key: only use location name if report_by is True
        sort_key = (
            lambda r: (r['location_name'], r['date'], r['product_id'])
            if report_by else
            (r['date'], r['product_id'])
        )
        report_lines.sort(key=sort_key)

        # Optionally suppress location column later during rendering
        return report_lines

    @api.model
    def _get_transit_in_out_by_location(self, start_date, end_date, product_ids, selected_location_ids, all_location_ids):
        domain = [
            ('state', '=', 'done'),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            '|',
            ('location_id', 'in', all_location_ids),
            ('location_dest_id', 'in', all_location_ids),
        ]
        if product_ids:
            domain.append(('product_id', 'in', product_ids))

        result = defaultdict(lambda: {'transit_in': 0.0, 'transit_out': 0.0})
        for move in self.env['stock.move'].search(domain):
            src = move.location_id
            dest = move.location_dest_id
            pid = move.product_id.id
            date = move.date.date()

            for line in move.move_line_ids:
                qty = line.qty_done or 0.0

                if src.usage == 'internal' and dest.usage == 'transit':
                    if dest.id in selected_location_ids:
                        result[(date, pid, dest.id)]['transit_out'] += qty
                    elif src.id in all_location_ids:
                        result[(date, pid, src.id)]['transit_out'] += qty

                elif src.usage == 'transit' and dest.usage == 'internal':
                    if src.id in selected_location_ids:
                        result[(date, pid, src.id)]['transit_in'] += qty
                    elif dest.id in all_location_ids:
                        result[(date, pid, dest.id)]['transit_in'] += qty

        return [
            {
                'date': date,
                'product_id': pid,
                'location_id': lid,
                'transit_in': val['transit_in'],
                'transit_out': val['transit_out'],
            }
            for (date, pid, lid), val in result.items()
            if lid in selected_location_ids
        ]

    @api.model
    def _get_report_data_single_location(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        product_ids = data.get('product_ids') or []
        categ_ids = data.get('categ_ids') or []
        location_ids = data.get('location_ids') or []
        report_by = data.get('report_by')
        all_location_ids = data.get('all_location_ids', location_ids)

        # Resolve final product ids
        final_product_ids = []
        if categ_ids:
            category_product_ids = self.env['product.template'].search([
                ('categ_id', 'in', categ_ids)
            ]).mapped('product_variant_ids.id')
        else:
            category_product_ids = []

        if product_ids and category_product_ids:
            final_product_ids = list(set(product_ids) & set(category_product_ids))
        elif product_ids or category_product_ids:
            final_product_ids = product_ids or category_product_ids

        if (product_ids or categ_ids) and not final_product_ids:
            return []

        # Product filtering
        base_condition = "sm.date BETWEEN %s AND %s"
        base_params = [start_date, end_date]
        if location_ids:
            base_condition += " AND (sm.location_id = ANY(%s) OR sm.location_dest_id = ANY(%s))"
            base_params += [location_ids, location_ids]
        if final_product_ids:
            base_condition += " AND sm.product_id = ANY(%s)"
            base_params.append(final_product_ids)

        self.env.cr.execute(f"""
            SELECT DISTINCT sm.product_id
            FROM stock_move sm
            WHERE sm.state = 'done' AND {base_condition}
        """, tuple(base_params))
        filtered_product_ids = [r['product_id'] for r in self.env.cr.dictfetchall()]
        if not filtered_product_ids:
            return []

        # Opening calculation
        opening_map = defaultdict(float)
        self.env.cr.execute("""
            SELECT sm.product_id, sm.location_id, sm.location_dest_id,
                   sml.qty_done, sl_src.usage AS src_usage, sl_dest.usage AS dest_usage
            FROM stock_move sm
            LEFT JOIN stock_move_line sml ON sm.id = sml.move_id
            LEFT JOIN stock_location sl_src ON sm.location_id = sl_src.id
            LEFT JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
            WHERE sm.date < %s AND sm.state = 'done' AND sm.product_id = ANY(%s)
        """, (start_date, filtered_product_ids))

        for row in self.env.cr.dictfetchall():
            pid, qty = row['product_id'], row['qty_done'] or 0.0
            src_id, dest_id = row['location_id'], row['location_dest_id']
            if src_id in location_ids:
                if row['src_usage'] in ['internal', 'transit']:
                    opening_map[(pid, src_id)] -= qty
            if dest_id in location_ids:
                if row['dest_usage'] in ['internal', 'transit']:
                    opening_map[(pid, dest_id)] += qty

        # Main movement query
        main_query = f"""
            WITH normalized_move AS (
                SELECT sm.date::date AS date, sm.product_id, ptmpl.categ_id,
                       CASE WHEN sm.location_id = ANY(%s) THEN sm.location_id ELSE sm.location_dest_id END AS location_id,
                       sml.qty_done, pt.code AS picking_code,
                       sl_src.usage AS src_usage, sl_dest.usage AS dest_usage,
                       sm.production_id, sm.raw_material_production_id,
                       sm.location_dest_id = ANY(%s) AS is_internal_in,
                       sm.location_id = ANY(%s) AS is_internal_out
                FROM stock_move sm
                LEFT JOIN stock_move_line sml ON sm.id = sml.move_id
                LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
                LEFT JOIN stock_picking_type pt ON sp.picking_type_id = pt.id
                LEFT JOIN stock_location sl_src ON sm.location_id = sl_src.id
                LEFT JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                LEFT JOIN product_product pp ON sm.product_id = pp.id
                LEFT JOIN product_template ptmpl ON pp.product_tmpl_id = ptmpl.id
                WHERE sm.state = 'done' AND {base_condition}
            )
            SELECT date, product_id, categ_id, location_id,
                   SUM(CASE WHEN picking_code = 'outgoing' AND src_usage = 'internal' AND dest_usage = 'customer' THEN qty_done ELSE 0 END) AS sale_qty,
                   SUM(CASE WHEN picking_code = 'incoming' AND src_usage = 'supplier' AND dest_usage = 'internal' THEN qty_done ELSE 0 END) AS purchase_qty,
                   SUM(CASE WHEN picking_code = 'incoming' AND src_usage = 'customer' AND dest_usage = 'internal' THEN qty_done ELSE 0 END) AS sale_return_qty,
                   SUM(CASE WHEN picking_code = 'outgoing' AND src_usage = 'internal' AND dest_usage = 'supplier' THEN qty_done ELSE 0 END) AS purchase_return_qty,
                   SUM(CASE WHEN src_usage = 'internal' AND dest_usage = 'internal' AND is_internal_in THEN qty_done ELSE 0 END) AS internal_in_qty,
                   SUM(CASE WHEN src_usage = 'internal' AND dest_usage = 'internal' AND is_internal_out THEN qty_done ELSE 0 END) AS internal_out_qty,
                   SUM(CASE WHEN production_id IS NOT NULL AND raw_material_production_id IS NULL THEN qty_done ELSE 0 END) AS production_in_qty,
                   SUM(CASE WHEN production_id IS NULL AND raw_material_production_id IS NOT NULL THEN qty_done ELSE 0 END) AS production_out_qty,
                   SUM(CASE WHEN src_usage IN ('inventory', 'inventory_loss') AND dest_usage = 'internal' THEN qty_done ELSE 0 END) AS adjustment_in_qty,
                   SUM(CASE WHEN src_usage = 'internal' AND dest_usage IN ('inventory', 'inventory_loss') THEN qty_done ELSE 0 END) AS adjustment_out_qty
            FROM normalized_move
            GROUP BY date, product_id, categ_id, location_id
            ORDER BY date
        """
        params = [location_ids, location_ids, location_ids] + base_params
        self.env.cr.execute(main_query, tuple(params))
        results = self.env.cr.dictfetchall()

        # Add transit data
        transit_lines = self._get_transit_in_out_by_location(
            start_date, end_date, filtered_product_ids, location_ids, all_location_ids
        )
        transit_map = {(l['date'], l['product_id'], l['location_id']): l for l in transit_lines}
        transit_short_map = {(l['date'], l['product_id']): l for l in transit_lines}

        loc_map = {l.id: l for l in self.env['stock.location'].browse(set(r['location_id'] for r in results))}
        prod_map = {p.id: p for p in self.env['product.product'].browse(set(r['product_id'] for r in results))}
        cat_map = {c.id: c for c in self.env['product.category'].browse(set(r['categ_id'] for r in results))}

        current_opening_map = dict(opening_map)
        report_lines = []
        for res in results:
            pid, lid = res['product_id'], res['location_id']
            date_key = res['date']
            opening_qty = current_opening_map.get((pid, lid), 0.0)
            loc_usage = loc_map[lid].usage

            # Transit data merge
            if loc_usage == 'transit':
                t_data = transit_short_map.get((date_key, pid), {})
                res['transit_in_qty'] = t_data.get('transit_out', 0.0)
                res['transit_out_qty'] = t_data.get('transit_in', 0.0)
            else:
                t_data = transit_map.get((date_key, pid, lid), {})
                res['transit_in_qty'] = t_data.get('transit_in', 0.0)
                res['transit_out_qty'] = t_data.get('transit_out', 0.0)

            total_in = sum(res.get(k, 0.0) for k in (
                'purchase_qty', 'sale_return_qty', 'internal_in_qty',
                'transit_in_qty', 'production_in_qty', 'adjustment_in_qty',
            ))
            total_out = sum(res.get(k, 0.0) for k in (
                'sale_qty', 'purchase_return_qty', 'internal_out_qty',
                'transit_out_qty', 'production_out_qty', 'adjustment_out_qty',
            ))
            closing_qty = opening_qty + total_in - total_out
            current_opening_map[(pid, lid)] = closing_qty

            res.update({
                'product_name': prod_map[pid].name,
                'category_name': cat_map.get(res['categ_id'], '').name if res['categ_id'] else '',
                'location_name': loc_map[lid].complete_name,
                'opening_qty': opening_qty,
                'closing_qty': closing_qty,
            })
            report_lines.append(res)

        return report_lines
