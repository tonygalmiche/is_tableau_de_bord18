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
                this.setupDashboard();
            }
        });
    }

    async setupDashboard() {
        // Vérifier si l'utilisateur est gestionnaire
        await this.checkUserPermissions();
        
        // Attendre que le formulaire soit complètement chargé
        setTimeout(() => {
            this.createDashboardLayout();
            this.loadDashboardItems();
        }, 1500);
    }

    async checkUserPermissions() {
        try {
            // Vérifier si l'utilisateur appartient au groupe manager via notre méthode custom
            const result = await rpc("/web/dataset/call_kw/is.tableau.de.bord/check_is_manager", {
                model: 'is.tableau.de.bord',
                method: 'check_is_manager',
                args: [],
                kwargs: {},
            });
            this.isManager = result;
        } catch (error) {
            // En cas d'erreur, considérer l'utilisateur comme non-manager
            this.isManager = false;
        }
    }

    createDashboardLayout() {
        const record = this.model.root;
        if (!record?.data?.line_ids?.records) {
            return;
        }

        const container = document.getElementById('dashboard_container');
        if (!container) {
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
            
            // Boutons d'édition uniquement pour les gestionnaires
            let editButtons = '';
            if (this.isManager) {
                editButtons = `
                    <a href="#" class="btn btn-sm btn-outline-info edit-line-link" data-line-id="${serverLineId}" title="Modifier la ligne du tableau de bord">
                        <i class="fa fa-pencil"></i>
                    </a>
                    <a href="#" class="btn btn-sm btn-outline-secondary edit-filter-link" data-line-id="${serverLineId}" title="Modifier le filtre">
                        <i class="fa fa-search"></i>
                    </a>
                `;
            }
            
            html += `
                <div class="col-md-${isNaN(widthCol) ? 6 : widthCol} mb-3">
                    <div class="card h-100">
                        <div class="card-header d-flex justify-content-between align-items-start">
                            <div>
                                <h5 class="card-title mb-0">${line.name || 'Sans nom'}</h5>
                            </div>
                            <div class="d-flex gap-2">
                                <a href="#" class="btn btn-sm btn-outline-primary open-filter-link" data-line-id="${serverLineId}" title="Ouvrir la recherche complète en plein écran">
                                    <i class="fa fa-expand"></i> Plein écran
                                </a>
                                ${editButtons}
                            </div>
                        </div>
                        <div class="card-body p-0" style="height: ${isNaN(heightPx) ? 400 : heightPx}px; overflow: auto;">
                            <div id="dashboard_item_${lineRecord.id}" class="dashboard-item h-100 d-flex align-items-center justify-content-center">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Chargement...</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }



        
        html += '</div>';
    container.innerHTML = html;
    
    // Ajouter les gestionnaires d'événements
    setTimeout(() => {
        this.attachOpenFilterLinks();
        // Boutons d'édition uniquement pour les gestionnaires
        if (this.isManager) {
            this.attachEditLineLinks();
            this.attachEditFilterLinks();
        }
    }, 100);
    }

    attachOpenFilterLinks() {
        const links = document.querySelectorAll('.open-filter-link');
        
        links.forEach(link => {
            link.addEventListener('click', async (e) => {
                e.preventDefault();
                const lineId = parseInt(link.dataset.lineId);
                
                if (!lineId) {
                    return;
                }
                
                await this.openFilterFullScreen(lineId);
            });
        });
    }

    attachEditFilterLinks() {
        const links = document.querySelectorAll('.edit-filter-link');
        
        links.forEach(link => {
            link.addEventListener('click', async (e) => {
                e.preventDefault();
                const lineId = parseInt(link.dataset.lineId);
                
                if (!lineId) {
                    return;
                }
                
                await this.editFilter(lineId);
            });
        });
    }

    attachEditLineLinks() {
        const links = document.querySelectorAll('.edit-line-link');
        
        links.forEach(link => {
            link.addEventListener('click', async (e) => {
                e.preventDefault();
                const lineId = parseInt(link.dataset.lineId);
                
                if (!lineId) {
                    return;
                }
                
                await this.editLine(lineId);
            });
        });
    }

    async openFilterFullScreen(lineId) {
        try {
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
            } 
            
        } catch (error) {
            console.error("[TDB] Erreur lors de l'ouverture du filtre:", error);
        }
    }

    async editFilter(lineId) {
        try {
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
            }
            
        } catch (error) {
            console.error("[TDB] Erreur lors de l'édition du filtre:", error);
        }
    }

    async editLine(lineId) {
        try {
            // Ouvrir le formulaire de la ligne en plein écran avec la vue dédiée
            await this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Modifier la ligne du tableau de bord',
                res_model: 'is.tableau.de.bord.line',
                res_id: lineId,
                views: [[false, 'form']],
                view_mode: 'form',
                target: 'current',
                context: {
                    'form_view_ref': 'is_tableau_de_bord18.view_is_tableau_de_bord_line_edit_form'
                }
            });
            
        } catch (error) {
            console.error("[TDB] Erreur lors de l'édition de la ligne:", error);
        }
    }

    async loadDashboardItems() {
        const record = this.model.root;
        if (!record?.data?.line_ids?.records) return;

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
                const overrides = {
                    display_mode: line.display_mode,
                    graph_chart_type: line.graph_chart_type,
                    graph_aggregator: line.graph_aggregator,
                    pivot_row_groupby: line.pivot_row_groupby,
                    pivot_column_groupby: line.pivot_col_groupby,
                    pivot_measures: line.pivot_measure,
                    pivot_sort_by: line.pivot_sort_by,
                    pivot_sort_order: line.pivot_sort_order,
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
            const data = await rpc("/tableau_de_bord/get_filter_data/" + filterId, { line_id: lid, overrides, dashboard_id: dashboardId });
            this.renderFilterData(lineId, data);
        } catch (error) {
            this.renderError(lineId, "Erreur lors du chargement des données: " + error.message);
        }
    }

    renderFilterData(lineId, data) {
        const container = document.getElementById(`dashboard_item_${lineId}`);
        if (!container) {
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
                // Ne pas afficher false/null/undefined comme texte
                let displayVal = '';
                if (val !== null && val !== undefined && val !== false) {
                    displayVal = val;
                }
                html += `<td>${displayVal}</td>`;
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

    const dataset = data.data?.datasets?.[0];
        const labels = data.data?.labels || [];
        if (!dataset) {
            container.innerHTML = '<div class="alert alert-info m-2">Aucune donnée graphique disponible</div>';
            return;
        }

        // Si Chart global est disponible (injecté par Odoo web), dessiner; sinon fallback texte
    const el = document.getElementById(chartId);
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

    formatNumber(value) {
        if (value === null || value === undefined) return '0';
        // Formater avec séparateur de milliers en nombres entiers uniquement
        const num = parseFloat(value);
        if (isNaN(num)) return value;
        // Arrondir à l'entier le plus proche
        const rounded = Math.round(num);
        return rounded.toLocaleString('fr-FR');
    }

    renderPivotData(container, data) {
        // Support 2D matrix: data.data = { columns: [{label}], rows: [{row, values:[]}], measure_label, row_label, col_label }
        if (data.data && data.data.columns && data.data.rows) {
            const cols = data.data.columns;
            const rows = data.data.rows;
            const measureLabel = data.data.measure_label || 'Total';
            const rowLabel = data.data.row_label || 'Lignes';
            const colLabel = data.data.col_label || 'Colonnes';
            const colTotals = data.data.col_totals || null;
            const grandTotal = data.data.grand_total || null;
            const showRowTotals = rows.length > 0 && rows[0].hasOwnProperty('row_total');
            const showColTotals = colTotals !== null;
            
            let html = '<div class="h-100 d-flex flex-column">';
            html += '<div class="px-2 pt-2"><small class="text-muted">Mesure: <strong>' + measureLabel + '</strong></small></div>';
            html += '<div class="table-responsive flex-grow-1 px-2"><table class="table table-sm table-hover mb-0" style="font-size: 0.9rem;">';
            
            // header avec libellés améliorés
            html += '<thead class="table-light"><tr>';
            html += '<th class="border-end" style="background-color: #f8f9fa;">' + rowLabel + '</th>';
            for (const c of cols) html += '<th class="text-end">' + c.label + '</th>';
            if (showRowTotals) {
                html += '<th class="text-end border-start fw-bold" style="background-color: #e9ecef;">Total</th>';
            }
            html += '</tr></thead>';
            
            // body
            html += '<tbody>';
            for (const r of rows) {
                html += '<tr><td class="border-end fw-bold" style="background-color: #fafbfc;">' + r.row + '</td>';
                for (const v of (r.values || [])) {
                    const formattedValue = this.formatNumber(v);
                    html += '<td class="text-end">' + formattedValue + '</td>';
                }
                if (showRowTotals) {
                    const total = r.row_total !== undefined ? r.row_total : (r.values || []).reduce((a, b) => a + (b || 0), 0);
                    const formattedTotal = this.formatNumber(total);
                    html += '<td class="text-end border-start fw-bold" style="background-color: #f8f9fa;">' + formattedTotal + '</td>';
                }
                html += '</tr>';
            }
            
            // footer totals by column
            if (showColTotals) {
                html += '<tr class="table-secondary border-top border-2"><td class="border-end fw-bold">Total</td>';
                for (const t of colTotals) {
                    const formattedValue = this.formatNumber(t);
                    html += '<td class="text-end fw-bold">' + formattedValue + '</td>';
                }
                if (showRowTotals && grandTotal !== null) {
                    const formattedGrand = this.formatNumber(grandTotal);
                    html += '<td class="text-end border-start fw-bold">' + formattedGrand + '</td>';
                } else if (showRowTotals) {
                    // Calculer le grand total si pas fourni
                    const grand = colTotals.reduce((a, b) => a + b, 0);
                    const formattedGrand = this.formatNumber(grand);
                    html += '<td class="text-end border-start fw-bold">' + formattedGrand + '</td>';
                }
                html += '</tr>';
            }
            html += '</tbody></table></div></div>';
            container.innerHTML = html;
            container.className = "dashboard-item h-100";
            return;
        }

        // 1D list fallback avec libellés améliorés
        const measureLabel = data.measure_label || 'Valeur';
        const rowLabel = data.row_label || 'Lignes';
        const showTotal = data.total !== undefined;
        
        let html = '<div class="h-100 d-flex flex-column">';
        html += '<div class="px-2 pt-2"><small class="text-muted">Mesure: <strong>' + measureLabel + '</strong></small></div>';
        html += '<div class="table-responsive flex-grow-1 px-2"><table class="table table-sm table-hover mb-0" style="font-size: 0.9rem;">';
        html += '<thead class="table-light"><tr><th>' + rowLabel + '</th><th class="text-end">' + measureLabel + '</th></tr></thead>';
        html += '<tbody>';
        
        for (const row of (data.data || [])) {
            const formattedValue = this.formatNumber(row.value);
            html += '<tr><td>' + row.row + '</td><td class="text-end fw-bold">' + formattedValue + '</td></tr>';
        }
        
        // Ajouter une ligne de total UNIQUEMENT si fourni par le backend
        if (showTotal) {
            const formattedTotal = this.formatNumber(data.total);
            html += '<tr class="table-secondary border-top border-2"><td class="fw-bold">Total</td><td class="text-end fw-bold">' + formattedTotal + '</td></tr>';
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
        async checkUserPermissions() {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.checkUserPermissions.call(this);
            }
        }
        
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
        
        attachEditLineLinks() {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.attachEditLineLinks.call(this);
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
        
        async editLine(lineId) {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.editLine.call(this, lineId);
            }
        }
        
        formatNumber(value) {
            if (this.props.context?.dashboard_mode) {
                return DashboardFormController.prototype.formatNumber.call(this, value);
            }
            // Fallback si pas en mode dashboard
            if (value === null || value === undefined) return '0';
            const num = parseFloat(value);
            if (isNaN(num)) return value;
            if (Number.isInteger(num)) {
                return num.toLocaleString('fr-FR');
            }
            return num.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
    }
}, { force: true });
