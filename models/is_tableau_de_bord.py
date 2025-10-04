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
    filter_id = fields.Many2one('ir.filters', string='Recherche enregistrée', domain="[('model_id', '=', model_id)]")
    
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

    @api.onchange('model_id')
    def _onchange_model_id(self):
        """Réinitialiser le filtre si le modèle change"""
        if self.model_id and self.filter_id and self.filter_id.model_id != self.model_id.model:
            self.filter_id = False

    @api.onchange('filter_id')
    def _onchange_filter_id(self):
        """Remplir automatiquement le nom et le modèle avec ceux du filtre"""
        if self.filter_id:
            self.name = self.filter_id.name
            # Mettre à jour le modèle si pas encore défini
            if not self.model_id:
                self.model_id = self.env['ir.model'].search([('model', '=', self.filter_id.model_id)], limit=1)
