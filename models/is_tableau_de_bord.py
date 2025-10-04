# -*- coding: utf-8 -*-

from odoo import models, fields, api


class IsTableauDeBord(models.Model):
    _name = 'is.tableau.de.bord'
    _description = 'Tableau de bord'
    _order = 'name'

    name = fields.Char('Nom du tableau de bord', required=True)
    line_ids = fields.One2many('is.tableau.de.bord.line', 'tableau_id', string='Lignes du tableau de bord')
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
        ('auto', 'Auto (depuis le favori)'),
        ('list', 'Liste'),
        ('graph', 'Graphique'),
        ('pivot', 'Tableau croisé'),
    ], string='Mode d\'affichage', default='auto')

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

    pivot_row_groupby = fields.Char('Pivot: Groupe lignes')
    pivot_col_groupby = fields.Char('Pivot: Groupe colonnes')
    pivot_measure = fields.Char('Pivot: Mesure (champ numérique)')

    @api.depends('model_id', 'user_id')
    def _compute_filter_domain(self):
        """Calcule le domaine pour filter_id en fonction de model_id et user_id"""
        for record in self:
            domain = []
            if record.model_id:
                domain.append(('model_id', '=', record.model_id.model))
            if record.user_id:
                # Filtrer par utilisateur OU recherches globales (user_id = False)
                domain.append('|')
                domain.append(('user_id', '=', record.user_id.id))
                domain.append(('user_id', '=', False))
            record.filter_domain = str(domain)

    filter_domain = fields.Char(compute='_compute_filter_domain', store=False)

    @api.depends_context('uid')
    def _compute_model_ids(self):
        """Calcule la liste des IDs des modèles ayant au moins un filtre utilisateur"""
        # Récupérer tous les filtres
        filters = self.env['ir.filters'].search([])
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
            record.model_ids = model_ids

    model_ids = fields.Many2many('ir.model', compute='_compute_model_ids', store=False)

    @api.onchange('model_id', 'user_id')
    def _onchange_model_user(self):
        """Réinitialiser le filtre si le modèle ou l'utilisateur change"""
        if self.filter_id:
            # Vérifier si le filtre actuel est compatible
            domain_valid = True
            if self.model_id and self.filter_id.model_id != self.model_id.model:
                domain_valid = False
            if self.user_id and self.filter_id.user_id and self.filter_id.user_id.id != self.user_id.id:
                domain_valid = False
            if not domain_valid:
                self.filter_id = False

    @api.onchange('filter_id')
    def _onchange_filter_id(self):
        """Remplir automatiquement le nom, le modèle et l'utilisateur avec ceux du filtre"""
        if self.filter_id:
            self.name = self.filter_id.name
            # Mettre à jour le modèle si pas encore défini
            if not self.model_id:
                self.model_id = self.env['ir.model'].search([('model', '=', self.filter_id.model_id)], limit=1)
            # Mettre à jour l'utilisateur si pas encore défini
            if not self.user_id and self.filter_id.user_id:
                self.user_id = self.filter_id.user_id

    def action_open_filter(self):
        """Ouvrir la recherche enregistrée en plein écran"""
        self.ensure_one()
        if not self.filter_id:
            return
        
        # Récupérer les informations du filtre
        filter_rec = self.filter_id
        
        # Préparer le contexte
        context = {}
        if filter_rec.context:
            try:
                import ast
                context = ast.literal_eval(filter_rec.context) if isinstance(filter_rec.context, str) else filter_rec.context
            except:
                context = {}
        
        # Préparer le domaine
        domain = []
        if filter_rec.domain:
            try:
                import ast
                domain = ast.literal_eval(filter_rec.domain) if isinstance(filter_rec.domain, str) else filter_rec.domain
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
            'name': filter_rec.name,
            'res_model': filter_rec.model_id,
            'views': views,
            'view_mode': view_mode,
            'domain': domain,
            'context': context,
            'target': 'current',
        }

    def action_edit_filter(self):
        """Ouvrir la fiche du filtre pour modification"""
        self.ensure_one()
        if self.filter_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Modifier la recherche enregistrée',
                'res_model': 'ir.filters',
                'res_id': self.filter_id.id,
                'view_mode': 'form',
            }
