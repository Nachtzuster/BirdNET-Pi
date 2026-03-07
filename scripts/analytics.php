<?php
// scripts/analytics.php
?>
<style>
/* Layout */
.analytics-dashboard {
    padding: 20px 40px;
    width: 100%;
    max-width: none !important;
    margin: 0;
    box-sizing: border-box;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
.dashboard-header { margin-bottom: 24px; }
.dashboard-header h1 { font-size: 1.8rem; margin: 0; color: var(--text-heading); }
.dashboard-header p { margin: 4px 0 0 0; color: var(--text-muted, #64748b); }

/* KPI Grid */
.kpi-grid {
    display: grid !important;
    grid-template-columns: repeat(4, 1fr) !important;
    gap: 15px !important;
    margin-bottom: 32px !important;
    width: 100% !important;
    justify-items: stretch !important;
}
@media (max-width: 1200px) {
    .kpi-grid { grid-template-columns: repeat(2, 1fr) !important; }
}
@media (max-width: 768px) {
    .kpi-grid { grid-template-columns: 1fr !important; }
}
.kpi-card {
    background: var(--bg-card);
    padding: 24px;
    border-radius: 16px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
    display: flex;
    align-items: center;
    gap: 20px;
    border: 1px solid var(--border-light, #f1f5f9);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    width: 100% !important;
    max-width: none !important;
    min-width: 0;
    margin: 0 !important;
    box-sizing: border-box !important;
}
.kpi-card:hover { 
    transform: translateY(-4px); 
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}
.kpi-icon {
    width: 56px; height: 56px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.8rem;
    flex-shrink: 0;
}
.kpi-icon.total { background: #eff6ff; color: #3b82f6; }
.kpi-icon.species { background: #f0fdf4; color: #22c55e; }
.kpi-icon.confidence { background: #fff7ed; color: #f97316; }
.kpi-icon.common { background: #faf5ff; color: #a855f7; }
.kpi-info { 
    display: flex; 
    flex-direction: column; 
    flex-grow: 1; 
    min-width: 0;
    overflow: hidden;
}
.kpi-label { font-size: 0.85rem; font-weight: 500; color: var(--text-muted, #64748b); }
.kpi-value { font-size: 1.5rem; font-weight: 700; margin: 2px 0; color: var(--text-primary); }
.kpi-period { font-size: 0.75rem; color: var(--text-muted, #94a3b8); }

/* Filter Bar */
.filter-card {
    background: var(--bg-card);
    padding: 24px;
    border-radius: 12px;
    margin-bottom: 24px;
    border: 1px solid var(--border-light, #f1f5f9);
}
.filter-card h3 { margin: 0 0 16px 0; font-size: 1.1rem; }
.filter-controls {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-wrap: wrap;
    gap: 20px;
}
.filter-group { display: flex; flex-direction: column; gap: 8px; }
.filter-group label { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); }
.styled-select {
    padding: 8px 12px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--bg-card);
    color: var(--text-primary);
    min-width: 200px;
    outline: none;
}
.filter-actions { display: flex; gap: 12px; }
.btn-reset {
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-weight: 500;
    cursor: pointer;
}
.btn-apply {
    background: #2563eb !important;
    color: white !important;
    border: none !important;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s, color 0.2s;
    text-decoration: none !important;
}
.btn-apply:hover { 
    background: #1d4ed8 !important;
    color: white !important;
}

#ebird-export-btn {
    box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
}

/* Viz Grid */
.viz-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(48%, 1fr));
    gap: 24px;
    margin-bottom: 24px;
}
.viz-card {
    background: var(--bg-card);
    padding: 24px;
    border-radius: 12px;
    border: 1px solid var(--border-light, #f1f5f9);
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    position: relative;
}
.viz-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
}
.viz-card h3 { margin: 0; font-size: 1rem; font-weight: 600; }
.btn-filter {
    background: #f1f5f9;
    color: #64748b;
    border: 1px solid #e2e8f0;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    transition: all 0.2s;
}
.btn-filter:hover { background: #e2e8f0; color: #1e293b; }
.btn-reset-chart {
    background: transparent;
    color: var(--text-muted);
    border: 1px solid var(--border-light);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
}
.btn-reset-chart:hover { background: var(--bg-page); color: var(--text-primary); }
.chart-sub { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 16px; margin-top: 4px; }

/* Modal */
.picker-modal {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    width: 90%;
    max-width: 500px;
    z-index: 100000;
    display: none;
    flex-direction: column;
    padding: 24px;
}
.modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    backdrop-filter: blur(4px);
    z-index: 99999;
    display: none;
}
.picker-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.picker-header h4 { margin: 0; font-size: 1.2rem; }
.picker-search { margin-bottom: 16px; }
.picker-input {
    width: 100%;
    padding: 10px 14px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--bg-page);
    color: var(--text-primary);
    outline: none;
}
.picker-results {
    max-height: 200px;
    overflow-y: auto;
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 16px;
    display: none;
}
.result-item {
    padding: 8px 12px;
    cursor: pointer;
    border-bottom: 1px solid var(--border-light);
}
.result-item:hover { background: var(--hover-color, #f8fafc); }
.picker-selected {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 20px;
}
.selected-tag {
    background: #eff6ff;
    color: #2563eb;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;
}
.tag-remove { cursor: pointer; opacity: 0.6; }
.tag-remove:hover { opacity: 1; }
.picker-footer { display: flex; justify-content: flex-end; gap: 12px; }

/* Chart Sizing */
.chart-container { position: relative; height: 300px; width: 100%; }
.chart-container.tall { height: 400px; }

/* Full Visualizations Layout */
.full-viz {
    display: flex;
    flex-direction: column;
    gap: 24px;
    margin-bottom: 24px;
}

/* New Species List Styling */
.new-species-container {
    height: 300px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
}
.empty-state {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-style: italic;
    font-size: 0.9rem;
}
.new-species-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px;
    border-radius: 8px;
    background: var(--bg-page, #f8fafc);
}
.ns-icon { 
    width: 40px; height: 40px; 
    border-radius: 50%; 
    background: #fff; 
    display: flex; 
    align-items: center; 
    justify-content: center; 
    font-size: 1.2rem; 
    border: 1px solid var(--border); 
}
.ns-info { display: flex; flex-direction: column; }
.ns-name { font-weight: 600; font-size: 0.95rem; }
.ns-sci { font-size: 0.8rem; font-style: italic; color: var(--text-muted); }
.ns-date { font-size: 0.75rem; color: #22c55e; font-weight: 600; }

/* Recent Detections Table Styling */
.table-container { overflow-x: auto; margin-top: 16px; }
.styled-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.styled-table th { 
    text-align: left; 
    padding: 12px 16px; 
    border-bottom: 2px solid var(--border); 
    color: var(--text-muted); 
    font-size: 0.8rem; 
    text-transform: uppercase; 
    letter-spacing: 0.05em; 
}
.styled-table td { padding: 12px 16px; border-bottom: 1px solid var(--border-light); vertical-align: middle; }
.styled-table tr:last-child td { border-bottom: none; }
.species-details { display: flex; flex-direction: column; text-align: left; }
.species-name { font-weight: 600; color: var(--text-primary); }
.species-sci { font-size: 0.75rem; font-style: italic; color: var(--text-muted); }
.td-species { display: flex; align-items: center; gap: 12px; }

/* Confidence Indicators */
.conf-bar-container { display: flex; align-items: center; gap: 8px; }
.conf-bar-bg { flex: 1; height: 6px; background: #f1f5f9; border-radius: 3px; overflow: hidden; min-width: 60px; }
.conf-bar-fill { height: 100%; border-radius: 3px; }
.conf-label { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); min-width: 40px; }

/* Time Badges */
.badge-time { 
    padding: 4px 8px; 
    border-radius: 12px; 
    font-size: 0.75rem; 
    font-weight: 600; 
    background: #f1f5f9; 
    color: #64748b; 
}

</style>
<div class="modal-overlay" id="species-picker-overlay"></div>
<div class="picker-modal" id="species-picker">
    <div class="picker-header">
        <h4 id="picker-title">Select Species</h4>
        <button class="btn-reset" onclick="closePicker()">✕</button>
    </div>
    <div class="picker-search">
        <input type="text" class="picker-input" id="species-search-input" placeholder="Search for a species...">
    </div>
    <div class="picker-results" id="search-results"></div>
    <div class="picker-selected" id="selected-species-container"></div>
    <div class="picker-footer">
        <button class="btn-reset" onclick="closePicker()">Cancel</button>
        <button class="btn-apply" onclick="saveSpeciesSelection()">Apply</button>
    </div>
</div>
<div class="analytics-dashboard">
    <!-- Header -->
    <div class="dashboard-header">
        <h1>Analytics Dashboard</h1>
        <p>Comprehensive insights and detection patterns.</p>
    </div>

    <div class="kpi-grid" id="stats-kpi">
        <div class="kpi-card">
            <div class="kpi-info">
                <span class="kpi-label">Total Detections</span>
                <h2 class="kpi-value" id="kpi-total">-</h2>
                <span class="kpi-period">Last 7 days</span>
            </div>
            <div class="kpi-icon total">🔭</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-info">
                <span class="kpi-label">Unique Species</span>
                <h2 class="kpi-value" id="kpi-unique">-</h2>
                <span class="kpi-period">Last 7 days</span>
            </div>
            <div class="kpi-icon species">🐦</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-info">
                <span class="kpi-label">Avg. Confidence</span>
                <h2 class="kpi-value" id="kpi-conf">-</h2>
                <span class="kpi-period">Last 7 days</span>
            </div>
            <div class="kpi-icon confidence">ℹ️</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-info" id="kpi-common-container">
                <span class="kpi-label">Most Common</span>
                <h2 class="kpi-value" id="kpi-common" style="font-size: 1.2rem;">-</h2>
                <span class="kpi-period" id="kpi-common-sub">-</span>
            </div>
            <div class="kpi-icon common">⬆️</div>
        </div>
    </div>

    <!-- Filter Bar -->
    <div class="filter-card">
        <h3>Filter Data</h3>
        <div class="filter-controls">
            <div class="filter-group">
                <label for="time-period">Time Period</label>
                <select id="time-period" class="styled-select">
                    <option value="1">Last 24 Hours</option>
                    <option value="7" selected>Last 7 Days</option>
                    <option value="30">Last 30 Days</option>
                    <option value="90">Last 90 Days</option>
                    <option value="365">Last Year</option>
                </select>
            </div>
            <div class="filter-actions">
                <button type="button" class="btn-reset" onclick="resetFilters()">Reset</button>
                <button type="button" class="btn-apply" onclick="applyFilters()">Apply Filters</button>
            </div>
        </div>
    </div>

    <!-- Main Grid -->
    <div class="viz-grid">
        <div class="viz-card">
            <h3>Top 10 Species</h3>
            <div class="chart-container">
                <canvas id="topSpeciesChart"></canvas>
            </div>
        </div>
        <div class="viz-card">
            <h3>Detections by Time of Day</h3>
            <div class="chart-container">
                <canvas id="dayActivityChart"></canvas>
            </div>
        </div>
        <div class="viz-card">
            <h3>Detection Trends</h3>
            <div class="chart-container">
                <canvas id="mainTrendsChart"></canvas>
            </div>
        </div>
        <div class="viz-card">
            <h3>New Species Detected</h3>
            <div class="new-species-container" id="new-species-list">
                <div class="empty-state">No new species detected in this period.</div>
            </div>
        </div>
    </div>

    <!-- Full Width Visualizations -->
    <div class="full-viz">
        <div class="viz-card">
            <div class="viz-card-header">
                <h3>Detection Patterns by Time of Day</h3>
                <div style="display: flex; gap: 8px;">
                    <button class="btn-reset-chart" onclick="resetSpeciesFilter('patterns')">Reset</button>
                    <button class="btn-filter" onclick="openPicker('patterns')">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z"/></svg>
                        Filter
                    </button>
                </div>
            </div>
            <p class="chart-sub" id="patterns-sub">Showing average detection counts throughout the day for selected species</p>
            <div class="chart-container tall">
                <canvas id="speciesPatternsChart"></canvas>
            </div>
        </div>
        <div class="viz-card">
            <div class="viz-card-header">
                <h3>Species Detection Trends</h3>
                <div style="display: flex; gap: 8px;">
                    <button class="btn-reset-chart" onclick="resetSpeciesFilter('trends')">Reset</button>
                    <button class="btn-filter" onclick="openPicker('trends')">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z"/></svg>
                        Filter
                    </button>
                </div>
            </div>
            <p class="chart-sub" id="trends-sub">Shows detection trends over time for selected species</p>
            <div class="chart-container tall">
                <canvas id="speciesTrendsChart"></canvas>
            </div>
        </div>
        <div class="viz-card">
            <h3>Species Diversity Over Time</h3>
            <p class="chart-sub">Shows the number of unique species detected per day</p>
            <div class="chart-container tall">
                <canvas id="diversityChart"></canvas>
            </div>
        </div>
    </div>

    <!-- Recent Detections List -->
    <div class="viz-card full-width">
        <h3>Recent Detections</h3>
        <div class="table-container">
            <table class="styled-table">
                <thead>
                    <tr>
                        <th>Date & Time</th>
                        <th>Species</th>
                        <th>Confidence</th>
                        <th>Time of Day</th>
                    </tr>
                </thead>
                <tbody id="recent-detections-body">
                    <!-- Rows injected via JS -->
                </tbody>
            </table>
        </div>
    </div>
</div>

<?php include('history.php'); ?>



<script src="static/Chart.bundle.js"></script>
<script>
let charts = {};
let colorPalette = [
    '#3b82f6', '#22c55e', '#eab308', '#ec4899', '#8b5cf6', 
    '#f97316', '#06b6d4', '#ef4444', '#10b981', '#6366f1'
];

document.addEventListener("DOMContentLoaded", function() {
    initCharts();
    loadAllData();
});

function applyFilters() {
    loadAllData();
}

function resetFilters() {
    document.getElementById('time-period').value = '7';
    loadAllData();
}

function initCharts() {
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const fontColor = isDark ? '#e2e8f0' : '#475569';
    const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)';
    
    Chart.defaults.global.defaultFontColor = fontColor;
    Chart.defaults.global.defaultFontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif';

    const commonLineOptions = {
        responsive: true,
        maintainAspectRatio: false,
        legend: { position: 'top' },
        scales: {
            yAxes: [{ gridLines: { color: gridColor }, ticks: { beginAtZero: true } }],
            xAxes: [{ gridLines: { display: false } }]
        },
        elements: { line: { tension: 0.3 } }
    };

    // 1. Top Species Chart
    charts.top = new Chart(document.getElementById('topSpeciesChart'), {
        type: 'horizontalBar',
        data: { labels: [], datasets: [{ backgroundColor: colorPalette, data: [] }] },
        options: {
            responsive: true, maintainAspectRatio: false, legend: { display: false },
            scales: {
                xAxes: [{ gridLines: { color: gridColor }, ticks: { beginAtZero: true } }],
                yAxes: [{ gridLines: { display: false } }]
            }
        }
    });

    // 2. Day Activity Chart
    charts.activity = new Chart(document.getElementById('dayActivityChart'), {
        type: 'bar',
        data: { labels: [], datasets: [{ label: 'Detections', backgroundColor: colorPalette[0], data: [] }] },
        options: {
            responsive: true, maintainAspectRatio: false, legend: { display: false },
            scales: {
                yAxes: [{ gridLines: { color: gridColor }, ticks: { beginAtZero: true } }],
                xAxes: [{ gridLines: { display: false } }]
            }
        }
    });

    // 3. Main Trends Chart
    charts.trends = new Chart(document.getElementById('mainTrendsChart'), {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Daily Detections', borderColor: colorPalette[0], backgroundColor: colorPalette[0] + '22', fill: true, data: [] }] },
        options: commonLineOptions
    });

    // 4. Species Patterns Chart (Multi-line)
    charts.patterns = new Chart(document.getElementById('speciesPatternsChart'), {
        type: 'line',
        data: { labels: Array.from({length: 24}, (_, i) => str_pad(i, 2, '0') + ':00'), datasets: [] },
        options: {
            ...commonLineOptions,
            elements: { line: { tension: 0.4 }, point: { radius: 3 } }
        }
    });

    // 5. Species Trends Chart (Stacked/Area)
    charts.speciesTrends = new Chart(document.getElementById('speciesTrendsChart'), {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: {
            ...commonLineOptions,
            scales: {
                yAxes: [{ stacked: false, gridLines: { color: gridColor }, ticks: { beginAtZero: true } }],
                xAxes: [{ gridLines: { display: false } }]
            }
        }
    });

    // 6. Diversity Chart (Area)
    charts.diversity = new Chart(document.getElementById('diversityChart'), {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Unique Species', borderColor: colorPalette[0], backgroundColor: colorPalette[0] + '22', fill: true, data: [] }] },
        options: {
            ...commonLineOptions,
            scales: {
                yAxes: [{ gridLines: { color: gridColor }, ticks: { beginAtZero: true, stepSize: 1 } }],
                xAxes: [{ gridLines: { display: false } }]
            }
        }
    });
}

function loadAllData() {
    const days = document.getElementById('time-period').value;
    const periodText = days == '1' ? 'Last 24 hours' : `Last ${days} days`;
    document.querySelectorAll('.kpi-period').forEach(el => el.textContent = periodText);

    // KPI Stats
    fetch(`api/v1/analytics/stats?days=${days}`)
        .then(r => r.json())
        .then(data => {
            document.getElementById('kpi-total').textContent = data.total_detections.toLocaleString();
            document.getElementById('kpi-unique').textContent = data.unique_species;
            document.getElementById('kpi-conf').textContent = data.avg_confidence;
            document.getElementById('kpi-common').textContent = data.most_common;
            document.getElementById('kpi-common-sub').textContent = `${data.most_common_count.toLocaleString()} detections`;
        });

    // Top Species
    fetch(`api/v1/analytics/top_species?days=${days}&limit=10`)
        .then(r => r.json())
        .then(data => {
            charts.top.data.labels = data.map(d => d.species);
            charts.top.data.datasets[0].data = data.map(d => d.count);
            charts.top.update();
        });

    // Hourly Activity
    fetch(`api/v1/analytics/activity?days=${days}`)
        .then(r => r.json())
        .then(data => {
            charts.activity.data.labels = data.map(d => d.hour + ':00');
            charts.activity.data.datasets[0].data = data.map(d => d.count);
            charts.activity.update();
        });

    // Detection Trends
    fetch(`api/v1/analytics/detections?days=${days}`)
        .then(r => r.json())
        .then(data => {
            charts.trends.data.labels = data.dates;
            charts.trends.data.datasets[0].data = data.counts;
            charts.trends.update();
        });

    // Diversity
    fetch(`api/v1/analytics/diversity?days=${days}`)
        .then(r => r.json())
        .then(data => {
            charts.diversity.data.labels = data.dates;
            charts.diversity.data.datasets[0].data = data.counts;
            charts.diversity.update();
        });

    // New Species
    fetch(`api/v1/analytics/new_species?days=${days}`)
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('new-species-list');
            if (data.length === 0) {
                container.innerHTML = '<div class="empty-state">No new species detected in this period.</div>';
            } else {
                container.innerHTML = data.map(d => `
                    <div class="new-species-item">
                        <div class="ns-icon">🐦</div>
                        <div class="ns-info">
                            <span class="ns-name">${d.Com_Name}</span>
                            <span class="ns-sci">${d.Sci_Name}</span>
                            <span class="ns-date">First seen ${d.first_date}</span>
                        </div>
                    </div>
                `).join('');
            }
        });

    // Species Patterns
    fetch(`api/v1/analytics/patterns?days=${days}`)
        .then(r => r.json())
        .then(data => {
            charts.patterns.data.datasets = Object.entries(data).map(([species, series], i) => ({
                label: species,
                data: series,
                borderColor: colorPalette[i % colorPalette.length],
                backgroundColor: 'transparent',
                borderWidth: 2,
                pointRadius: 0
            }));
            charts.patterns.update();
        });

    // Species Trends
    fetch(`api/v1/analytics/trends?days=${days}`)
        .then(r => r.json())
        .then(data => {
            charts.speciesTrends.data.labels = data.dates.map(date => {
                const d = new Date(date);
                return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
            });
            charts.speciesTrends.data.datasets = Object.entries(data.series).map(([species, series], i) => ({
                label: species,
                data: series,
                borderColor: colorPalette[i % colorPalette.length],
                backgroundColor: colorPalette[i % colorPalette.length] + '11',
                fill: true,
                borderWidth: 2,
                tension: 0.4
            }));
            charts.speciesTrends.update();
        });

    // Recent Detections
    fetch(`api/v1/detections/recent?limit=10&days=${days}`)
        .then(r => r.json())
        .then(data => {
            const body = document.getElementById('recent-detections-body');
            body.innerHTML = data.map(d => `
                <tr>
                    <td>${d.date}, ${d.time}</td>
                    <td>
                        <div class="td-species">
                            <div class="ns-icon" style="width: 24px; height: 24px; font-size: 0.8rem;">🐦</div>
                            <div class="species-details">
                                <span class="species-name">${d.species}</span>
                                <span class="species-sci">${d.sci_name}</span>
                            </div>
                        </div>
                    </td>
                    <td>
                        <div class="conf-bar-container">
                            <div class="conf-bar-bg">
                                <div class="conf-bar-fill" style="width: ${d.confidence * 100}%; background: ${getConfColor(d.confidence)}"></div>
                            </div>
                            <span class="conf-label">${(d.confidence * 100).toFixed(1)}%</span>
                        </div>
                    </td>
                    <td>
                        <span class="badge-time">${getTimeOfOfDay(d.time)}</span>
                    </td>
                </tr>
            `).join('');
        });
}

function getConfColor(conf) {
    if (conf >= 0.8) return '#22c55e';
    if (conf >= 0.6) return '#eab308';
    return '#ef4444';
}

function getTimeOfOfDay(time) {
    const hour = parseInt(time.split(':')[0]);
    if (hour >= 5 && hour < 9) return 'Dawn';
    if (hour >= 9 && hour < 12) return 'Morning';
    if (hour >= 12 && hour < 17) return 'Afternoon';
    if (hour >= 17 && hour < 21) return 'Evening';
    return 'Night';
}

function str_pad(n, width, z) {
    z = z || '0';
    n = n + '';
    return n.length >= width ? n : new Array(width - n.length + 1).join(z) + n;
}

// Picker State
let currentTarget = null; // 'patterns' or 'trends'
let selectedSpecies = {
    patterns: [],
    trends: []
};

function openPicker(target) {
    currentTarget = target;
    document.getElementById('picker-title').innerText = target === 'patterns' ? 'Filter Detection Patterns' : 'Filter Detection Trends';
    document.getElementById('species-picker-overlay').style.display = 'block';
    document.getElementById('species-picker').style.display = 'flex';
    document.getElementById('species-search-input').value = '';
    document.getElementById('search-results').style.display = 'none';
    renderSelectedTags();
    document.getElementById('species-search-input').focus();
}

function closePicker() {
    document.getElementById('species-picker-overlay').style.display = 'none';
    document.getElementById('species-picker').style.display = 'none';
}

function renderSelectedTags() {
    const container = document.getElementById('selected-species-container');
    container.innerHTML = '';
    selectedSpecies[currentTarget].forEach(s => {
        const tag = document.createElement('div');
        tag.className = 'selected-tag';
        tag.innerHTML = `<span>${s}</span><span class="tag-remove" onclick="removeSpecies('${s}')">✕</span>`;
        container.appendChild(tag);
    });
}

function removeSpecies(name) {
    selectedSpecies[currentTarget] = selectedSpecies[currentTarget].filter(s => s !== name);
    renderSelectedTags();
}

function addSpecies(name) {
    if (selectedSpecies[currentTarget].length >= 5) {
        alert("You can only select up to 5 species.");
        return;
    }
    if (!selectedSpecies[currentTarget].includes(name)) {
        selectedSpecies[currentTarget].push(name);
        renderSelectedTags();
    }
    document.getElementById('search-results').style.display = 'none';
    document.getElementById('species-search-input').value = '';
}

function resetSpeciesFilter(target) {
    selectedSpecies[target] = [];
    const days = document.getElementById('time-period').value;
    if (target === 'patterns') {
        loadPatternsData(days);
    } else {
        loadTrendsData(days);
    }
}

function saveSpeciesSelection() {
    closePicker();
    const days = document.getElementById('time-period').value;
    if (currentTarget === 'patterns') {
        loadPatternsData(days);
    } else {
        loadTrendsData(days);
    }
}

// Search logic
document.getElementById('species-search-input').addEventListener('input', function(e) {
    const q = e.target.value;
    if (q.length < 2) {
        document.getElementById('search-results').style.display = 'none';
        return;
    }
    fetch(`api/v1/species/search?q=${encodeURIComponent(q)}`)
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('search-results');
            if (data.length === 0) {
                container.style.display = 'none';
                return;
            }
            container.innerHTML = data.map(d => `<div class="result-item" onclick="addSpecies('${d.name}')">${d.name} <small>(${d.sciName})</small></div>`).join('');
            container.style.display = 'block';
        });
});

function loadPatternsData(days) {
    const species = selectedSpecies.patterns.join(',');
    fetch(`api/v1/analytics/patterns?days=${days}&species=${encodeURIComponent(species)}`)
        .then(r => r.json())
        .then(data => {
            charts.patterns.data.datasets = Object.entries(data).map(([species, series], i) => ({
                label: species,
                data: series,
                borderColor: colorPalette[i % colorPalette.length],
                backgroundColor: 'transparent',
                borderWidth: 2,
                pointRadius: 0
            }));
            charts.patterns.update();
            const label = species ? `Showing patterns for: ${selectedSpecies.patterns.join(', ')}` : 'Showing average detection counts throughout the day for selected species';
            document.getElementById('patterns-sub').textContent = label;
        });
}

function loadTrendsData(days) {
    const species = selectedSpecies.trends.join(',');
    fetch(`api/v1/analytics/trends?days=${days}&species=${encodeURIComponent(species)}`)
        .then(r => r.json())
        .then(data => {
            charts.speciesTrends.data.labels = data.dates.map(date => {
                const d = new Date(date);
                return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
            });
            charts.speciesTrends.data.datasets = Object.entries(data.series).map(([species, series], i) => ({
                label: species,
                data: series,
                borderColor: colorPalette[i % colorPalette.length],
                backgroundColor: colorPalette[i % colorPalette.length] + '11',
                fill: true,
                borderWidth: 2,
                tension: 0.4
            }));
            charts.speciesTrends.update();
            const label = species ? `Showing trends for: ${selectedSpecies.trends.join(', ')}` : 'Shows detection trends over time for selected species';
            document.getElementById('trends-sub').textContent = label;
        });
}

// Update existing loadAllData
const originalLoadAllData = loadAllData;
loadAllData = function() {
    originalLoadAllData();
    const days = document.getElementById('time-period').value;
    loadPatternsData(days);
    loadTrendsData(days);
};

// Force all charts to resize correctly on browser zoom
var resizeTimer;
window.addEventListener('resize', function() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() {
        Chart.helpers.each(Chart.instances, function(instance) {
            instance.resize();
        });
    }, 250);
});
</script>
