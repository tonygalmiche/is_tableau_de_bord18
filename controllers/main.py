# -*- coding: utf-8 -*-

import json
import ast
import logging
from odoo import http
from odoo.http import request
from lxml import etree


_logger = logging.getLogger(__name__)


class TableauDeBordController(http.Controller):

    @http.route('/tableau_de_bord/get_filter_data/<int:filter_id>', type='json', auth='user')
    def get_filter_data(self, filter_id, line_id=None, **kwargs):
        """Récupère les données d'un filtre pour l'afficher dans le tableau de bord"""
        try:
            # line_id/overrides peuvent arriver uniquement dans kwargs selon le client JS
            if not line_id:
                line_id = kwargs.get('line_id')
            overrides = kwargs.get('overrides') or {}
            _logger.info("[TDB] get_filter_data filter_id=%s", filter_id)
            filter_obj = request.env['ir.filters'].browse(filter_id)
            if not filter_obj.exists():
                return {'error': 'Filtre non trouvé'}

            model = request.env[filter_obj.model_id]

            # Récupérer le domaine du filtre
            domain = []
            if filter_obj.domain:
                try:
                    domain = ast.literal_eval(filter_obj.domain)
                except Exception:
                    domain = []

            # Récupérer le contexte du filtre
            context = {}
            if filter_obj.context:
                try:
                    context = ast.literal_eval(filter_obj.context)
                except Exception:
                    context = {}

            # Fusionner avec le contexte actuel
            ctx = dict(request.env.context)
            ctx.update(context)

            # Appliquer overrides éventuels de la ligne (sur ctx)
            if line_id:
                try:
                    line = request.env['is.tableau.de.bord.line'].browse(int(line_id))
                    if line and line.exists():
                        if line.display_mode and line.display_mode != 'auto':
                            ctx['search_default_view_type'] = line.display_mode
                        if line.graph_chart_type:
                            ctx['graph_chart_type'] = line.graph_chart_type
                        if line.graph_aggregator:
                            ctx['graph_aggregator'] = line.graph_aggregator
                        if line.pivot_row_groupby:
                            ctx['pivot_row_groupby'] = line.pivot_row_groupby
                        if line.pivot_col_groupby:
                            ctx['pivot_column_groupby'] = line.pivot_col_groupby
                        if line.pivot_measure:
                            ctx['pivot_measures'] = line.pivot_measure
                except Exception:
                    pass

            # Appliquer aussi d'éventuels overrides envoyés côté client (sécurisé au scope utilisateur)
            if isinstance(overrides, dict):
                safe_keys = {
                    'search_default_view_type', 'graph_chart_type', 'graph_aggregator',
                    'pivot_row_groupby', 'pivot_column_groupby', 'pivot_measures',
                    'graph_groupbys', 'graph_measure', 'list_fields', 'measure', 'group_by'
                }
                for k, v in overrides.items():
                    if k in ('display_mode',):
                        ctx['search_default_view_type'] = v
                    elif k in safe_keys:
                        ctx[k] = v

            _logger.debug("[TDB] ctx_keys=%s domain=%s", list(ctx.keys()), domain)

            # Déterminer le type de vue à utiliser
            view_type = self._get_view_type_from_context(ctx)
            _logger.info("[TDB] view_type=%s model=%s", view_type, filter_obj.model_id)

            model = model.with_context(ctx)
            if view_type == 'graph':
                return self._get_graph_data(model, filter_obj, domain, ctx)
            elif view_type == 'pivot':
                return self._get_pivot_data(model, filter_obj, domain, ctx)
            else:
                return self._get_list_data(model, filter_obj, domain, ctx)

        except Exception as e:
            _logger.exception("[TDB] get_filter_data error: %s", e)
            return {'error': str(e)}

    def _get_view_type_from_context(self, context):
        """Détermine le type de vue à partir du contexte"""
        if context.get('graph_measure') or context.get('graph_groupbys'):
            return 'graph'
        if context.get('pivot_measures') or context.get('pivot_row_groupby') or context.get('pivot_column_groupby'):
            return 'pivot'
        if 'graph' in context.get('search_default_view_type', ''):
            return 'graph'
        if 'pivot' in context.get('search_default_view_type', ''):
            return 'pivot'
        return 'list'

    def _get_list_data(self, model, filter_obj, domain, context):
        """Génère les données pour une vue liste"""
        # 1) Champs explicitement définis dans le favori (list_fields)
        explicit_fields = []
        if context.get('list_fields'):
            lf = context.get('list_fields')
            if isinstance(lf, str):
                # accepter "a,b,c"
                explicit_fields = [f.strip() for f in lf.split(',') if f.strip()]
            elif isinstance(lf, (list, tuple)):
                explicit_fields = [str(f).strip() for f in lf if str(f).strip()]
            # ne garder que les champs existants
            explicit_fields = [f for f in explicit_fields if f in model._fields]

        view_id = None
        xmlid = context.get('tree_view_ref') or context.get('list_view_ref')
        if xmlid:
            try:
                view_id = request.env.ref(xmlid).id
            except Exception:
                view_id = None

        if explicit_fields:
            # libellés depuis fields_get
            fields_def = model.fields_get(explicit_fields)
            fields_to_display = explicit_fields
            field_labels = {f: fields_def.get(f, {}).get('string', f) for f in explicit_fields}
        else:
            fields_to_display, field_labels = self._get_fields_from_view(model, 'list', view_id=view_id)
        _logger.info("[TDB] list fields=%s (view_id=%s)", fields_to_display, view_id)

        recs = model.search(domain, limit=50)
        data = recs.read(fields_to_display) if recs else []

        fields_meta = [{'name': f, 'string': field_labels.get(f, f)} for f in fields_to_display]

        return {
            'type': 'list',
            'data': data,
            'fields': fields_meta,
            'count': model.search_count(domain),
            'model': filter_obj.model_id,
        }

    def _get_graph_data(self, model, filter_obj, domain, context):
        """Génère les données pour un graphique simple"""
        groupbys = context.get('graph_groupbys') or context.get('group_by') or []
        if isinstance(groupbys, str):
            groupbys = [groupbys]
        measure = context.get('graph_measure') or context.get('measure')
        aggregator = context.get('graph_aggregator') or 'sum'
        chart_type = context.get('graph_chart_type') or 'bar'
        _logger.info("[TDB] graph groupbys=%s measure=%s agg=%s", groupbys, measure, aggregator)

        agg_label = "Nombre d'enregistrements"
        use_count = not measure or str(measure) in ('count', '__count')
        fields = [] if use_count else [f"{measure}:{aggregator}"]
        if not use_count:
            agg_label = f"{aggregator} de {measure}"

        try:
            results = model.read_group(domain, fields=fields, groupby=groupbys, lazy=False)
        except Exception:
            results = []
        _logger.debug("[TDB] graph results=%s", len(results))

        labels = []
        values = []
        if results:
            for r in results:
                label_parts = []
                for gb in groupbys:
                    base = gb.split(':')[0]
                    val = r.get(gb) or r.get(base) or r.get(f"{gb}_name") or r.get(f"{base}_name")
                    label_parts.append(str(val) if val is not None else '')
                labels.append(" / ".join([p for p in label_parts if p]))
                if use_count:
                    values.append(r.get("__count") or 0)
                else:
                    values.append(r.get(f"{measure}_{aggregator}") or r.get(measure) or 0)
        else:
            labels = ['Total']
            values = [model.search_count(domain)]

        # Ajuster la palette à la longueur
        palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        bg = [palette[i % len(palette)] for i in range(len(values))]

        return {
            'type': 'graph',
            'chart_type': chart_type,
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': agg_label,
                    'data': values,
                    'backgroundColor': bg
                }]
            }
        }

    def _get_pivot_data(self, model, filter_obj, domain, context):
        """Génère les données pour un tableau croisé; support 1D (lignes) et 2D (lignes x colonnes)."""
        row_gb = context.get('pivot_row_groupby') or context.get('group_by')
        if isinstance(row_gb, list):
            row_gb = row_gb[0] if row_gb else None
        col_gb = context.get('pivot_column_groupby')
        if isinstance(col_gb, list):
            col_gb = col_gb[0] if col_gb else None
        measures = context.get('pivot_measures') or context.get('measure')
        if isinstance(measures, list):
            measure = measures[0] if measures else None
        else:
            measure = measures
        _logger.info("[TDB] pivot row_gb=%s col_gb=%s measure=%s", row_gb, col_gb, measure)

        use_count = not measure or str(measure) in ('count', '__count')
        fields = [] if use_count else [f"{measure}:sum"]

        if row_gb and col_gb:
            # 2D pivot
            try:
                results = model.read_group(domain, fields=fields or ["__count"], groupby=[row_gb, col_gb], lazy=False)
            except Exception:
                results = []
            # collect columns
            col_labels = []
            col_index = {}
            def _label_for(rec, gb):
                full = (gb or '')
                base = full.split(':')[0]
                # tenter d'abord la clé complète (utile pour date gb: field:year)
                return rec.get(f"{full}_name") or rec.get(f"{base}_name") or rec.get(full) or rec.get(base) or 'Indéfini'
            # build rows structure
            rows_map = {}
            for r in results:
                rlab = _label_for(r, row_gb)
                clab = _label_for(r, col_gb)
                if clab not in col_index:
                    col_index[clab] = len(col_labels)
                    col_labels.append(clab)
                if rlab not in rows_map:
                    rows_map[rlab] = []
                # ensure row list size
                while len(rows_map[rlab]) < len(col_labels):
                    rows_map[rlab].append(0)
                val = (r.get('__count') if use_count else (r.get(f"{measure}_sum") or r.get(measure) or 0)) or 0
                rows_map[rlab][col_index[clab]] = val
            # ensure all rows have full width
            for rlab, vals in rows_map.items():
                if len(vals) < len(col_labels):
                    vals.extend([0] * (len(col_labels) - len(vals)))
            # build rows list
            rows = [{'row': rlab, 'values': vals} for rlab, vals in rows_map.items()]
            # sort columns by label for stability
            columns = [{'key': i, 'label': lbl} for i, lbl in enumerate(col_labels)]
            return {
                'type': 'pivot',
                'data': {
                    'columns': columns,
                    'rows': rows,
                },
            }

        # 1D pivot (lignes uniquement)
        data_rows = []
        if row_gb:
            try:
                results = model.read_group(domain, fields=fields or ["__count"], groupby=[row_gb], lazy=False)
                for r in results:
                    full = (row_gb or '')
                    base = full.split(':')[0]
                    label = r.get(f"{full}_name") or r.get(f"{base}_name") or r.get(full) or r.get(base) or 'Indéfini'
                    value = (r.get('__count') if use_count else (r.get(f"{measure}_sum") or r.get(measure))) or 0
                    data_rows.append({'row': label, 'value': value})
            except Exception:
                pass

        if not data_rows:
            # Retourner un total cohérent (sum de measure si défini, sinon count)
            total_value = None
            if not use_count:
                try:
                    res = model.read_group(domain, fields=[f"{measure}:sum"], groupby=[], lazy=False)
                    if res and isinstance(res, list):
                        total_value = res[0].get(f"{measure}_sum") or 0
                except Exception:
                    total_value = None
            if total_value is None:
                total_value = model.search_count(domain)
            data_rows = [{'row': 'Total', 'value': total_value}]

        _logger.debug("[TDB] pivot rows=%s", len(data_rows))
        return {
            'type': 'pivot',
            'data': data_rows,
        }

    def _get_fields_from_view(self, model, view_type, view_id=None):
        """Récupère les champs et leurs libellés depuis la vue list/tree.
        Essaie d'abord 'list', puis 'tree' si nécessaire. Supporte un view_id explicite.
        """
        try:
            vt_primary = 'list' if view_type in ('tree', 'list') else view_type
            vt_fallback = 'tree' if vt_primary == 'list' else 'list'

            def _extract(view_res):
                arch = view_res.get('arch', '')
                fields_def = view_res.get('fields', {})
                names = []
                if arch:
                    root = etree.fromstring(arch.encode('utf-8')) if isinstance(arch, str) else etree.fromstring(arch)
                    for node in root.xpath('//list/field | //tree/field'):
                        name = node.get('name')
                        if name and name not in names:
                            if node.get('invisible') in ('1', 'True', 'true'):
                                continue
                            names.append(name)
                return names, fields_def

            view = model.fields_view_get(view_id=view_id, view_type=vt_primary)
            field_names, fields_def = _extract(view)

            if not field_names:
                view2 = model.fields_view_get(view_type=vt_fallback)
                field_names, fields_def = _extract(view2)

            if len(field_names) <= 1:
                View = request.env['ir.ui.view'].sudo()
                candidates = View.search([
                    ('model', '=', model._name),
                    ('type', 'in', ['list', 'tree'])
                ], order='priority, id')
                for v in candidates:
                    try:
                        vt = v.type or 'list'
                        vres = model.fields_view_get(view_id=v.id, view_type=vt)
                        fn, fd = _extract(vres)
                        if len(fn) > 1:
                            field_names, fields_def = fn, fd
                            break
                    except Exception:
                        continue

            if not field_names:
                # essayer une liste de champs usuels fréquents
                preference = [
                    'name', 'display_name', 'date', 'invoice_date', 'create_date', 'write_date', 'ref',
                    'partner_id', 'user_id', 'company_id', 'state', 'amount_total', 'amount_untaxed', 'amount_tax',
                ]
                # filtrer par champs existants côté modèle
                field_names = [f for f in preference if f in model._fields]
                if not field_names:
                    # fallback générique: prendre quelques champs non x2many/binary
                    for fname, fdef in model._fields.items():
                        t = getattr(fdef, 'type', '')
                        if t in ('one2many', 'many2many', 'binary'):
                            continue
                        field_names.append(fname)
                        if len(field_names) >= 6:
                            break

            field_names = field_names[:8]
            labels = {fn: fields_def.get(fn, {}).get('string', fn) for fn in field_names}
            return field_names, labels
        except Exception:
            return ['display_name'], {'display_name': 'Nom à afficher'}
