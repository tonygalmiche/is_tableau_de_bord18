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
            console.warn("[IS_TABLEAU_DE_BORD] Impossible de récupérer le menu courant:", e);
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
        
        // Enrichir irFilter.context avec les métadonnées
        result.irFilter.context = {
            ...result.irFilter.context,
            active_menu_id: activeMenuId,
            active_view_id: activeViewId,
            view_type: viewType,
        };
        
        return result;
    }
});
