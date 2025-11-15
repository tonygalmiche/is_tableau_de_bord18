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
                    # Remplacer null par None pour que ast.literal_eval fonctionne
                    context_str = filter_obj.context.replace('null', 'None').replace('true', 'True').replace('false', 'False')
                    context = ast.literal_eval(context_str)
                except Exception as e:
                    _logger.warning("[TDB] Erreur parsing contexte du filtre: %s - context: %s", e, filter_obj.context)
                    context = {}

            # Fusionner avec le contexte actuel
            ctx = dict(request.env.context)
            # Conserver les informations importantes du contexte du filtre AVANT d'ajouter celles de la ligne
            if context:
                _logger.info("[TDB] Contexte du filtre à fusionner: %s", context)
                ctx.update(context)
            
            # Ajouter le line_id au contexte pour qu'il soit accessible dans _get_list_data
            if line_id:
                ctx['line_id'] = line_id

            # Appliquer overrides éventuels de la ligne (sur ctx)
            # Ces overrides peuvent SURCHARGER le contexte du filtre si définis dans la ligne
            if line_id:
                try:
                    line = request.env['is.tableau.de.bord.line'].browse(int(line_id))
                    if line and line.exists():
                        if line.display_mode and line.display_mode != 'auto':
                            ctx['search_default_view_type'] = line.display_mode
                        # Seulement surcharger si la ligne a des valeurs définies
                        if line.graph_chart_type:
                            ctx['graph_chart_type'] = line.graph_chart_type
                        if line.graph_aggregator:
                            ctx['graph_aggregator'] = line.graph_aggregator
                        if line.graph_measure:
                            ctx['graph_measure'] = line.graph_measure
                        if line.graph_groupbys:
                            ctx['graph_groupbys'] = line.graph_groupbys
                        if line.pivot_row_groupby:
                            # Convertir la chaîne en liste si nécessaire
                            ctx['pivot_row_groupby'] = [g.strip() for g in line.pivot_row_groupby.split(',')] if ',' in line.pivot_row_groupby else [line.pivot_row_groupby]
                            _logger.info("[TDB DEBUG CTRL] pivot_row_groupby de la ligne: %s -> ctx: %s", line.pivot_row_groupby, ctx['pivot_row_groupby'])
                        if line.pivot_col_groupby:
                            # Convertir la chaîne en liste si nécessaire
                            ctx['pivot_column_groupby'] = [g.strip() for g in line.pivot_col_groupby.split(',')] if ',' in line.pivot_col_groupby else [line.pivot_col_groupby]
                            _logger.info("[TDB DEBUG CTRL] pivot_col_groupby de la ligne: %s -> ctx pivot_column_groupby: %s", line.pivot_col_groupby, ctx['pivot_column_groupby'])
                        else:
                            _logger.warning("[TDB DEBUG CTRL] line.pivot_col_groupby est VIDE ou False!")
                        if line.pivot_measure:
                            # Convertir la chaîne en liste si nécessaire
                            ctx['pivot_measures'] = [g.strip() for g in line.pivot_measure.split(',')] if ',' in line.pivot_measure else [line.pivot_measure]
                            _logger.info("[TDB DEBUG CTRL] pivot_measure de la ligne: %s -> ctx: %s", line.pivot_measure, ctx['pivot_measures'])
                        # Ajouter les paramètres de tri
                        if line.pivot_sort_by:
                            ctx['pivot_sort_by'] = line.pivot_sort_by
                        if line.pivot_sort_order:
                            ctx['pivot_sort_order'] = line.pivot_sort_order
                        _logger.info("[TDB] Overrides depuis la ligne appliqués: graph_measure=%s graph_groupbys=%s", 
                                   line.graph_measure, line.graph_groupbys)
                except Exception as e:
                    _logger.exception("[TDB] Erreur application overrides ligne: %s", e)

            # Appliquer aussi d'éventuels overrides envoyés côté client (sécurisé au scope utilisateur)
            if isinstance(overrides, dict):
                safe_keys = {
                    'search_default_view_type', 'graph_chart_type', 'graph_aggregator',
                    'pivot_row_groupby', 'pivot_column_groupby', 'pivot_measures',
                    'pivot_sort_by', 'pivot_sort_order',
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
        # Priorité 1: display_mode explicite (depuis la ligne du tableau de bord)
        if 'search_default_view_type' in context:
            view_type = context.get('search_default_view_type', '')
            if 'graph' in view_type:
                return 'graph'
            if 'pivot' in view_type:
                return 'pivot'
            if 'list' in view_type:
                return 'list'
        
        # Priorité 2: paramètres spécifiques au type de vue
        if context.get('graph_measure') or context.get('graph_groupbys'):
            return 'graph'
        if context.get('pivot_measures') or context.get('pivot_row_groupby') or context.get('pivot_column_groupby'):
            return 'pivot'
        
        # Par défaut: liste
        return 'list'

    def _get_list_data(self, model, filter_obj, domain, context):
        """Génère les données pour une vue liste"""
        # 1) Priorité 1: Champs configurés dans la ligne du tableau de bord (field_ids)
        line_id = context.get('line_id')
        explicit_fields = []
        field_labels = {}
        
        if line_id:
            try:
                line = request.env['is.tableau.de.bord.line'].browse(int(line_id))
                if line and line.exists() and line.field_ids:
                    # Récupérer uniquement les champs visibles
                    visible_fields = line.field_ids.filtered(lambda f: f.visible).sorted('sequence')
                    _logger.info("[TDB] Found %s visible fields in line configuration", len(visible_fields))
                    
                    # Maintenant field_name contient le nom technique et field_label le libellé
                    for field_config in visible_fields:
                        field_name = field_config.field_name
                        field_label = field_config.field_label or field_name
                        
                        # Vérifier que le champ existe dans le modèle
                        if field_name and field_name in model._fields:
                            explicit_fields.append(field_name)
                            field_labels[field_name] = field_label
                    
                    _logger.info("[TDB] Mapped fields from line config: %s", explicit_fields)
            except Exception as e:
                _logger.exception("[TDB] Error loading field_ids from line: %s", e)
        
        # 2) Champs explicitement définis dans le favori (list_fields)
        if not explicit_fields and context.get('list_fields'):
            lf = context.get('list_fields')
            if isinstance(lf, str):
                # accepter "a,b,c"
                explicit_fields = [f.strip() for f in lf.split(',') if f.strip()]
            elif isinstance(lf, (list, tuple)):
                explicit_fields = [str(f).strip() for f in lf if str(f).strip()]
            # ne garder que les champs existants
            explicit_fields = [f for f in explicit_fields if f in model._fields]
            if explicit_fields:
                fields_def = model.fields_get(explicit_fields)
                field_labels = {f: fields_def.get(f, {}).get('string', f) for f in explicit_fields}

        view_id = None
        xmlid = context.get('tree_view_ref') or context.get('list_view_ref')
        if xmlid:
            try:
                view_id = request.env.ref(xmlid).id
            except Exception:
                view_id = None

        if explicit_fields:
            # libellés depuis fields_get
            if not field_labels:
                fields_def = model.fields_get(explicit_fields)
                field_labels = {f: fields_def.get(f, {}).get('string', f) for f in explicit_fields}
            fields_to_display = explicit_fields
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
        _logger.info("[TDB GRAPH] >>> Contexte complet: %s", context)
        _logger.info("[TDB GRAPH] >>> groupbys brut: %s (type: %s)", groupbys, type(groupbys))
        
        if isinstance(groupbys, str):
            # Si c'est une chaîne séparée par des virgules, on split
            if ',' in groupbys:
                groupbys = [g.strip() for g in groupbys.split(',')]
            else:
                groupbys = [groupbys]
        
        _logger.info("[TDB GRAPH] >>> groupbys après traitement: %s", groupbys)
        
        measure = context.get('graph_measure') or context.get('measure')
        aggregator = context.get('graph_aggregator') or 'sum'
        chart_type = context.get('graph_chart_type') or 'bar'
        _logger.info("[TDB GRAPH] >>> measure=%s agg=%s chart_type=%s", measure, aggregator, chart_type)

        agg_label = "Nombre d'enregistrements"
        use_count = not measure or str(measure) in ('count', '__count')
        fields = [] if use_count else [f"{measure}:{aggregator}"]
        _logger.info("[TDB GRAPH] >>> use_count=%s fields=%s", use_count, fields)
        
        if not use_count:
            agg_label = f"{aggregator} de {measure}"

        try:
            _logger.info("[TDB GRAPH] >>> Appel read_group avec domain=%s fields=%s groupby=%s", domain, fields, groupbys)
            results = model.read_group(domain, fields=fields, groupby=groupbys, lazy=False)
            _logger.info("[TDB GRAPH] >>> read_group retourne %s résultats", len(results))
            for i, r in enumerate(results):
                _logger.info("[TDB GRAPH] >>> Résultat %s: %s", i, r)
        except Exception as e:
            _logger.exception("[TDB GRAPH] >>> Erreur read_group: %s", e)
            results = []

        labels = []
        values = []
        if results:
            for r in results:
                label_parts = []
                for gb in groupbys:
                    base = gb.split(':')[0]
                    val = r.get(gb) or r.get(base) or r.get(f"{gb}_name") or r.get(f"{base}_name")
                    _logger.info("[TDB GRAPH] >>> Extraction label pour groupby=%s: base=%s val=%s", gb, base, val)
                    label_parts.append(str(val) if val is not None else '')
                label = " / ".join([p for p in label_parts if p])
                labels.append(label)
                
                if use_count:
                    value = r.get("__count") or 0
                else:
                    value = r.get(f"{measure}_{aggregator}") or r.get(measure) or 0
                values.append(value)
                _logger.info("[TDB GRAPH] >>> Label: %s -> Valeur: %s", label, value)
        else:
            _logger.info("[TDB GRAPH] >>> Pas de résultats, utilisation du count total")
            labels = ['Total']
            values = [model.search_count(domain)]

        _logger.info("[TDB GRAPH] >>> Labels finaux: %s", labels)
        _logger.info("[TDB GRAPH] >>> Valeurs finales: %s", values)

        # Ajuster la palette à la longueur
        palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        bg = [palette[i % len(palette)] for i in range(len(values))]

        result = {
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
        
        _logger.info("[TDB GRAPH] >>> Résultat final: %s", result)
        return result

    def _get_pivot_data(self, model, filter_obj, domain, context):
        """Génère les données pour un tableau croisé; support 1D (lignes) et 2D (lignes x colonnes).
        Utilise les informations du contexte du filtre pour respecter les paramètres de la vue pivot standard."""
        
        # Récupérer les groupements et mesures depuis le contexte (priorité au contexte du filtre)
        row_gb = context.get('pivot_row_groupby') or context.get('graph_groupbys') or context.get('group_by')
        if isinstance(row_gb, list):
            row_gb = row_gb[0] if row_gb else None
        
        col_gb = context.get('pivot_column_groupby')
        _logger.info("[TDB DEBUG PIVOT] pivot_column_groupby brut du context: %s (type: %s)", col_gb, type(col_gb))
        if isinstance(col_gb, list):
            col_gb = col_gb[0] if col_gb else None
        _logger.info("[TDB DEBUG PIVOT] col_gb après traitement: %s", col_gb)
        
        # Pour la mesure, utiliser graph_measure du contexte si pivot_measures n'est pas défini
        measures = context.get('pivot_measures') or context.get('graph_measure') or context.get('measure')
        if isinstance(measures, list):
            measure = measures[0] if measures else None
        else:
            measure = measures
        
        _logger.info("[TDB] pivot row_gb=%s col_gb=%s measure=%s context_keys=%s", 
                     row_gb, col_gb, measure, list(context.keys()))

        use_count = not measure or str(measure) in ('count', '__count')
        fields = [] if use_count else [f"{measure}:sum"]
        
        # Récupérer le libellé de la mesure
        measure_label = "Nombre"
        if measure and measure not in ('count', '__count'):
            try:
                field_info = model.fields_get([measure])
                measure_label = field_info.get(measure, {}).get('string', measure)
            except Exception:
                measure_label = measure
        
        # Récupérer les libellés des groupements
        row_label = "Lignes"
        col_label = "Colonnes"
        if row_gb:
            try:
                row_field = row_gb.split(':')[0]
                field_info = model.fields_get([row_field])
                row_label = field_info.get(row_field, {}).get('string', row_field)
            except Exception:
                row_label = row_gb
        if col_gb:
            try:
                col_field = col_gb.split(':')[0]
                field_info = model.fields_get([col_field])
                col_label = field_info.get(col_field, {}).get('string', col_field)
            except Exception:
                col_label = col_gb

        if row_gb and col_gb:
            # 2D pivot
            try:
                results = model.read_group(domain, fields=fields or ["__count"], groupby=[row_gb, col_gb], lazy=False)
            except Exception:
                results = []
            
            # Récupérer les informations des champs pour gérer les Selection
            row_field_name = row_gb.split(':')[0]
            col_field_name = col_gb.split(':')[0]
            
            # Récupérer les définitions de champs
            fields_info = model.fields_get([row_field_name, col_field_name])
            row_field_info = fields_info.get(row_field_name, {})
            col_field_info = fields_info.get(col_field_name, {})
            
            # Créer des dictionnaires de mapping pour les Selection
            row_selection_map = {}
            col_selection_map = {}
            
            if row_field_info.get('type') == 'selection' and row_field_info.get('selection'):
                row_selection_map = dict(row_field_info['selection'])
            
            if col_field_info.get('type') == 'selection' and col_field_info.get('selection'):
                col_selection_map = dict(col_field_info['selection'])
            
            _logger.info("[TDB DEBUG] col_field_info: %s", col_field_info)
            _logger.info("[TDB DEBUG] col_selection_map: %s", col_selection_map)
            
            # collect columns
            col_labels = []
            col_index = {}
            def _label_for(rec, gb, selection_map=None):
                full = (gb or '')
                base = full.split(':')[0]
                # tenter d'abord la clé complète (utile pour date gb: field:year)
                val = rec.get(full) or rec.get(base)
                # Pour les many2one, prendre le display_name
                if isinstance(val, (list, tuple)) and len(val) > 1:
                    return val[1]  # [id, display_name]
                # Pour les Selection, chercher le libellé
                if selection_map and val in selection_map:
                    return selection_map[val]
                # Pour les dates avec groupement temporel
                if rec.get(f"{base}") and ':' in full:
                    return str(val) if val else 'Indéfini'
                return str(val) if val is not None else 'Indéfini'
            # build rows structure
            rows_map = {}
            for r in results:
                rlab = _label_for(r, row_gb, row_selection_map)
                clab = _label_for(r, col_gb, col_selection_map)
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
            
            # Appliquer le tri selon les paramètres
            sort_by = context.get('pivot_sort_by', 'row')
            sort_order = context.get('pivot_sort_order', 'asc')
            reverse = (sort_order == 'desc')
            
            _logger.info("[TDB PIVOT SORT] Avant tri: %s lignes, sort_by=%s, sort_order=%s, reverse=%s", 
                        len(rows), sort_by, sort_order, reverse)
            _logger.info("[TDB PIVOT SORT] Lignes avant tri: %s", [(r['row'], sum(r['values'])) for r in rows[:5]])
            
            if sort_by == 'total':
                # Trier par le total de chaque ligne
                rows.sort(key=lambda r: sum(r['values']), reverse=reverse)
            else:
                # Trier par le libellé de la ligne
                # Essayer d'abord un tri numérique, sinon alphabétique
                def sort_key(r):
                    label = r['row']
                    if label is None:
                        return (1, '')  # Les None à la fin
                    # Essayer de convertir en nombre pour tri numérique
                    try:
                        return (0, float(str(label).replace(',', '.').replace(' ', '')))
                    except (ValueError, AttributeError):
                        # Si ce n'est pas un nombre, tri alphabétique insensible à la casse
                        return (1, str(label).lower())
                
                rows.sort(key=sort_key, reverse=reverse)
            
            _logger.info("[TDB PIVOT SORT] Lignes après tri: %s", [(r['row'], sum(r['values'])) for r in rows[:5]])
            
            # sort columns by label for stability
            columns = [{'key': i, 'label': lbl} for i, lbl in enumerate(col_labels)]
            return {
                'type': 'pivot',
                'data': {
                    'columns': columns,
                    'rows': rows,
                    'measure_label': measure_label,
                    'row_label': row_label,
                    'col_label': col_label,
                },
            }

        # 1D pivot (lignes uniquement)
        data_rows = []
        if row_gb:
            # Récupérer les informations du champ pour gérer les Selection
            row_field_name = row_gb.split(':')[0]
            fields_info = model.fields_get([row_field_name])
            row_field_info = fields_info.get(row_field_name, {})
            
            # Créer un dictionnaire de mapping pour les Selection
            row_selection_map = {}
            if row_field_info.get('type') == 'selection' and row_field_info.get('selection'):
                row_selection_map = dict(row_field_info['selection'])
            
            try:
                results = model.read_group(domain, fields=fields or ["__count"], groupby=[row_gb], lazy=False)
                for r in results:
                    full = (row_gb or '')
                    base = full.split(':')[0]
                    val = r.get(full) or r.get(base)
                    # Pour les many2one, prendre le display_name
                    if isinstance(val, (list, tuple)) and len(val) > 1:
                        label = val[1]  # [id, display_name]
                    # Pour les Selection, chercher le libellé
                    elif row_selection_map and val in row_selection_map:
                        label = row_selection_map[val]
                    else:
                        label = str(val) if val is not None else 'Indéfini'
                    value = (r.get('__count') if use_count else (r.get(f"{measure}_sum") or r.get(measure))) or 0
                    data_rows.append({'row': label, 'value': value})
            except Exception as e:
                _logger.exception("[TDB] Error in 1D pivot: %s", e)

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
        else:
            # Appliquer le tri selon les paramètres (sauf si c'est juste le total)
            sort_by = context.get('pivot_sort_by', 'row')
            sort_order = context.get('pivot_sort_order', 'asc')
            reverse = (sort_order == 'desc')
            
            _logger.info("[TDB PIVOT 1D SORT] Avant tri: %s lignes, sort_by=%s, sort_order=%s, reverse=%s", 
                        len(data_rows), sort_by, sort_order, reverse)
            _logger.info("[TDB PIVOT 1D SORT] Lignes avant tri: %s", [(r['row'], r['value']) for r in data_rows[:5]])
            
            if sort_by == 'total':
                # Trier par la valeur
                data_rows.sort(key=lambda r: r['value'], reverse=reverse)
            else:
                # Trier par le libellé de la ligne
                # Essayer d'abord un tri numérique, sinon alphabétique
                def sort_key(r):
                    label = r['row']
                    if label is None:
                        return (1, '')  # Les None à la fin
                    # Essayer de convertir en nombre pour tri numérique
                    try:
                        return (0, float(str(label).replace(',', '.').replace(' ', '')))
                    except (ValueError, AttributeError):
                        # Si ce n'est pas un nombre, tri alphabétique insensible à la casse
                        return (1, str(label).lower())
                
                data_rows.sort(key=sort_key, reverse=reverse)
            
            _logger.info("[TDB PIVOT 1D SORT] Lignes après tri: %s", [(r['row'], r['value']) for r in data_rows[:5]])

        _logger.debug("[TDB] pivot rows=%s", len(data_rows))
        return {
            'type': 'pivot',
            'data': data_rows,
            'measure_label': measure_label,
            'row_label': row_label,
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
                            # Ne pas filtrer les champs invisibles - on veut toutes les colonnes
                            # if node.get('invisible') in ('1', 'True', 'true'):
                            #     continue
                            names.append(name)
                return names, fields_def

            _logger.info("[TDB] Getting fields for model=%s view_type=%s view_id=%s", model._name, vt_primary, view_id)
            
            # Vérifier si le modèle a la méthode fields_view_get
            if hasattr(model, 'fields_view_get'):
                view = model.fields_view_get(view_id=view_id, view_type=vt_primary)
                field_names, fields_def = _extract(view)
                _logger.info("[TDB] Primary view extraction: %s fields", len(field_names))

                if not field_names:
                    _logger.info("[TDB] Trying fallback view type: %s", vt_fallback)
                    view2 = model.fields_view_get(view_type=vt_fallback)
                    field_names, fields_def = _extract(view2)
                    _logger.info("[TDB] Fallback view extraction: %s fields", len(field_names))

                if len(field_names) <= 1:
                    _logger.info("[TDB] Searching for alternative views in ir.ui.view")
                    View = request.env['ir.ui.view'].sudo()
                    candidates = View.search([
                        ('model', '=', model._name),
                        ('type', 'in', ['list', 'tree'])
                    ], order='priority, id')
                    _logger.info("[TDB] Found %s candidate views", len(candidates))
                    for v in candidates:
                        try:
                            vt = v.type or 'list'
                            vres = model.fields_view_get(view_id=v.id, view_type=vt)
                            fn, fd = _extract(vres)
                            if len(fn) > 1:
                                field_names, fields_def = fn, fd
                                _logger.info("[TDB] Using alternative view %s with %s fields", v.id, len(fn))
                                break
                        except Exception as e:
                            _logger.debug("[TDB] Failed to load view %s: %s", v.id, e)
                            continue
            else:
                _logger.info("[TDB] Model %s has no fields_view_get method, using fields directly", model._name)
                field_names = []
                fields_def = {}

            if not field_names:
                _logger.warning("[TDB] No fields found in views, using model fields directly")
                # Récupérer tous les champs du modèle (sauf relations complexes et binaires)
                field_names = []
                for fname, fdef in model._fields.items():
                    t = getattr(fdef, 'type', '')
                    # Exclure les champs techniques et complexes
                    if fname.startswith('_'):
                        continue
                    if t in ('one2many', 'many2many', 'binary'):
                        continue
                    # Inclure les champs standards
                    field_names.append(fname)
                
                # Limiter à 15 champs pour ne pas surcharger l'affichage
                if len(field_names) > 15:
                    # Préférer certains champs communs
                    preference = [
                        'name', 'display_name', 'date', 'invoice_date', 'partner_id', 'amount_total', 
                        'amount_untaxed', 'amount_tax', 'user_id', 'company_id', 'state', 'ref',
                        'create_date', 'write_date'
                    ]
                    preferred = [f for f in preference if f in field_names]
                    others = [f for f in field_names if f not in preference]
                    field_names = preferred + others[:15-len(preferred)]
                
                # Récupérer les définitions des champs
                fields_def = model.fields_get(field_names)

            # Ne pas limiter le nombre de champs pour afficher toutes les colonnes de la vue
            _logger.info("[TDB] Final field list: %s fields - %s", len(field_names), field_names[:10])
            labels = {fn: fields_def.get(fn, {}).get('string', fn) for fn in field_names}
            return field_names, labels
        except Exception as e:
            _logger.exception("[TDB] Error in _get_fields_from_view: %s", e)
            return ['display_name'], {'display_name': 'Nom à afficher'}
