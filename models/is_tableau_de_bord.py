# -*- coding: utf-8 -*-

from odoo import models, fields, api


class IsTableauDeBord(models.Model):
    _name = 'is.tableau.de.bord'
    _description = 'Tableau de bord'
    _order = 'name'

    name = fields.Char('Nom du tableau de bord', required=True)
    description = fields.Text('Description')
    line_ids = fields.One2many('is.tableau.de.bord.line', 'tableau_id', copy=True, string='Lignes du tableau de bord')
    active = fields.Boolean('Actif', default=True)

    def action_view_dashboard(self):
        """Action pour afficher le tableau de bord"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Tableau de bord - {self.name}',
            'res_model': 'is.tableau.de.bord',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'main',
            'context': {'dashboard_mode': True},
            'views': [(self.env.ref('is_tableau_de_bord18.view_is_tableau_de_bord_dashboard').id, 'form')],
            'flags': {'mode': 'readonly'},
        }

    def action_back_to_list(self):
        """Retour à la liste des tableaux de bord"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Mes tableaux de bord',
            'res_model': 'is.tableau.de.bord',
            'view_mode': 'kanban,list',
            'domain': [('active', '=', True)],
            'target': 'main',
        }

    def action_edit_dashboard(self):
        """Ouvrir le formulaire d'édition du tableau de bord"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Modifier le tableau de bord',
            'res_model': 'is.tableau.de.bord',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'main',
            'views': [(self.env.ref('is_tableau_de_bord18.view_is_tableau_de_bord_form').id, 'form')],
        }

    @api.model
    def check_is_manager(self):
        """Vérifier si l'utilisateur actuel est un gestionnaire de tableau de bord"""
        return self.env.user.has_group('is_tableau_de_bord18.group_tableau_de_bord_manager')

    @api.model
    def action_open_tableaux_de_bord(self):
        """Action pour ouvrir les tableaux de bord selon les droits de l'utilisateur"""
        is_manager = self.env.user.has_group('is_tableau_de_bord18.group_tableau_de_bord_manager')
        
        if is_manager:
            # Gestionnaire : accès complet avec kanban, list, form
            view_mode = 'kanban,list,form'
        else:
            # Utilisateur simple : vue kanban seulement
            view_mode = 'kanban'
        

        action = {
            'type': 'ir.actions.act_window',
            'name': 'Mes tableaux de bord',
            'res_model': 'is.tableau.de.bord',
            'view_mode': view_mode,
            'domain': [('active', '=', True)],
            'target': 'main',
            'context': {},
            'help': """
                <p class="o_view_nocontent_smiling_face">
                    Aucun tableau de bord disponible !
                </p>
            """ if not is_manager else """
                <p class="o_view_nocontent_smiling_face">
                    Aucun tableau de bord disponible !
                </p>
                <p>
                    Créez d'abord vos tableaux de bord.
                </p>
            """
        }
        return action

    def action_refresh_all_lines_from_filters(self):
        """Action pour rafraîchir toutes les lignes du tableau de bord depuis leurs filtres"""
        self.ensure_one()
        updated_count = 0
        for line in self.line_ids:
            if line.filter_id:
                extracted = line._extract_filter_context_values(line.filter_id)
                if extracted:
                    line.write(extracted)
                    updated_count += 1
        


