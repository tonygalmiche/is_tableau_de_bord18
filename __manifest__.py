# -*- coding: utf-8 -*-

{
  "name"      : "InfoSaône - Tableau de bord pour Odoo 18",
  # /!\ Penser à chaque changement à : 1) incrémenter cette version, 2) ajouter une
  # entrée dans "Notes de version" du README.md, 3) si une migration de données est
  # nécessaire, créer migrations/<version>/post-migrate.py (le dossier doit correspondre
  # exactement à cette version pour être exécuté).
  "version"   : "18.0.2.0.7",
  "author"    : "InfoSaône / Tony Galmiche",
  "maintainer": "InfoSaône",
  "website"   : "http://www.infosaone.com",
  "category"  : "InfoSaône",
  "description": """
InfoSaône - Tableau de bord pour Odoo 18

Module permettant de créer des tableaux de bord personnalisés en affichant
plusieurs recherches enregistrées sur une même page.

Fonctionnalités :
- Création de tableaux de bord avec nom personnalisé
- Ajout de recherches enregistrées (listes, graphiques, tableaux croisés)
- Configuration de la taille et position des éléments
- Affichage en temps réel des données
""",
  "depends" : [
    'base',
    'web',
  ], 
  "init_xml" : [],            
  "demo_xml" : [
    'data/demo_data.xml',
  ],            
  "data" : [
  'security/is_tableau_de_bord_security.xml',
  'security/ir.model.access.csv',
  'views/ir_filters_views.xml',
  'views/is_tableau_de_bord_views.xml',
  ],   
   'assets': {
        'web.assets_backend': [
            'is_tableau_de_bord18/static/src/css/dashboard.css',
            'is_tableau_de_bord18/static/src/scss/kanban_view.scss',
            'web/static/lib/Chart/Chart.js',
            'is_tableau_de_bord18/static/src/js/dashboard_view.js',
            'is_tableau_de_bord18/static/src/js/custom_favorite_item.js',
        ],
    },
  "installable": True,         
  "active": False,            
  "application": True,
  "license": "AGPL-3",
}


