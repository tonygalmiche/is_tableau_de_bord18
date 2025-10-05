# -*- coding: utf-8 -*-

from odoo import models, fields, api
import json


class IrFilters(models.Model):
    _inherit = 'ir.filters'

    # Nouveaux champs pour stocker le menu et la vue courante
    is_menu_id = fields.Many2one(
        'ir.ui.menu', 
        string='Menu courant',
        help="Menu qui était actif lors de la création de cette recherche enregistrée"
    )
    is_view_id = fields.Many2one(
        'ir.ui.view', 
        string='Vue courante',
        help="Vue qui était active lors de la création de cette recherche enregistrée"
    )
    is_view_type = fields.Selection([
        ('list', 'Liste'),
        ('form', 'Formulaire'),
        ('kanban', 'Kanban'),
        ('calendar', 'Calendrier'),
        ('pivot', 'Tableau croisé'),
        ('graph', 'Graphique'),
        ('activity', 'Activité'),
        ('gantt', 'Gantt'),
        ('map', 'Carte'),
    ], string='Type de vue', help="Type de vue qui était active lors de la création")

    @api.model
    def create_or_replace(self, vals):
        """
        Override de la méthode create_or_replace pour capturer 
        le menu_id, view_id et view_type depuis le contexte du favori
        """
        print("\n" + "="*80)
        print("[IS_TABLEAU_DE_BORD] create_or_replace appelé")
        print(f"[IS_TABLEAU_DE_BORD] vals reçu: {vals}")
        print("="*80 + "\n")
        
        # Extraire les informations du contexte dans vals si elles existent
        if 'context' in vals and vals['context']:
            print(f"[IS_TABLEAU_DE_BORD] Contexte présent: {vals['context']}")
            print(f"[IS_TABLEAU_DE_BORD] Type du contexte: {type(vals['context'])}")
            
            try:
                # Parser le contexte (peut être une chaîne JSON ou un dict)
                if isinstance(vals['context'], str):
                    print("[IS_TABLEAU_DE_BORD] Parsing du contexte (string)")
                    context_dict = json.loads(vals['context']) if vals['context'] else {}
                else:
                    print("[IS_TABLEAU_DE_BORD] Contexte déjà un dict")
                    context_dict = vals['context']
                
                print(f"[IS_TABLEAU_DE_BORD] context_dict: {context_dict}")
                
                # Extraire menu_id, view_id et view_type du contexte
                if 'active_menu_id' in context_dict and context_dict['active_menu_id']:
                    print(f"[IS_TABLEAU_DE_BORD] active_menu_id trouvé: {context_dict['active_menu_id']}")
                    vals['is_menu_id'] = context_dict['active_menu_id']
                    # Retirer du contexte pour ne pas polluer
                    del context_dict['active_menu_id']
                else:
                    print("[IS_TABLEAU_DE_BORD] active_menu_id NON trouvé dans le contexte")
                
                if 'active_view_id' in context_dict and context_dict['active_view_id']:
                    print(f"[IS_TABLEAU_DE_BORD] active_view_id trouvé: {context_dict['active_view_id']}")
                    vals['is_view_id'] = context_dict['active_view_id']
                    # Retirer du contexte pour ne pas polluer
                    del context_dict['active_view_id']
                else:
                    print("[IS_TABLEAU_DE_BORD] active_view_id NON trouvé dans le contexte")
                
                if 'view_type' in context_dict and context_dict['view_type']:
                    print(f"[IS_TABLEAU_DE_BORD] view_type trouvé: {context_dict['view_type']}")
                    vals['is_view_type'] = context_dict['view_type']
                    # Retirer du contexte pour ne pas polluer
                    del context_dict['view_type']
                else:
                    print("[IS_TABLEAU_DE_BORD] view_type NON trouvé dans le contexte")
                
                # Remettre le contexte nettoyé
                vals['context'] = json.dumps(context_dict) if context_dict else '{}'
                print(f"[IS_TABLEAU_DE_BORD] Contexte nettoyé: {vals['context']}")
                
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"[IS_TABLEAU_DE_BORD] ERREUR lors de l'extraction: {str(e)}")
                # En cas d'erreur, on continue sans bloquer
                self.env['ir.logging'].sudo().create({
                    'name': 'ir.filters.create_or_replace',
                    'type': 'server',
                    'level': 'warning',
                    'message': f'Erreur lors de l\'extraction des métadonnées du contexte: {str(e)}',
                    'path': 'is_tableau_de_bord18/models/ir_filters.py',
                    'line': '0',
                    'func': 'create_or_replace',
                })
        else:
            print("[IS_TABLEAU_DE_BORD] Pas de contexte dans vals")
        
        print(f"[IS_TABLEAU_DE_BORD] vals final avant appel super(): {vals}")
        print("="*80 + "\n")
        
        # Appeler la méthode parent
        result = super(IrFilters, self).create_or_replace(vals)
        
        print(f"[IS_TABLEAU_DE_BORD] Résultat de create_or_replace: {result}")
        print(f"[IS_TABLEAU_DE_BORD] is_menu_id: {result.is_menu_id}")
        print(f"[IS_TABLEAU_DE_BORD] is_view_id: {result.is_view_id}")
        print(f"[IS_TABLEAU_DE_BORD] is_view_type: {result.is_view_type}")
        print("="*80 + "\n")
        
        return result