class IsTableauDeBordLine(models.Model):
    _name = 'is.tableau.de.bord.line'
    _description = 'Ligne du tableau de bord'
    _order = 'sequence, id'

    tableau_id = fields.Many2one('is.tableau.de.bord', string='Tableau de bord', required=True, ondelete='cascade')
    name = fields.Char('Nom', required=True)
    sequence = fields.Integer('Séquence', default=10)
    
    # Sélection du modèle et de la recherche enregistrée
    model_id = fields.Many2one('ir.model', string='Modèle', help='Sélectionnez le modèle pour filtrer les recherches enregistrées')
    user_id = fields.Many2one('res.users', string='Utilisateur', default=lambda self: self.env.user, help='Filtrer les recherches par utilisateur (laisser vide pour voir toutes les recherches)')
    filter_id = fields.Many2one('ir.filters', string='Recherche enregistrée')
    
    # Configuration de l'affichage
    width = fields.Selection([
        ('12', 'Pleine largeur'),
        ('6', 'Demi largeur'),
        ('4', 'Tiers de largeur'),
        ('3', 'Quart de largeur'),
    ], string='Largeur', default='6')
    
    height = fields.Selection([
        ('300', 'Petit (300px)'),
        ('400', 'Moyen (400px)'),
        ('500', 'Grand (500px)'),
        ('600', 'Très grand (600px)'),
    ], string='Hauteur', default='400')

    # Overrides d'affichage (facultatifs)
    display_mode = fields.Selection([
        ('list', 'Liste'),
        ('graph', 'Graphique'),
        ('pivot', 'Tableau croisé'),
    ], string='Mode d\'affichage', default='graph')

    graph_chart_type = fields.Selection([
        ('bar', 'Barres'),
        ('line', 'Courbes'),
        ('pie', 'Camembert'),
    ], string='Type de graphique', default='bar')

    graph_aggregator = fields.Selection([
        ('sum', 'Somme'),
        ('avg', 'Moyenne'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
        ('count', 'Compte'),
    ], string='Agrégateur', default='sum')
    
    graph_measure = fields.Char('Graph: Mesure', help='Champ utilisé pour la mesure du graphique')
    graph_groupbys = fields.Char('Graph: Groupements', help='Liste des groupements pour le graphique (ex: invoice_date:year)')

    pivot_row_groupby = fields.Char('Pivot: Groupe lignes')
    pivot_col_groupby = fields.Char('Pivot: Groupe colonnes')
    pivot_measure     = fields.Char('Pivot: Mesure (champ numérique)')
    pivot_sort_by = fields.Selection([
        ('row', 'Tri des lignes'),
        ('total', 'Tri des totaux'),
    ], string='Tri par', default='row', help='Critère de tri (graphique: label=row, value=total)')
    pivot_sort_order = fields.Selection([
        ('asc', 'Tri croissant'),
        ('desc', 'Tri décroissant'),
    ], string='Ordre du tri', default='asc', help='Ordre de tri (pivot et graphique)')
    pivot_show_row_totals = fields.Boolean('Afficher les totaux des lignes', default=True, help='Ajouter une colonne de total pour chaque ligne')
    pivot_show_col_totals = fields.Boolean('Afficher les totaux des colonnes', default=True, help='Ajouter une ligne de total pour chaque colonne')
    limit = fields.Integer('Limite', default=0, help='Nombre maximum de lignes à afficher (0 = toutes les lignes)')
    filter_domain     = fields.Char(compute='_compute_filter_domain', store=False)
    field_ids         = fields.One2many('is.tableau.de.bord.line.field', 'line_id', string='Champs de la liste')
    model_ids         = fields.Many2many('ir.model', compute='_compute_model_ids', store=False, compute_sudo=True)


    @api.depends('tableau_id')
    def _compute_model_ids(self):
        """Calcule la liste des IDs des modèles ayant au moins un filtre utilisateur"""
        # Filtrer uniquement les filtres des utilisateurs (exclure les filtres système)
        filters = self.env['ir.filters'].search([('user_id', '!=', False)])
        
        # Extraire les noms de modèles uniques
        model_names = list(set(filters.mapped('model_id')))
        
        if model_names:
            # Récupérer les IDs des ir.model correspondants
            models = self.env['ir.model'].search([('model', 'in', model_names)])
            model_ids = models.ids
        else:
            model_ids = []
        
        # Appliquer la même liste à tous les enregistrements
        for record in self:
            record.model_ids = [(6, 0, model_ids)]

    @api.depends('model_id', 'user_id')
    def _compute_filter_domain(self):
        """Calcule le domaine pour filter_id en fonction de model_id et user_id"""
        for record in self:
            domain = [('user_id', '!=', False)]  # Uniquement les filtres des utilisateurs
            if record.model_id:
                domain.append(('model_id', '=', record.model_id.model))
            if record.user_id:
                # Filtrer par utilisateur spécifique
                domain.append(('user_id', '=', record.user_id.id))
            record.filter_domain = str(domain)


    @api.onchange('model_id', 'user_id')
    def _onchange_model_user(self):
        """Réinitialiser le filtre si le modèle ou l'utilisateur change"""

        if self.model_id:
            self.name = self.model_id.name

        if self.filter_id:
            # Vérifier si le filtre actuel est compatible
            domain_valid = True
            if self.model_id and self.filter_id.model_id != self.model_id.model:
                domain_valid = False
            if self.user_id and self.filter_id.user_id and self.filter_id.user_id.id != self.user_id.id:
                domain_valid = False
            if not domain_valid:
                self.filter_id = False
                # Vider la liste des champs si on réinitialise le filtre
                if self.display_mode == 'list':
                    self.field_ids = [(5, 0, 0)]

    @api.onchange('filter_id')
    def _onchange_filter_id(self):
        """Remplir automatiquement le nom, le modèle et l'utilisateur avec ceux du filtre"""
        if not self.filter_id:
            # Si on désélectionne le filtre, vider la liste des champs
            if self.display_mode == 'list':
                self.field_ids = [(5, 0, 0)]
            return
            
        self.name = self.filter_id.name

        # Mettre à jour le modèle si pas encore défini
        if not self.model_id:
            self.model_id = self.env['ir.model'].search([('model', '=', self.filter_id.model_id)], limit=1)
        # Mettre à jour l'utilisateur si pas encore défini
        if not self.user_id and self.filter_id.user_id:
            self.user_id = self.filter_id.user_id
        
        # Récupérer le display_mode depuis le filtre si renseigné
        if self.filter_id.is_view_type:
            view_type = self.filter_id.is_view_type
            if view_type:
                self.display_mode = view_type
        
        # Extraire les informations du contexte pour les graphiques
        if self.filter_id.context:
            try:
                import ast
                context = ast.literal_eval(self.filter_id.context) if isinstance(self.filter_id.context, str) else self.filter_id.context
                
                # Pour les graphiques
                if self.display_mode == 'graph' and isinstance(context, dict):
                    # Récupérer graph_mode (bar, line, pie)
                    if 'graph_mode' in context:
                        graph_mode = context['graph_mode']
                        self.graph_chart_type = graph_mode if graph_mode in ['bar', 'line', 'pie'] else 'bar'
                    
                    # Récupérer graph_measure
                    if 'graph_measure' in context:
                        self.graph_measure = context['graph_measure']
                    
                    # Récupérer graph_groupbys (liste)
                    if 'graph_groupbys' in context:
                        groupbys = context['graph_groupbys']
                        if isinstance(groupbys, list):
                            self.graph_groupbys = ','.join(groupbys)
                        else:
                            self.graph_groupbys = str(groupbys)
                
                # Pour les pivots
                elif self.display_mode == 'pivot' and isinstance(context, dict):
                    # Récupérer pivot_measures
                    if 'pivot_measures' in context:
                        measures = context['pivot_measures']
                        if isinstance(measures, list) and measures:
                            self.pivot_measure = measures[0]
                        else:
                            self.pivot_measure = str(measures)
                    
                    # Récupérer pivot_row_groupby
                    if 'pivot_row_groupby' in context:
                        row_groupby = context['pivot_row_groupby']
                        if isinstance(row_groupby, list):
                            self.pivot_row_groupby = ','.join(row_groupby)
                        else:
                            self.pivot_row_groupby = str(row_groupby)
                    
                    # Récupérer pivot_column_groupby (la clé standard dans les favoris)
                    if 'pivot_column_groupby' in context:
                        col_groupby = context['pivot_column_groupby']
                        if isinstance(col_groupby, list):
                            self.pivot_col_groupby = ','.join(col_groupby)
                        else:
                            self.pivot_col_groupby = str(col_groupby)
            
            except Exception:
                pass  # En cas d'erreur de parsing, on ignore
        
        # Charger les champs de la vue si display_mode est 'list'
        # Recharger systématiquement les champs quand on change de filtre
        if self.display_mode == 'list':
            self._load_list_fields()

    @api.onchange('display_mode')
    def _onchange_display_mode(self):
        """Charger les champs de la liste lorsque display_mode = 'list'"""

        self.graph_chart_type=False
        if self.display_mode == 'graph':
            self.graph_chart_type='bar'



        if self.display_mode == 'list' and self.filter_id:
            self._load_list_fields()

    def _load_list_fields(self):
        """Charge les champs de la vue liste par défaut ou depuis le filtre"""
        # Supprimer les champs existants
        self.field_ids = [(5, 0, 0)]
        
        # Si pas de filtre ou de modèle, laisser la liste vide
        if not self.filter_id or not self.model_id:
            return
        
        # Essayer de récupérer les champs depuis la vue enregistrée dans le filtre
        field_names = []
        view = None
        
        # Si le filtre a une vue spécifique (is_view_id), on utilise cette vue
        if hasattr(self.filter_id, 'is_view_id') and self.filter_id.is_view_id:
            view = self.filter_id.is_view_id
            if view.type in ('tree', 'list'):
                # Parser l'arch pour extraire les champs
                import lxml.etree as etree
                try:
                    arch = etree.fromstring(view.arch)
                    field_elements = arch.xpath('//field[@name]')
                    field_names = [f.get('name') for f in field_elements if f.get('name')]
                except Exception as e:
                    field_names = []
        
        # Si pas de vue spécifique ou pas de champs trouvés, utiliser la vue par défaut du modèle
        if not field_names:
            # Récupérer la vue liste par défaut
            view = self.env['ir.ui.view'].search([
                ('model', '=', self.filter_id.model_id),
                ('type', 'in', ['tree', 'list'])
            ], limit=1, order='priority,id')
            
            if view:
                import lxml.etree as etree
                try:
                    arch = etree.fromstring(view.arch)
                    field_elements = arch.xpath('//field[@name]')
                    field_names = [f.get('name') for f in field_elements if f.get('name')]
                except Exception as e:
                    field_names = []
        
        # Si toujours pas de champs, utiliser les champs de base du modèle
        if not field_names:
            # Récupérer quelques champs du modèle
            model = self.env[self.filter_id.model_id]
            field_names = []
            for fname, field in model._fields.items():
                if fname not in ['id', 'create_uid', 'create_date', 'write_uid', 'write_date']:
                    field_names.append(fname)
                if len(field_names) >= 10:  # Limiter à 10 champs
                    break
        
        # Récupérer le modèle pour obtenir les labels des champs
        model = self.env[self.filter_id.model_id]
        
        # Filtrer les champs valides (qui existent réellement dans le modèle)
        valid_field_names = [fname for fname in field_names if fname and fname in model._fields]
        
        # Créer les lignes de champs avec leur nom technique
        # Le libellé sera calculé automatiquement par _compute_field_label
        sequence = 10
        for fname in valid_field_names:
            self.field_ids = [(0, 0, {
                'field_name': fname,  # Nom technique (le label sera calculé automatiquement)
                'visible': True,
                'sequence': sequence,
            })]
            sequence += 10


    def _extract_filter_context_values(self, filter_obj):
        """Extrait les valeurs pivot/graph du contexte d'un filtre"""
        if not filter_obj or not filter_obj.context:
            return {}
        
        try:
            import ast
            context = ast.literal_eval(filter_obj.context) if isinstance(filter_obj.context, str) else filter_obj.context
            if not isinstance(context, dict):
                return {}
            
            result = {}
            
            # Récupérer le display_mode depuis le filtre
            if filter_obj.is_view_type:
                result['display_mode'] = filter_obj.is_view_type
            
            # Pour les pivots
            if 'pivot_measures' in context:
                measures = context['pivot_measures']
                if isinstance(measures, list) and measures:
                    result['pivot_measure'] = measures[0]
                else:
                    result['pivot_measure'] = str(measures)
            
            if 'pivot_row_groupby' in context:
                row_groupby = context['pivot_row_groupby']
                if isinstance(row_groupby, list):
                    result['pivot_row_groupby'] = ','.join(row_groupby)
                else:
                    result['pivot_row_groupby'] = str(row_groupby)
            
            if 'pivot_column_groupby' in context:
                col_groupby = context['pivot_column_groupby']
                if isinstance(col_groupby, list):
                    result['pivot_col_groupby'] = ','.join(col_groupby)
                else:
                    result['pivot_col_groupby'] = str(col_groupby)
            
            # Pour les graphiques
            if 'graph_mode' in context:
                graph_mode = context['graph_mode']
                if graph_mode in ['bar', 'line', 'pie']:
                    result['graph_chart_type'] = graph_mode
            
            if 'graph_measure' in context:
                result['graph_measure'] = context['graph_measure']
            
            if 'graph_groupbys' in context:
                groupbys = context['graph_groupbys']
                if isinstance(groupbys, list):
                    result['graph_groupbys'] = ','.join(groupbys)
                else:
                    result['graph_groupbys'] = str(groupbys)
            
            return result
            
        except Exception:
            return {}

    @api.model_create_multi
    def create(self, vals_list):
        """Surcharge create pour extraire automatiquement les valeurs du filtre"""
        for vals in vals_list:
            if vals.get('filter_id') and not vals.get('pivot_col_groupby'):
                # Extraire les valeurs du contexte du filtre
                filter_obj = self.env['ir.filters'].browse(vals['filter_id'])
                extracted = self._extract_filter_context_values(filter_obj)
                # Ne surcharger que les valeurs non définies
                for key, value in extracted.items():
                    if key not in vals or not vals[key]:
                        vals[key] = value
        
        return super().create(vals_list)

    def write(self, vals):
        """Surcharge write pour extraire automatiquement les valeurs du filtre"""
        # Si on change le filter_id, extraire les nouvelles valeurs
        if 'filter_id' in vals and vals['filter_id']:
            for record in self:
                filter_obj = self.env['ir.filters'].browse(vals['filter_id'])
                extracted = self._extract_filter_context_values(filter_obj)
                # Ne surcharger que les valeurs non définies dans vals
                for key, value in extracted.items():
                    if key not in vals or not vals[key]:
                        vals[key] = value
        
        return super().write(vals)


    def action_refresh_from_filter(self):
        """Action pour forcer le rechargement des paramètres depuis le filtre"""
        for record in self:
            if not record.filter_id:
                continue
            
            extracted = record._extract_filter_context_values(record.filter_id)
            if extracted:
                record.write(extracted)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Paramètres rechargés',
                'message': 'Les paramètres ont été rechargés depuis le filtre.',
                'type': 'success',
                'sticky': False,
            }
        }


    def action_open_filter(self):
        """Ouvrir la recherche enregistrée en plein écran"""
        self.ensure_one()
        if not self.filter_id:
            return
        
        # Préparer le contexte
        context = {}
        if self.filter_id.context:
            try:
                import ast
                # Remplacer null par None pour que ast.literal_eval fonctionne
                context_str = self.filter_id.context.replace('null', 'None').replace('true', 'True').replace('false', 'False')
                context = ast.literal_eval(context_str) if isinstance(context_str, str) else self.filter_id.context
            except Exception as e:
                context = {}
        
        # Ajouter/Surcharger avec les informations de la ligne si définies
        if self.graph_measure:
            context['graph_measure'] = self.graph_measure
        if self.graph_groupbys:
            # Convertir la chaîne en liste
            context['graph_groupbys'] = [g.strip() for g in self.graph_groupbys.split(',')]
        if self.graph_chart_type:
            context['graph_mode'] = self.graph_chart_type
        if self.graph_aggregator:
            context['graph_aggregator'] = self.graph_aggregator
        if self.pivot_measure:
            context['pivot_measures'] = [self.pivot_measure]
        if self.pivot_row_groupby:
            context['pivot_row_groupby'] = [g.strip() for g in self.pivot_row_groupby.split(',')]
        if self.pivot_col_groupby:
            context['pivot_column_groupby'] = [g.strip() for g in self.pivot_col_groupby.split(',')]
        
        # Préparer le domaine
        domain = []
        if self.filter_id.domain:
            try:
                import ast
                domain = ast.literal_eval(self.filter_id.domain) if isinstance(self.filter_id.domain, str) else self.filter_id.domain
            except:
                domain = []
        
        # Déterminer les vues et le mode en fonction de display_mode
        if self.display_mode == 'list':
            views = [[False, 'list'], [False, 'form']]
            view_mode = 'list,form'
        elif self.display_mode == 'graph':
            views = [[False, 'graph'], [False, 'list'], [False, 'form']]
            view_mode = 'graph,list,form'
        elif self.display_mode == 'pivot':
            views = [[False, 'pivot'], [False, 'list'], [False, 'form']]
            view_mode = 'pivot,list,form'
        else:  # auto ou non défini
            # Utiliser toutes les vues disponibles
            views = [[False, 'list'], [False, 'graph'], [False, 'pivot'], [False, 'form']]
            view_mode = 'list,graph,pivot,form'
        
        # Ouvrir l'action
        return {
            'type': 'ir.actions.act_window',
            'name': self.filter_id.name,
            'res_model': self.filter_id.model_id,
            'views': views,
            'view_mode': view_mode,
            'domain': domain,
            'context': context,
            'target': 'current',
        }

    def action_edit_filter(self):
        """Ouvrir la fiche du filtre pour modification"""
        self.ensure_one()
        if not self.filter_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Aucun filtre',
                    'message': 'Aucune recherche enregistrée n\'est associée à cette ligne.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Modifier la recherche enregistrée',
            'res_model': 'ir.filters',
            'res_id': self.filter_id.id,
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'current',
        }

    def action_duplicate_line(self):
        """Dupliquer la ligne du tableau de bord"""
        self.ensure_one()
        # Copier la ligne
        new_line = self.copy()
        # Modifier le nom pour indiquer que c'est une copie
        new_line.name = f"{self.name} (copie)"


