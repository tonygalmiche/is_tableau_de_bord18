# Module Tableau de Bord pour Odoo 18

Ce module permet de créer des tableaux de bord personnalisés dans Odoo 18 Community, reproduisant les fonctionnalités des tableaux de bord d'Odoo 14.

## Fonctionnalités

- **Création de tableaux de bord** : Créez des tableaux de bord avec un nom personnalisé
- **Ajout de recherches enregistrées** : Sélectionnez des recherches enregistrées (listes, graphiques, tableaux croisés)
- **Configuration de l'affichage** : Configurez la taille et la position des éléments
- **Visualisation unifiée** : Affichez plusieurs recherches sur un même écran

## Installation

1. Placez le module dans votre répertoire d'addons Odoo
2. Mettez à jour la liste des modules
3. Installez le module "InfoSaône - Tableau de bord pour Odoo 18"

## Utilisation

### 1. Créer des recherches enregistrées

Avant de créer un tableau de bord, vous devez avoir des recherches enregistrées :

1. Allez dans n'importe quel module (Ventes, Achats, CRM, etc.)
2. Configurez vos filtres et groupements
3. Cliquez sur "Favoris" > "Sauvegarder la recherche actuelle"
4. Donnez un nom à votre recherche

### 2. Créer un tableau de bord

1. Allez dans le menu "Tableaux de bord"
2. Cliquez sur "Créer"
3. Donnez un nom à votre tableau de bord
4. Dans l'onglet "Éléments du tableau de bord", ajoutez des lignes :
   - **Nom** : Nom de l'élément sur le tableau de bord
   - **Recherche enregistrée** : Sélectionnez une recherche existante
   - **Largeur** : Choisissez la largeur (pleine, demi, tiers, quart)
   - **Hauteur** : Choisissez la hauteur (300px à 600px)

### 3. Visualiser le tableau de bord

1. Depuis la liste des tableaux de bord, cliquez sur le bouton "Voir"
2. Ou depuis le formulaire d'un tableau de bord, cliquez sur "Voir le tableau de bord"

## Configuration des éléments

### Largeur disponible
- **Pleine largeur** : L'élément occupe toute la largeur
- **Demi largeur** : Deux éléments par ligne
- **Tiers de largeur** : Trois éléments par ligne  
- **Quart de largeur** : Quatre éléments par ligne

### Hauteur disponible
- **Petit** : 300px
- **Moyen** : 400px (par défaut)
- **Grand** : 500px
- **Très grand** : 600px

## Types de recherches supportées

- **Listes** : Affichage tabulaire des données
- **Graphiques** : Représentation graphique simple
- **Tableaux croisés** : Vue pivot des données

## Exemple d'utilisation

1. Créez une recherche "Mes opportunités ouvertes" dans le CRM
2. Créez une recherche "Ventes du mois" dans les Ventes
3. Créez un tableau de bord "Vue d'ensemble commercial"
4. Ajoutez les deux recherches avec des largeurs demi-largeur
5. Visualisez votre tableau de bord personnalisé

## Support

Ce module a été développé par InfoSaône pour offrir une alternative simple aux tableaux de bord dans Odoo 18 Community.

Pour toute question ou amélioration, contactez InfoSaône.
