# -*- coding: utf-8 -*-

from odoo import models, fields


class IsTableauDeBordTest(models.Model):
    _name = 'is.tableau.de.bord'
    _description = 'Tableau de bord'
    _order = 'name'

    name = fields.Char('Nom du tableau de bord', required=True)
    active = fields.Boolean('Actif', default=True)
    
    def action_view_dashboard(self):
        """Action pour afficher le tableau de bord"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Dashboard - {self.name}',
            'res_model': 'is.tableau.de.bord',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'main',
        }
