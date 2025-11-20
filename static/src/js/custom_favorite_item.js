/** @odoo-module **/

import { SearchModel } from "@web/search/search_model";
import { patch } from "@web/core/utils/patch";

/**
 * Extension de SearchModel pour capturer le menu et la vue courante
 * lors de la création d'un favori
 */
patch(SearchModel.prototype, {
    /**
     * Override de _getIrFilterDescription pour enrichir irFilter.context avec les métadonnées
     */
    _getIrFilterDescription(params) {
        // Appeler la méthode parente pour obtenir preFavorite et irFilter
        const result = super._getIrFilterDescription(params);
        
        // Récupérer les informations du menu courant
        let activeMenuId = false;
        try {
            const menuService = this.env.services.menu;
            const currentApp = menuService?.getCurrentApp();
            activeMenuId = currentApp?.id || false;
        } catch (e) {
            // Erreur lors de la récupération du menu courant
        }
        
        // Récupérer les informations de la vue courante
        const config = this.env.config;
        const viewType = config?.viewType || false;
        const views = config?.views || [];
        
        // Trouver l'ID de la vue correspondant au type actuel
        let activeViewId = false;
        
        // Essayer d'abord avec viewId direct (peut exister dans certains cas)
        if (config?.viewId) {
            activeViewId = config.viewId;
        }
        // Sinon chercher dans views
        else if (views && viewType) {
            const currentView = views.find(v => v[1] === viewType);
            if (currentView && currentView[0]) {
                activeViewId = currentView[0];
            }
        }
        
        // Capturer les colonnes visibles pour les vues list/tree
        let visibleColumns = [];
        
        if (viewType === 'list') {
            try {
                // Méthode 1: Lire directement les colonnes visibles depuis le DOM du tableau
                const tableHeaders = document.querySelectorAll('.o_list_view thead th[data-name]');
                
                if (tableHeaders.length > 0) {
                    tableHeaders.forEach(th => {
                        const fieldName = th.getAttribute('data-name');
                        if (fieldName && !visibleColumns.includes(fieldName)) {
                            visibleColumns.push(fieldName);
                        }
                    });
                }
                
                // Méthode 2 (fallback): Utiliser le renderer ou activeFields
                if (visibleColumns.length === 0) {
                    const renderer = this.env?.config?.getDisplayRenderer?.() || this.display?.renderer;
                    
                    if (renderer?.columns) {
                        visibleColumns = renderer.columns
                            .filter(col => col.type === 'field' && !col.optional || col.optional === 'show')
                            .map(col => col.name);
                    }
                    else if (this.env?.config?.activeFields) {
                        visibleColumns = Object.keys(this.env.config.activeFields);
                    }
                }
            } catch (e) {
                // Ignorer les erreurs silencieusement
            }
        }
        
        // Enrichir irFilter.context avec les métadonnées
        result.irFilter.context = {
            ...result.irFilter.context,
            active_menu_id: activeMenuId,
            active_view_id: activeViewId,
            view_type: viewType,
            visible_columns: visibleColumns.length > 0 ? visibleColumns : false,
        };
        
        return result;
    }
});
