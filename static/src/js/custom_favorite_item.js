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
        console.log("[IS_TABLEAU_DE_BORD] _getIrFilterDescription appelé");
        console.log("[IS_TABLEAU_DE_BORD] params:", params);
        
        // Appeler la méthode parente pour obtenir preFavorite et irFilter
        const result = super._getIrFilterDescription(params);
        console.log("[IS_TABLEAU_DE_BORD] result original:", result);
        
        // Récupérer les informations du menu courant
        let activeMenuId = false;
        try {
            const menuService = this.env.services.menu;
            console.log("[IS_TABLEAU_DE_BORD] menuService:", menuService);
            const currentApp = menuService?.getCurrentApp();
            console.log("[IS_TABLEAU_DE_BORD] currentApp:", currentApp);
            activeMenuId = currentApp?.id || false;
            console.log("[IS_TABLEAU_DE_BORD] activeMenuId:", activeMenuId);
        } catch (e) {
            console.warn("[IS_TABLEAU_DE_BORD] Impossible de récupérer le menu courant:", e);
        }
        
        // Récupérer les informations de la vue courante
        const config = this.env.config;
        console.log("[IS_TABLEAU_DE_BORD] config:", config);
        const viewType = config?.viewType || false;
        console.log("[IS_TABLEAU_DE_BORD] viewType:", viewType);
        const views = config?.views || [];
        console.log("[IS_TABLEAU_DE_BORD] views:", views);
        
        // Trouver l'ID de la vue correspondant au type actuel
        let activeViewId = false;
        if (views && viewType) {
            const currentView = views.find(v => v[1] === viewType);
            console.log("[IS_TABLEAU_DE_BORD] currentView trouvée:", currentView);
            if (currentView && currentView[0]) {
                activeViewId = currentView[0];
                console.log("[IS_TABLEAU_DE_BORD] activeViewId:", activeViewId);
            }
        }
        
        // Enrichir irFilter.context avec les métadonnées
        result.irFilter.context = {
            ...result.irFilter.context,
            active_menu_id: activeMenuId,
            active_view_id: activeViewId,
            view_type: viewType,
        };
        
        console.log("[IS_TABLEAU_DE_BORD] irFilter.context enrichi:", result.irFilter.context);
        
        return result;
    }
});
