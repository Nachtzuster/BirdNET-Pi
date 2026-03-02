<?php
// scripts/analytics.php
?>
<div class="row">
    <div class="col-12 col-md-12">
        <h2 style="text-align: center; margin-top: 20px;">Trends & Analytics</h2>
        <p style="text-align: center;">Long-term detection trends spanning the last 30 days.</p>
    </div>
</div>

<style>
/* Chart Container Styles */
.chart-container-card {
    flex: 1 1 400px; 
    background: var(--bg-card, #fff); 
    padding: 20px; 
    border-radius: 8px; 
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    display: flex;
    flex-direction: column;
}
.chart-container-card h3 {
    text-align: center;
    margin-top: 0;
    margin-bottom: 15px;
}
.chart-wrapper {
    position: relative;
    width: 100%;
    margin: 0 auto;
}
/* Force constrained heights */
.chart-wrapper.donut {
    height: 350px;
}
.chart-wrapper.bar {
    height: 350px;
}
.chart-wrapper.line {
    height: 400px;
}
.full-width-card {
    flex: 1 1 100%;
}
</style>

<div style="display: flex; flex-wrap: wrap; justify-content: space-around; gap: 20px; padding: 20px;">
    
    <!-- Top Species Chart -->
    <div class="chart-container-card">
        <h3>Top 10 Species</h3>
        <div class="chart-wrapper donut">
            <canvas id="topSpeciesChart"></canvas>
        </div>
    </div>

    <!-- Activity by Hour Chart -->
    <div class="chart-container-card">
        <h3>Activity by Hour</h3>
        <div class="chart-wrapper bar">
            <canvas id="hourlyActivityChart"></canvas>
        </div>
    </div>

    <!-- 30-Day Trends Chart -->
    <div class="chart-container-card full-width-card">
        <h3>30-Day Detections (Top 5 Species)</h3>
        <div class="chart-wrapper line">
            <canvas id="trendsChart"></canvas>
        </div>
    </div>
    
</div>

<script src="static/Chart.bundle.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function() {
    // Colors for charts
    const colors = [
        'rgba(54, 162, 235, 0.7)',
        'rgba(255, 99, 132, 0.7)',
        'rgba(75, 192, 192, 0.7)',
        'rgba(255, 206, 86, 0.7)',
        'rgba(153, 102, 255, 0.7)',
        'rgba(255, 159, 64, 0.7)',
        'rgba(199, 199, 199, 0.7)',
        'rgba(83, 102, 255, 0.7)',
        'rgba(40, 159, 64, 0.7)',
        'rgba(210, 199, 199, 0.7)'
    ];
    
    const isDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const fontColor = getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim() || (isDarkMode ? '#e0e0e0' : '#444');
    
    Chart.defaults.global.defaultFontColor = fontColor;

    // Fetch and render Top Species
    fetch('api/v1/analytics/top_species?days=30&limit=10')
        .then(response => response.json())
        .then(data => {
            const labels = data.map(d => d.species);
            const counts = data.map(d => d.count);
            
            new Chart(document.getElementById('topSpeciesChart'), {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: counts,
                        backgroundColor: colors
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    legend: { position: 'right', labels: { fontColor: fontColor } }
                }
            });
        });

    // Fetch and render Hourly Activity
    fetch('api/v1/analytics/activity')
        .then(response => response.json())
        .then(data => {
            const labels = data.map(d => d.hour + ':00');
            const counts = data.map(d => d.count);
            
            new Chart(document.getElementById('hourlyActivityChart'), {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Total Detections',
                        data: counts,
                        backgroundColor: 'rgba(54, 162, 235, 0.7)'
                    }]
                },
                options: {
                    responsive: true,
                    legend: { display: false },
                    scales: {
                        yAxes: [{ ticks: { beginAtZero: true, fontColor: fontColor } }],
                        xAxes: [{ ticks: { fontColor: fontColor } }]
                    }
                }
            });
        });

    // Fetch and render 30-Day Trends
    fetch('api/v1/analytics/trends?days=30')
        .then(response => response.json())
        .then(data => {
            const datasets = [];
            let colorIndex = 0;
            
            for (const [species, seriesData] of Object.entries(data.series)) {
                datasets.push({
                    label: species,
                    data: seriesData,
                    borderColor: colors[colorIndex % colors.length].replace('0.7', '1'),
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    tension: 0.3
                });
                colorIndex++;
            }
            
            new Chart(document.getElementById('trendsChart'), {
                type: 'line',
                data: {
                    labels: data.dates,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    legend: { position: 'top', labels: { fontColor: fontColor } },
                    scales: {
                        yAxes: [{ ticks: { beginAtZero: true, fontColor: fontColor } }],
                        xAxes: [{ ticks: { fontColor: fontColor, maxRotation: 45, minRotation: 45 } }]
                    }
                }
            });
        });
});
</script>
