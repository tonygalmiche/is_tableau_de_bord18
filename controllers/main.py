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
                    context = {}

            # Fusionner avec le contexte actuel
            ctx = dict(request.env.context)
            # Conserver les informations importantes du contexte du filtre AVANT d'ajouter celles de la ligne
            if context:
                ctx.update(context)
            
            # Ajouter le line_id au contexte pour qu'il soit accessible dans _get_list_data
            if line_id:
                ctx['line_id'] = line_id

            # Récupérer la ligne pour accéder à ses paramètres (notamment limit)
            line = None
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
                        # Toujours passer graph_show_legend (avec valeur par défaut True)
                        ctx['graph_show_legend'] = line.graph_show_legend if hasattr(line, 'graph_show_legend') else True
                        if line.pivot_row_groupby:
                            # Convertir la chaîne en liste si nécessaire
                            ctx['pivot_row_groupby'] = [g.strip() for g in line.pivot_row_groupby.split(',')] if ',' in line.pivot_row_groupby else [line.pivot_row_groupby]
                        if line.pivot_col_groupby:
                            # Convertir la chaîne en liste si nécessaire
                            ctx['pivot_column_groupby'] = [g.strip() for g in line.pivot_col_groupby.split(',')] if ',' in line.pivot_col_groupby else [line.pivot_col_groupby]
                        if line.pivot_measure:
                            # Convertir la chaîne en liste si nécessaire
                            ctx['pivot_measures'] = [g.strip() for g in line.pivot_measure.split(',')] if ',' in line.pivot_measure else [line.pivot_measure]
                        # Ajouter les paramètres de tri
                        if line.pivot_sort_by:
                            ctx['pivot_sort_by'] = line.pivot_sort_by
                        if line.pivot_sort_order:
                            ctx['pivot_sort_order'] = line.pivot_sort_order
                        # Ajouter les paramètres d'affichage des totaux
                        if hasattr(line, 'pivot_show_row_totals'):
                            ctx['pivot_show_row_totals'] = line.pivot_show_row_totals
                        if hasattr(line, 'pivot_show_col_totals'):
                            ctx['pivot_show_col_totals'] = line.pivot_show_col_totals
                except Exception:
                    pass

            # Appliquer aussi d'éventuels overrides envoyés côté client (sécurisé au scope utilisateur)
            if isinstance(overrides, dict):
                safe_keys = {
                    'search_default_view_type', 'graph_chart_type', 'graph_aggregator', 'graph_show_legend', 'show_data_title', 'show_record_count',
                    'pivot_row_groupby', 'pivot_column_groupby', 'pivot_measures',
                    'pivot_sort_by', 'pivot_sort_order',
                    'graph_groupbys', 'graph_measure', 'list_fields', 'measure', 'group_by'
                }
                for k, v in overrides.items():
                    if k in ('display_mode',):
                        ctx['search_default_view_type'] = v
                    elif k in safe_keys:
                        ctx[k] = v

            # Déterminer le type de vue à utiliser
            view_type = self._get_view_type_from_context(ctx)

            model = model.with_context(ctx)
            if view_type == 'graph':
                return self._get_graph_data(model, filter_obj, domain, ctx, line)
            elif view_type == 'pivot':
                return self._get_pivot_data(model, filter_obj, domain, ctx, line)
            else:
                return self._get_list_data(model, filter_obj, domain, ctx, line)

        except Exception:
            return {'error': 'Une erreur s\'est produite'}

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

    def _get_list_data(self, model, filter_obj, domain, context, line=None):
        """Génère les données pour une vue liste"""
        # Déterminer la limite et show_record_count
        limit = 50  # Valeur par défaut
        show_record_count = context.get('show_record_count', True)
        
        if line and hasattr(line, 'limit') and line.limit > 0:
            limit = line.limit
        if line and hasattr(line, 'show_record_count'):
            show_record_count = line.show_record_count
        
        # 1) Priorité 1: Champs configurés dans la ligne du tableau de bord (field_ids)
        line_id = context.get('line_id')
        explicit_fields = []
        field_labels = {}
        order_string = None  # Chaîne de tri pour search()
        
        if line_id:
            try:
                line = request.env['is.tableau.de.bord.line'].browse(int(line_id))
                if line and line.exists() and line.field_ids:
                    # Récupérer uniquement les champs visibles
                    visible_fields = line.field_ids.filtered(lambda f: f.visible).sorted('sequence')
                    
                    # Récupérer les champs avec ordre de tri (sort_order > 0)
                    sort_fields = line.field_ids.filtered(lambda f: f.sort_order > 0).sorted('sort_order')
                    
                    if sort_fields:
                        # Construire la chaîne de tri : "field1 asc, field2 desc, ..."
                        order_parts = []
                        for field_config in sort_fields:
                            field_name = field_config.field_name
                            direction = field_config.sort_direction or 'asc'
                            if field_name and field_name in model._fields:
                                order_parts.append(f"{field_name} {direction}")
                        if order_parts:
                            order_string = ', '.join(order_parts)
                    
                    # Maintenant field_name contient le nom technique et field_label le libellé
                    for field_config in visible_fields:
                        field_name = field_config.field_name
                        field_label = field_config.field_label or field_name
                        
                        # Vérifier que le champ existe dans le modèle
                        if field_name and field_name in model._fields:
                            explicit_fields.append(field_name)
                            field_labels[field_name] = field_label
                    
            except Exception:
                pass
        
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

        # Appliquer le tri si défini
        if order_string:
            recs = model.search(domain, limit=limit, order=order_string)
        else:
            recs = model.search(domain, limit=limit)
            
        data = recs.read(fields_to_display) if recs else []

        fields_meta = [{'name': f, 'string': field_labels.get(f, f)} for f in fields_to_display]

        result = {
            'type': 'list',
            'data': data,
            'fields': fields_meta,
            'model': filter_obj.model_id,
        }
        
        # Ajouter le compteur seulement si show_record_count est True
        if show_record_count:
            result['count'] = model.search_count(domain)
            result['show_record_count'] = True
        else:
            result['show_record_count'] = False
        
        return result

    def _get_graph_data(self, model, filter_obj, domain, context, line=None):
        """Génère les données pour un graphique simple"""
        # Déterminer la limite et le tri (depuis line ou contexte)
        limit = None
        sort_by = context.get('pivot_sort_by', 'row')  # Par défaut tri par libellé
        sort_order = context.get('pivot_sort_order', 'asc')
        
        if line and hasattr(line, 'limit') and line.limit > 0:
            limit = line.limit
        if line and hasattr(line, 'pivot_sort_by') and line.pivot_sort_by:
            sort_by = line.pivot_sort_by  # 'row' = tri par libellé, 'total' = tri par valeur
        if line and hasattr(line, 'pivot_sort_order') and line.pivot_sort_order:
            sort_order = line.pivot_sort_order
        
        groupbys = context.get('graph_groupbys') or context.get('group_by') or []
        
        if isinstance(groupbys, str):
            # Si c'est une chaîne séparée par des virgules, on split
            if ',' in groupbys:
                groupbys = [g.strip() for g in groupbys.split(',')]
            else:
                groupbys = [groupbys]
        
        measure = context.get('graph_measure') or context.get('measure')
        aggregator = context.get('graph_aggregator') or 'sum'
        chart_type = context.get('graph_chart_type') or 'bar'
        show_legend = context.get('graph_show_legend', True)
        show_data_title = context.get('show_data_title', True)

        agg_label = "Nombre d'enregistrements"
        use_count = not measure or str(measure) in ('count', '__count')
        fields = [] if use_count else [f"{measure}:{aggregator}"]
        
        if not use_count:
            # Traduire l'agrégateur
            agg_translations = {
                'sum': 'Somme',
                'avg': 'Moyenne',
                'max': 'Maximum',
                'min': 'Minimum',
                'count': 'Nombre',
            }
            agg_french = agg_translations.get(aggregator, aggregator)
            
            # Récupérer le nom traduit du champ
            measure_field_name = measure
            try:
                field_info = model.fields_get([measure])
                measure_field_name = field_info.get(measure, {}).get('string', measure)
            except Exception:
                pass
            
            agg_label = f"{agg_french} de {measure_field_name}"

        try:
            # NE PAS appliquer limit dans read_group (on le fera après le tri)
            results = model.read_group(domain, fields=fields, groupby=groupbys, lazy=False)
        except Exception:
            results = []

        # Construire les labels et valeurs
        data_list = []
        if results:
            for r in results:
                label_parts = []
                for gb in groupbys:
                    base = gb.split(':')[0]
                    val = r.get(gb) or r.get(base) or r.get(f"{gb}_name") or r.get(f"{base}_name")
                    label_parts.append(str(val) if val is not None else '')
                label = " / ".join([p for p in label_parts if p])
                
                if use_count:
                    value = r.get("__count") or 0
                else:
                    value = r.get(f"{measure}_{aggregator}") or r.get(measure) or 0
                
                data_list.append({'label': label, 'value': value})
        else:
            total_count = model.search_count(domain)
            data_list = [{'label': 'Total', 'value': total_count}]

        # Appliquer le tri et la limite
        if sort_by == 'total':
            # Tri par valeur
            reverse = (sort_order == 'desc')
            data_list.sort(key=lambda x: x['value'], reverse=reverse)
        else:
            # Tri par libellé (smart key)
            reverse = (sort_order == 'desc')
            data_list.sort(key=lambda x: self._sort_key_smart(x['label']), reverse=reverse)
        
        # Appliquer la limite après le tri
        if limit and limit > 0:
            data_list = data_list[:limit]
        
        # Extraire les labels et valeurs triés/limités
        labels = [item['label'] for item in data_list]
        values = [item['value'] for item in data_list]

        # Ajuster la palette à la longueur
        palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        bg = [palette[i % len(palette)] for i in range(len(values))]

        result = {
            'type': 'graph',
            'chart_type': chart_type,
            'show_legend': show_legend,
            'show_data_title': show_data_title,
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': agg_label,
                    'data': values,
                    'backgroundColor': bg
                }]
            }
        }
        
        return result

    def _get_selection_map(self, model, field_name):
        """Récupère le mapping pour un champ Selection"""
        try:
            fields_info = model.fields_get([field_name])
            field_info = fields_info.get(field_name, {})
            if field_info.get('type') == 'selection' and field_info.get('selection'):
                return dict(field_info['selection'])
        except Exception:
            pass
        return {}

    def _extract_label_from_record(self, record, groupby, selection_map=None):
        """Extrait le libellé d'un enregistrement read_group pour un groupby donné"""
        full = (groupby or '')
        base = full.split(':')[0]
        # Tenter d'abord la clé complète (utile pour date groupby: field:year)
        val = record.get(full) or record.get(base)
        
        # Pour les many2one, prendre le display_name
        if isinstance(val, (list, tuple)) and len(val) > 1:
            return val[1]  # [id, display_name]
        
        # Pour les Selection, chercher le libellé
        if selection_map and val in selection_map:
            return selection_map[val]
        
        # Pour les dates avec groupement temporel
        if record.get(f"{base}") and ':' in full:
            return str(val) if val else 'Indéfini'
        
        return str(val) if val is not None else 'Indéfini'

    def _sort_key_smart(self, label):
        """Génère une clé de tri intelligente (numérique si possible, sinon alphabétique)"""
        if label is None:
            return (1, '')  # Les None à la fin
        # Essayer de convertir en nombre pour tri numérique
        try:
            return (0, float(str(label).replace(',', '.').replace(' ', '')))
        except (ValueError, AttributeError):
            # Si ce n'est pas un nombre, tri alphabétique insensible à la casse
            return (1, str(label).lower())

    def _sort_and_limit_rows(self, rows, context, limit, is_2d=False):
        """Trie et limite les lignes selon les paramètres du contexte
        
        Args:
            rows: Liste de dict avec clé 'row' (et 'value' pour 1D ou 'values' pour 2D)
            context: Contexte contenant pivot_sort_by et pivot_sort_order
            limit: Nombre max de lignes à retourner (None = pas de limite)
            is_2d: True pour pivot 2D (avec 'values'), False pour 1D (avec 'value')
        
        Returns:
            Liste triée et limitée
        """
        sort_by = context.get('pivot_sort_by', 'row')
        sort_order = context.get('pivot_sort_order', 'asc')
        reverse = (sort_order == 'desc')
        
        if sort_by == 'total':
            # Trier par le total
            if is_2d:
                rows.sort(key=lambda r: sum(r['values']), reverse=reverse)
            else:
                rows.sort(key=lambda r: r['value'], reverse=reverse)
        else:
            # Trier par le libellé de la ligne
            rows.sort(key=lambda r: self._sort_key_smart(r['row']), reverse=reverse)
        
        # Appliquer la limite après le tri
        if limit and limit > 0:
            rows = rows[:limit]
        
        return rows

    def _get_pivot_data(self, model, filter_obj, domain, context, line=None):
        """Génère les données pour un tableau croisé; support 1D (lignes) et 2D (lignes x colonnes).
        Utilise les informations du contexte du filtre pour respecter les paramètres de la vue pivot standard."""
        
        # Récupérer show_data_title
        show_data_title = context.get('show_data_title', True)
        
        # Déterminer la limite
        limit = None  # Pas de limite par défaut pour les pivots
        if line and hasattr(line, 'limit') and line.limit > 0:
            limit = line.limit
        
        # Récupérer les groupements et mesures depuis le contexte (priorité au contexte du filtre)
        row_gb = context.get('pivot_row_groupby') or context.get('graph_groupbys') or context.get('group_by')
        if isinstance(row_gb, list):
            row_gb = row_gb[0] if row_gb else None
        
        col_gb = context.get('pivot_column_groupby')
        if isinstance(col_gb, list):
            col_gb = col_gb[0] if col_gb else None
        
        # Pour la mesure, utiliser graph_measure du contexte si pivot_measures n'est pas défini
        measures = context.get('pivot_measures') or context.get('graph_measure') or context.get('measure')
        if isinstance(measures, list):
            measure = measures[0] if measures else None
        else:
            measure = measures

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
            # Ne pas appliquer la limite au read_group, on triera et limitera après
            try:
                results = model.read_group(domain, fields=fields or ["__count"], groupby=[row_gb, col_gb], lazy=False)
            except Exception:
                results = []
            
            # Récupérer les mappings pour les champs Selection
            row_selection_map = self._get_selection_map(model, row_gb.split(':')[0])
            col_selection_map = self._get_selection_map(model, col_gb.split(':')[0])
            
            # Construire la structure des colonnes et des lignes
            col_labels = []
            col_index = {}
            rows_map = {}
            
            for r in results:
                rlab = self._extract_label_from_record(r, row_gb, row_selection_map)
                clab = self._extract_label_from_record(r, col_gb, col_selection_map)
                
                if clab not in col_index:
                    col_index[clab] = len(col_labels)
                    col_labels.append(clab)
                
                if rlab not in rows_map:
                    rows_map[rlab] = []
                
                # Assurer la taille de la liste des lignes
                while len(rows_map[rlab]) < len(col_labels):
                    rows_map[rlab].append(0)
                
                val = (r.get('__count') if use_count else (r.get(f"{measure}_sum") or r.get(measure) or 0)) or 0
                rows_map[rlab][col_index[clab]] = val
            
            # Assurer que toutes les lignes ont la largeur complète
            for rlab, vals in rows_map.items():
                if len(vals) < len(col_labels):
                    vals.extend([0] * (len(col_labels) - len(vals)))
            
            # Construire la liste des lignes
            rows = [{'row': rlab, 'values': vals} for rlab, vals in rows_map.items()]
            
            # Trier et limiter
            rows = self._sort_and_limit_rows(rows, context, limit, is_2d=True)
            
            # Calculer les totaux si demandé
            show_row_totals = context.get('pivot_show_row_totals', True)
            show_col_totals = context.get('pivot_show_col_totals', True)
            
            col_totals = None
            if show_col_totals and rows:
                # Calculer le total de chaque colonne
                col_totals = [0] * len(col_labels)
                for row in rows:
                    for i, val in enumerate(row['values']):
                        col_totals[i] += val
            
            # Ajouter le total de ligne à chaque ligne si demandé
            if show_row_totals:
                for row in rows:
                    row['row_total'] = sum(row['values'])
            
            # sort columns by label for stability
            columns = [{'key': i, 'label': lbl} for i, lbl in enumerate(col_labels)]
            
            result = {
                'type': 'pivot',
                'data': {
                    'columns': columns,
                    'rows': rows,
                    'measure_label': measure_label,
                    'row_label': row_label,
                    'col_label': col_label,
                },
                'show_data_title': show_data_title,
            }
            
            # Ajouter les totaux au résultat
            if show_col_totals and col_totals is not None:
                result['data']['col_totals'] = col_totals
                if show_row_totals:
                    # Ajouter aussi le grand total (total des totaux)
                    result['data']['grand_total'] = sum(col_totals)
            
            return result

        # 1D pivot (lignes uniquement)
        data_rows = []
        if row_gb:
            # Récupérer le mapping pour les champs Selection
            row_selection_map = self._get_selection_map(model, row_gb.split(':')[0])
            
            # Ne pas appliquer la limite au read_group, on triera et limitera après
            try:
                results = model.read_group(domain, fields=fields or ["__count"], groupby=[row_gb], lazy=False)
                for r in results:
                    label = self._extract_label_from_record(r, row_gb, row_selection_map)
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
        else:
            # Trier et limiter (sauf si c'est juste le total)
            data_rows = self._sort_and_limit_rows(data_rows, context, limit, is_2d=False)
        
        # Calculer le total général pour les pivots 1D si demandé
        show_col_totals = context.get('pivot_show_col_totals', True)
        result = {
            'type': 'pivot',
            'data': data_rows,
            'measure_label': measure_label,
            'row_label': row_label,
            'show_data_title': show_data_title,
        }
        
        # Ajouter le total si demandé et si ce n'est pas déjà un total unique
        if show_col_totals and data_rows and not (len(data_rows) == 1 and data_rows[0]['row'] == 'Total'):
            total_value = sum(row['value'] for row in data_rows)
            result['total'] = total_value
        
        return result

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
            
            # Vérifier si le modèle a la méthode fields_view_get
            if hasattr(model, 'fields_view_get'):
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
            else:
                field_names = []
                fields_def = {}

            if not field_names:
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
            labels = {fn: fields_def.get(fn, {}).get('string', fn) for fn in field_names}
            return field_names, labels
        except Exception:
            return ['display_name'], {'display_name': 'Nom à afficher'}
