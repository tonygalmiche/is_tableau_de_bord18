# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Renseigne field_id (nouveau champ) sur les lignes is.tableau.de.bord.line.field
    déjà existantes, à partir de leur field_name (nom technique déjà enregistré).
    N'affecte ni field_name ni field_label, qui restent inchangés.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    lines = env['is.tableau.de.bord.line.field'].search([
        ('field_id', '=', False),
        ('field_name', '!=', False),
    ])
    for line in lines:
        model_name = line.line_id.model_id.model
        if not model_name:
            continue
        field = env['ir.model.fields'].search([
            ('model', '=', model_name),
            ('name', '=', line.field_name),
        ], limit=1)
        if field:
            line.field_id = field.id
