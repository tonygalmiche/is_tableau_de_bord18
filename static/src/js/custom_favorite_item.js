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
        console.log('[TABLEAU DE BORD] ViewType:', viewType);
        console.log('[TABLEAU DE BORD] Config:', this.env?.config);
        
        if (viewType === 'list') {
            try {
                // Méthode 1: Lire directement les colonnes visibles depuis le DOM du tableau
                const tableHeaders = document.querySelectorAll('.o_list_view thead th[data-name]');
                console.log('[TABLEAU DE BORD] Headers trouvés dans le DOM:', tableHeaders.length);
                
                if (tableHeaders.length > 0) {
                    tableHeaders.forEach(th => {
                        const fieldName = th.getAttribute('data-name');
                        if (fieldName && !visibleColumns.includes(fieldName)) {
                            visibleColumns.push(fieldName);
                        }
                    });
                    console.log('[TABLEAU DE BORD] Colonnes extraites du DOM:', visibleColumns);
                }
                
                // Méthode 2 (fallback): Utiliser le renderer ou activeFields
                if (visibleColumns.length === 0) {
                    const renderer = this.env?.config?.getDisplayRenderer?.() || this.display?.renderer;
                    console.log('[TABLEAU DE BORD] Renderer:', renderer);
                    
                    if (renderer?.columns) {
                        console.log('[TABLEAU DE BORD] Colonnes du renderer:', renderer.columns);
                        visibleColumns = renderer.columns
                            .filter(col => col.type === 'field' && !col.optional || col.optional === 'show')
                            .map(col => col.name);
                    }
                    else if (this.env?.config?.activeFields) {
                        console.log('[TABLEAU DE BORD] Active fields:', this.env.config.activeFields);
                        visibleColumns = Object.keys(this.env.config.activeFields);
                    }
                }
                
                console.log('[TABLEAU DE BORD] Colonnes visibles capturées:', visibleColumns);
            } catch (e) {
                console.warn('[TABLEAU DE BORD] Erreur lors de la capture des colonnes visibles:', e);
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
        
        console.log('[TABLEAU DE BORD] Context final:', result.irFilter.context);
        console.log('[TABLEAU DE BORD] Colonnes visibles ajoutées:', visibleColumns);
        
        return result;
    }
});