class IsTableauDeBordLineField(models.Model):
    _name = 'is.tableau.de.bord.line.field'
    _description = 'Champ de la ligne du tableau de bord'
    _order = 'sequence, id'

    line_id = fields.Many2one('is.tableau.de.bord.line', string='Ligne', required=True, ondelete='cascade')
    sequence = fields.Integer('Séquence', default=10)
    field_name = fields.Char('Nom du champ', required=True, help='Nom technique du champ')
    field_label = fields.Char('Libellé du champ', compute='_compute_field_label', store=True, readonly=False, help='Libellé affiché du champ')
    visible = fields.Boolean('Visible', default=True, help='Afficher ce champ dans le tableau de bord')
    
    @api.depends('field_name', 'line_id.model_id')
    def _compute_field_label(self):
        """Calcule le libellé du champ à partir de son nom technique"""
        for record in self:
            if not record.field_name or not record.line_id or not record.line_id.model_id:
                record.field_label = record.field_name or ''
                continue
            
            try:
                # Récupérer le modèle
                model = self.env[record.line_id.model_id.model]
                # Utiliser fields_get() pour obtenir le libellé traduit
                fields_info = model.fields_get([record.field_name])
                if record.field_name in fields_info:
                    record.field_label = fields_info[record.field_name].get('string', record.field_name)
                else:
                    record.field_label = record.field_name
            except Exception:
                record.field_label = record.field_name
