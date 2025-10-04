/** @odoo-module **/

import { Component, onMounted, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class DashboardFormController extends FormController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        
        onMounted(() => {
            // Vérifier si nous sommes en mode dashboard
            if (this.props.context?.dashboard_mode) {
                console.log('[TDB] Dashboard mode ON', this.props);
                this.setupDashboard();
            }
        });
    }

    async setupDashboard() {
        // Attendre que le formulaire soit complètement chargé
        setTimeout(() => {
            this.createDashboardLayout();
            this.loadDashboardItems();
        }, 1500);
    }

    createDashboardLayout() {
        const record = this.model.root;
        if (!record?.data?.line_ids?.records) {
            console.log("[TDB] Aucune donnée de ligne trouvée", record?.data?.line_ids);
            return;
        }

        const container = document.getElementById('dashboard_container');
        if (!container) {
            console.log("[TDB] Container dashboard non trouvé");
            return;
        }

        let html = '<div class="row">';
        
        for (const lineRecord of record.data.line_ids.records) {
            const line = lineRecord.data;
            // filter_id peut être un many2one sous forme [id, display] ou un objet {resId}
            let filterId = null;
            if (Array.isArray(line.filter_id)) {
                filterId = line.filter_id[0];
            } else if (line.filter_id && typeof line.filter_id === 'object') {
                // Odoo 18 peut exposer m2o comme {id, display_name} ou {resId}
                filterId = line.filter_id.id || line.filter_id.resId || null;
            } else if (typeof line.filter_id === 'number') {
                filterId = line.filter_id;
            }
            
            // Récupérer l'ID serveur de la ligne
            const serverLineId = lineRecord.resId || line.id || (line._values && line._values.id) || lineRecord.id;
            
            const widthCol = parseInt(line.width || 6, 10);
            const heightPx = parseInt(line.height || 400, 10);
            html += `
                <div class="col-md-${isNaN(widthCol) ? 6 : widthCol} mb-3">
                    <div class="card h-100">
                        <div class="card-header">
                            <h5 class="card-title mb-0">${line.name || 'Sans nom'}</h5>
                            <small class="text-muted">ID Filtre: ${filterId || 'Non défini'}</small>
                        </div>
                        <div class="card-body p-0" style="height: ${isNaN(heightPx) ? 400 : heightPx}px; overflow: auto;">
                            <div id="dashboard_item_${lineRecord.id}" class="dashboard-item h-100 d-flex align-items-center justify-content-center">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Chargement...</span>
                                </div>
                            </div>
                        </div>
                        <div class="card-footer text-center py-2" style="background-color: #f8f9fa; border-top: 1px solid #dee2e6;">
                            <a href="#" class="btn btn-sm btn-outline-primary open-filter-link" data-line-id="${serverLineId}" title="Ouvrir la recherche complète en plein écran">
                                <i class="fa fa-expand"></i> Plein écran
                            </a>
                            <a href="#" class="btn btn-sm btn-outline-secondary edit-filter-link ms-2" data-line-id="${serverLineId}" title="Modifier le filtre">
                                <i class="fa fa-search"></i>
                            </a>
                        </div>
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
    container.innerHTML = html;
    console.log("[TDB] Layout créé avec", record.data.line_ids.records.length, "éléments");
    
    // Ajouter les gestionnaires d'événements pour les liens "Ouvrir en plein écran"
    setTimeout(() => {
        this.attachOpenFilterLinks();
        this.attachEditFilterLinks();
    }, 100);
    }

    attachOpenFilterLinks() {
        const links = document.querySelectorAll('.open-filter-link');
        console.log("[TDB] Attaching event listeners to", links.length, "links");
        
        links.forEach(link => {
            link.addEventListener('click', async (e) => {
                e.preventDefault();
                const lineId = parseInt(link.dataset.lineId);
                
                if (!lineId) {
                    console.warn("[TDB] Pas de lineId pour ce lien");
                    return;
                }
                
                await this.openFilterFullScreen(lineId);
            });
        });
    }

    attachEditFilterLinks() {
        const links = document.querySelectorAll('.edit-filter-link');
        console.log("[TDB] Attaching event listeners to", links.length, "edit filter links");
        
        links.forEach(link => {
            link.addEventListener('click', async (e) => {
                e.preventDefault();
                const lineId = parseInt(link.dataset.lineId);
                
                if (!lineId) {
                    console.warn("[TDB] Pas de lineId pour ce lien d'édition");
                    return;
                }
                
                await this.editFilter(lineId);
            });
        });
    }

    async openFilterFullScreen(lineId) {
        try {
            console.log("[TDB] Ouverture du filtre pour la ligne", lineId, "via action_open_filter");
            
            // Appeler la méthode Python action_open_filter sur le modèle is.tableau.de.bord.line
            const result = await rpc("/web/dataset/call_kw/is.tableau.de.bord.line/action_open_filter", {
                model: 'is.tableau.de.bord.line',
                method: 'action_open_filter',
                args: [[lineId]],
                kwargs: {}
            });
            
            if (result && result.type) {
                // Exécuter l'action retournée par Python
                await this.actionService.doAction(result);
            } else {
                console.warn("[TDB] Aucune action retournée par action_open_filter");
            }
            
        } catch (error) {
            console.error("[TDB] Erreur lors de l'ouverture du filtre:", error);
        }
    }

    async editFilter(lineId) {
        try {
            console.log("[TDB] Édition du filtre pour la ligne", lineId, "via action_edit_filter");
            
            // Appeler la méthode Python action_edit_filter sur le modèle is.tableau.de.bord.line
            const result = await rpc("/web/dataset/call_kw/is.tableau.de.bord.line/action_edit_filter", {
                model: 'is.tableau.de.bord.line',
                method: 'action_edit_filter',
                args: [[lineId]],
                kwargs: {}
            });
            
            if (result && result.type) {
                // Exécuter l'action retournée par Python
                await this.actionService.doAction(result);
            } else {
                console.warn("[TDB] Aucune action retournée par action_edit_filter");
            }
            
        } catch (error) {
            console.error("[TDB] Erreur lors de l'édition du filtre:", error);
        }
    }

    async loadDashboardItems() {
        const record = this.model.root;
        if (!record?.data?.line_ids?.records) return;

    console.log("[TDB] Chargement des éléments du dashboard...");

    for (const lineRecord of record.data.line_ids.records) {
            const line = lineRecord.data;
            let filterId = null;
            if (Array.isArray(line.filter_id)) {
                filterId = line.filter_id[0];
            } else if (line.filter_id && typeof line.filter_id === 'object') {
                filterId = line.filter_id.id || line.filter_id.resId || null;
            } else if (typeof line.filter_id === 'number') {
                filterId = line.filter_id;
            }
            if (filterId) {
        // Utiliser l'id serveur de la ligne si disponible pour le backend (overrides)
        const serverLineId = lineRecord.resId || line.id || (line._values && line._values.id) || lineRecord.id;
        console.log("[TDB] Ligne", lineRecord.id, "(server:", serverLineId, ") filterId:", filterId, "name:", line.name, "width:", line.width, "height:", line.height);
                const overrides = {
                    display_mode: line.display_mode,
                    graph_chart_type: line.graph_chart_type,
                    graph_aggregator: line.graph_aggregator,
                    pivot_row_groupby: line.pivot_row_groupby,
                    pivot_column_groupby: line.pivot_col_groupby,
                    pivot_measures: line.pivot_measure,
                };
                await this.loadFilterData(lineRecord.id, filterId, serverLineId, overrides);
            } else {
                this.renderError(lineRecord.id, "Aucun filtre sélectionné");
            }
        }
    }

    async loadFilterData(lineId, filterId, backendLineId, overrides) {
        try {
            const lid = backendLineId || lineId;
            const dashboardId = this.model?.root?.resId;
            console.log("[TDB] Appel RPC /tableau_de_bord/get_filter_data/", filterId, 'line', lid, '(container', lineId, ") overrides:", overrides, 'dashboard:', dashboardId);
            const data = await rpc("/tableau_de_bord/get_filter_data/" + filterId, { line_id: lid, overrides, dashboard_id: dashboardId });
            console.log("[TDB] Données reçues:", data);
            this.renderFilterData(lineId, data);
        } catch (error) {
            console.error("Erreur lors du chargement des données:", error);
            this.renderError(lineId, "Erreur lors du chargement des données: " + error.message);
        }
    }

    renderFilterData(lineId, data) {
        const container = document.getElementById(`dashboard_item_${lineId}`);
        if (!container) {
            console.warn("[TDB] Container non trouvé pour lineId:", lineId);
            return;
        }

        if (data.error) {
            this.renderError(lineId, data.error);
            return;
        }

        switch (data.type) {
            case 'list':
                this.renderListData(container, data);
                break;
            case 'graph':
                this.renderGraphData(container, data);
                break;
            case 'pivot':
                this.renderPivotData(container, data);
                break;
            default:
                this.renderError(lineId, "Type de données non supporté: " + data.type);
        }
    }

    renderListData(container, data) {
        if (!data.data || data.data.length === 0) {
            container.innerHTML = '<div class="alert alert-info m-2">Aucune donnée à afficher</div>';
            return;
        }

        console.log('[TDB] Render LIST with fields:', data.fields);
        
        // Filtrer les champs invalides
        const validFields = (data.fields || []).filter(f => f !== null && f !== undefined);
        
        if (validFields.length === 0) {
            container.innerHTML = '<div class="alert alert-warning m-2">Aucun champ à afficher</div>';
            return;
        }
        
        let html = '<div class="table-responsive h-100"><table class="table table-sm table-striped mb-0">';
        
        // En-têtes
        html += '<thead><tr>';
        for (const f of validFields) {
            const label = typeof f === 'string' ? f : (f?.string || f?.name || 'Sans nom');
            html += `<th>${label}</th>`;
        }
        html += '</tr></thead>';
        
        // Données
        html += '<tbody>';
        for (const row of data.data) {
            html += '<tr>';
            for (const f of validFields) {
                const name = typeof f === 'string' ? f : (f?.name || '');
                let val = row[name];
                if (Array.isArray(val)) {
                    // many2one: [id, display]
                    val = val.length > 1 ? val[1] : val[0];
                } else if (val && typeof val === 'object') {
                    // divers formats -> stringify propre
                    val = val.display_name || val.name || JSON.stringify(val);
                }
                html += `<td>${val ?? ''}</td>`;
            }
            html += '</tr>';
        }
        html += '</tbody>';
        
        html += `</table></div>`;
        html += `<div class="text-muted small p-2 border-top">Total: ${data.count} enregistrement(s)</div>`;
        
        container.innerHTML = html;
        container.className = "dashboard-item h-100 d-flex flex-column";
    }

    renderGraphData(container, data) {
        // Préparer un canvas pour dessiner un vrai graphique si Chart.js est dispo
        const chartId = `chart_${Math.random().toString(36).slice(2)}`;
        let html = `<div class="p-2 h-100 d-flex flex-column">
            <div class="d-flex align-items-center justify-content-between mb-2">
                <h6 class="mb-0">${data.data?.datasets?.[0]?.label || 'Graphique'}</h6>
            </div>
            <div class="flex-grow-1 position-relative">
                <canvas id="${chartId}" style="max-height: 100%;"></canvas>
            </div>
        </div>`;
        container.innerHTML = html;
        container.className = "dashboard-item h-100";

    console.log('[TDB] Render GRAPH with', data);
    const dataset = data.data?.datasets?.[0];
        const labels = data.data?.labels || [];
        if (!dataset) {
            container.innerHTML = '<div class="alert alert-info m-2">Aucune donnée graphique disponible</div>';
            return;
        }

        // Si Chart global est disponible (injecté par Odoo web), dessiner; sinon fallback texte
    const el = document.getElementById(chartId);
    console.log('[TDB] Chart available?', !!window.Chart, 'canvas?', !!el);
    if (window.Chart && el) {
            new window.Chart(el.getContext('2d'), {
                type: data.chart_type || 'bar',
                data: {
                    labels,
                    datasets: [{
                        label: dataset.label,
                        data: dataset.data,
                        backgroundColor: dataset.backgroundColor || '#1f77b4',
                        borderWidth: 1,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true } }
                }
            });
        } else {
            // Fallback: valeurs en gros comme avant
            let fallback = '<div class="text-center p-4 h-100 d-flex flex-column justify-content-center">';
            fallback += `<h5 class="mb-3">${dataset.label}</h5>`;
            fallback += '<div class="row flex-grow-1 align-items-center">';
            for (let i = 0; i < labels.length; i++) {
                const value = dataset.data[i];
                const label = labels[i];
                fallback += `<div class="col text-center">
                    <div class="display-4 text-primary mb-2">${value}</div>
                    <div class="small text-muted">${label}</div>
                </div>`;
            }
            fallback += '</div></div>';
            container.innerHTML = fallback;
        }
    }

    renderPivotData(container, data) {
        console.log('[TDB] Render PIVOT with', data);
        // Support 2D matrix: data.data = { columns: [{label}], rows: [{row, values:[]}] }
        if (data.data && data.data.columns && data.data.rows) {
            const cols = data.data.columns;
            const rows = data.data.rows;
            let html = '<div class="h-100 d-flex flex-column"><div class="table-responsive flex-grow-1"><table class="table table-sm table-striped mb-0">';
            // header
            html += '<thead><tr><th></th>';
            for (const c of cols) html += `<th class="text-end">${c.label}</th>`;
            html += '<th class="text-end">Total</th></tr></thead>';
            // body
            html += '<tbody>';
            for (const r of rows) {
                const total = (r.values || []).reduce((a, b) => a + (b || 0), 0);
                html += `<tr><td class="fw-bold">${r.row}</td>`;
                for (const v of (r.values || [])) html += `<td class="text-end">${v ?? 0}</td>`;
                html += `<td class="text-end fw-bold">${total}</td></tr>`;
            }
            // footer totals by column
            const colTotals = cols.map((_, i) => rows.reduce((a, r) => a + (r.values?.[i] || 0), 0));
            const grand = colTotals.reduce((a, b) => a + b, 0);
            html += '<tr class="table-light"><td class="fw-bold">Total</td>';
            for (const t of colTotals) html += `<td class="text-end fw-bold">${t}</td>`;
            html += `<td class="text-end fw-bold">${grand}</td></tr>`;
            html += '</tbody></table></div></div>';
            container.innerHTML = html;
            container.className = "dashboard-item h-100";
            return;
        }

        // 1D list fallback
        let html = '<div class="h-100 d-flex flex-column"><div class="table-responsive flex-grow-1"><table class="table table-sm mb-0">';
        html += '<tbody>';
        for (const row of (data.data || [])) {
            html += `<tr><td>${row.row}</td><td class="text-end fw-bold">${row.value}</td></tr>`;
        }
        html += '</tbody></table></div></div>';
        container.innerHTML = html;
        container.className = "dashboard-item h-100";
    }

    renderError(lineId, message) {
        const container = document.getElementById(`dashboard_item_${lineId}`);
        if (container) {
            container.innerHTML = `<div class="alert alert-warning m-2 h-100 d-flex align-items-center justify-content-center text-center">${message}</div>`;
            container.className = "dashboard-item h-100";
        }
    }
}

// Enregistrer le contrôleur personnalisé pour remplacer le contrôleur form standard
// quand nous sommes en mode dashboard
const originalFormController = registry.category("views").get("form");

registry.category("views").add("form", {
    ...originalFormController,
    Controller: class extends originalFormController.Controller {
        setup() {
            // Toujours initialiser le contrôleur parent
            super.setup();
            // Puis si dashboard, déclencher la logique spécifique
            if (this.props.context?.dashboard_mode) {
                try {
                    DashboardFormController.prototype.setup.call(this);
                } catch (e) {
                    console.error("Erreur setup dashboard:", e);
                }
            }
        }
        
        // Déléguer les autres méthodes si nécessaire
        async setupDashboard() {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.setupDashboard.call(this);
            }
        }
        
        createDashboardLayout() {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.createDashboardLayout.call(this);
            }
        }
        
        async loadDashboardItems() {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.loadDashboardItems.call(this);
            }
        }
        
        async loadFilterData(lineId, filterId, backendLineId, overrides) {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.loadFilterData.call(this, lineId, filterId, backendLineId, overrides);
            }
        }
        
        renderFilterData(lineId, data) {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.renderFilterData.call(this, lineId, data);
            }
        }
        
        renderListData(container, data) {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.renderListData.call(this, container, data);
            }
        }
        
        renderGraphData(container, data) {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.renderGraphData.call(this, container, data);
            }
        }
        
        renderPivotData(container, data) {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.renderPivotData.call(this, container, data);
            }
        }
        
        renderError(lineId, message) {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.renderError.call(this, lineId, message);
            }
        }
        
        attachOpenFilterLinks() {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.attachOpenFilterLinks.call(this);
            }
        }
        
        attachEditFilterLinks() {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.attachEditFilterLinks.call(this);
            }
        }
        
        async openFilterFullScreen(lineId) {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.openFilterFullScreen.call(this, lineId);
            }
        }
        
        async editFilter(lineId) {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.editFilter.call(this, lineId);
            }
        }
    }
}, { force: true });
