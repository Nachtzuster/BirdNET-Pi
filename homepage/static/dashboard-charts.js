/**
 * BirdNET-Pi Dashboard Charts
 * Renders interactive Chart.js charts for the Overview page,
 * replacing static PNG images from daily_plot.py.
 */

(function () {
    'use strict';

    var barChart = null;
    var heatmapChart = null;

    // Premium color palette for species bars (indigo/teal gradient by confidence)
    function getBarColor(confidence, alpha) {
        // Map confidence 0..1 to a premium indigo to teal shift
        var r = Math.round(14 + (1 - confidence) * 60);
        var g = Math.round(165 - (1 - confidence) * 120);
        var b = Math.round(233 + (1 - confidence) * 20);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + (alpha || 0.9) + ')';
    }

    function fetchChartData(callback) {
        var xhr = new XMLHttpRequest();
        xhr.onload = function () {
            if (xhr.status === 200 && xhr.responseText.length > 0) {
                try {
                    var data = JSON.parse(xhr.responseText);
                    callback(data);
                } catch (e) {
                    console.warn('Dashboard charts: could not parse JSON', e);
                }
            }
        };
        xhr.onerror = function () {
            console.warn('Dashboard charts: request failed');
        };
        xhr.open('GET', 'overview.php?ajax_chart_data=true', true);
        xhr.send();
    }

    function renderBarChart(canvas, species) {
        if (!species || species.length === 0) {
            canvas.parentElement.innerHTML = '<p style="text-align:center;padding:20px;color:#888;">No detections yet today.</p>';
            return;
        }

        // Show all species, sorted by count descending (already sorted from PHP)
        var displayed = species;

        var labels = displayed.map(function (s) { return s.name; });
        var counts = displayed.map(function (s) { return s.count; });
        var bgColors = displayed.map(function (s) { return getBarColor(s.maxConf); });
        var borderColors = displayed.map(function (s) { return getBarColor(s.maxConf, 1); });

        // Dynamically size the chart container based on species count
        var dynamicHeight = Math.max(200, displayed.length * 30 + 60);
        canvas.parentElement.style.height = dynamicHeight + 'px';

        var ctx = canvas.getContext('2d');

        if (barChart) {
            barChart.destroy();
        }

        barChart = new Chart(ctx, {
            type: 'horizontalBar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Detections',
                    data: counts,
                    backgroundColor: bgColors,
                    borderColor: borderColors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                legend: { display: false },
                title: {
                    display: true,
                    text: 'Species Detections Today',
                    fontSize: 14,
                    fontColor: getComputedStyle(document.body).color || '#333'
                },
                scales: {
                    xAxes: [{
                        ticks: {
                            beginAtZero: true,
                            precision: 0,
                            fontColor: getComputedStyle(document.body).color || '#333'
                        },
                        scaleLabel: {
                            display: true,
                            labelString: 'Detections',
                            fontColor: getComputedStyle(document.body).color || '#333'
                        },
                        gridLines: {
                            color: 'rgba(128,128,128,0.15)'
                        }
                    }],
                    yAxes: [{
                        ticks: {
                            fontColor: getComputedStyle(document.body).color || '#333',
                            fontSize: 11
                        },
                        gridLines: {
                            display: false
                        }
                    }]
                },
                tooltips: {
                    callbacks: {
                        afterLabel: function (tooltipItem) {
                            var s = displayed[tooltipItem.index];
                            return 'Max confidence: ' + Math.round(s.maxConf * 100) + '%\n' + s.sciName;
                        }
                    }
                }
            }
        });
    }

    function renderHeatmap(canvas, species, hourly, currentHour) {
        if (!species || species.length === 0) {
            canvas.parentElement.innerHTML = '<p style="text-align:center;padding:20px;color:#888;">No data available.</p>';
            return;
        }

        var displayed = species;
        var speciesNames = displayed.map(function (s) { return s.name; });
        var hours = [];
        for (var h = 0; h < 24; h++) hours.push(h);

        // Build datasets: one dataset per species (row), each containing 24 values
        // We'll use a simple grid rendered on canvas since Chart.js 2.x doesn't have a built-in heatmap
        var ctx = canvas.getContext('2d');
        var width = canvas.parentElement.clientWidth || canvas.width;
        var cellHeight = 22;
        var labelWidth = Math.min(160, width * 0.25);
        var chartWidth = width - labelWidth - 10;
        var cellWidth = chartWidth / 24;
        var headerHeight = 24;
        var totalHeight = headerHeight + (speciesNames.length * cellHeight) + 4;

        canvas.width = width;
        canvas.height = totalHeight;
        canvas.style.width = width + 'px';
        canvas.style.height = totalHeight + 'px';

        // Detect dark mode
        var bodyBg = getComputedStyle(document.body).backgroundColor;
        var isDark = false;
        if (bodyBg) {
            var match = bodyBg.match(/\d+/g);
            if (match && match.length >= 3) {
                isDark = (parseInt(match[0]) + parseInt(match[1]) + parseInt(match[2])) < 380;
            }
        }

        var textColor = isDark ? '#e0e0e0' : '#333';
        var emptyColor = isDark ? '#1e2433' : '#f8f9fa';
        var borderColor = isDark ? '#2d3748' : '#e2e8f0';

        // Find max value for color scaling
        var maxVal = 1;
        speciesNames.forEach(function (name) {
            if (hourly[name]) {
                hours.forEach(function (h) {
                    if (hourly[name][h] && hourly[name][h] > maxVal) {
                        maxVal = hourly[name][h];
                    }
                });
            }
        });

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw hour headers
        ctx.font = '10px Roboto Flex, sans-serif';
        ctx.fillStyle = textColor;
        ctx.textAlign = 'center';
        hours.forEach(function (h) {
            var x = labelWidth + (h * cellWidth) + (cellWidth / 2);
            var label = h.toString();
            if (h === currentHour) {
                ctx.fillStyle = isDark ? '#ffd54f' : '#e65100';
                ctx.font = 'bold 10px Roboto Flex, sans-serif';
            }
            ctx.fillText(label, x, headerHeight - 6);
            ctx.fillStyle = textColor;
            ctx.font = '10px Roboto Flex, sans-serif';
        });

        // Draw grid
        speciesNames.forEach(function (name, rowIdx) {
            var y = headerHeight + (rowIdx * cellHeight);

            // Species label
            ctx.fillStyle = textColor;
            ctx.textAlign = 'right';
            ctx.font = '10px Roboto Flex, sans-serif';
            var displayName = name.length > 20 ? name.substring(0, 18) + '…' : name;
            ctx.fillText(displayName, labelWidth - 6, y + cellHeight / 2 + 3);

            // Hour cells
            hours.forEach(function (h) {
                var x = labelWidth + (h * cellWidth);
                var val = (hourly[name] && hourly[name][h]) ? hourly[name][h] : 0;

                if (val > 0) {
                    var intensity = Math.min(val / maxVal, 1);
                    // Sleek GitHub-like indigo/blue contribution scale
                    var r = Math.round(224 - intensity * 145);
                    var g = Math.round(231 - intensity * 160);
                    var b = Math.round(255 - intensity * 26);
                    if (isDark) {
                        r = Math.round(30 + intensity * 49);
                        g = Math.round(41 + intensity * 29);
                        b = Math.round(59 + intensity * 166);
                    }
                    ctx.fillStyle = 'rgb(' + r + ',' + g + ',' + b + ')';
                } else {
                    ctx.fillStyle = emptyColor;
                }

                // Rounded inner cells look much more premium
                var radius = 3;
                var rectX = x + 1.5;
                var rectY = y + 1.5;
                var rectW = cellWidth - 3;
                var rectH = cellHeight - 3;

                ctx.beginPath();
                ctx.moveTo(rectX + radius, rectY);
                ctx.arcTo(rectX + rectW, rectY, rectX + rectW, rectY + rectH, radius);
                ctx.arcTo(rectX + rectW, rectY + rectH, rectX, rectY + rectH, radius);
                ctx.arcTo(rectX, rectY + rectH, rectX, rectY, radius);
                ctx.arcTo(rectX, rectY, rectX + rectW, rectY, radius);
                ctx.fill();

                // Draw border on the cell outside to give grid feel
                ctx.strokeStyle = borderColor;
                ctx.lineWidth = 0.5;
                ctx.strokeRect(x + 0.5, y + 0.5, cellWidth - 1, cellHeight - 1);

                // Show count in cells
                if (val > 0) {
                    ctx.fillStyle = intensity > 0.4 ? '#fff' : textColor;
                    if (isDark) ctx.fillStyle = intensity > 0.4 ? '#fff' : '#94a3b8';
                    ctx.textAlign = 'center';
                    ctx.font = '600 10px Roboto Flex, sans-serif'; // Bolder font
                    ctx.fillText(val.toString(), x + cellWidth / 2, y + cellHeight / 2 + 3.5);
                }
            });
        });
    }

    // Tooltip for heatmap canvas
    function addHeatmapTooltip(canvas, species, hourly) {
        var tooltip = document.createElement('div');
        tooltip.className = 'chart-tooltip';
        tooltip.style.cssText = 'display:none;position:absolute;background:rgba(0,0,0,0.8);color:#fff;padding:6px 10px;border-radius:4px;font-size:12px;pointer-events:none;z-index:100;white-space:nowrap;';
        canvas.parentElement.style.position = 'relative';
        canvas.parentElement.appendChild(tooltip);

        var displayed = species;
        var speciesNames = displayed.map(function (s) { return s.name; });

        canvas.addEventListener('mousemove', function (e) {
            var rect = canvas.getBoundingClientRect();
            var x = e.clientX - rect.left;
            var y = e.clientY - rect.top;
            var width = canvas.width;
            var labelWidth = Math.min(160, width * 0.25);
            var cellWidth = (width - labelWidth - 10) / 24;
            var headerHeight = 24;
            var cellHeight = 22;

            var hour = Math.floor((x - labelWidth) / cellWidth);
            var row = Math.floor((y - headerHeight) / cellHeight);

            if (hour >= 0 && hour < 24 && row >= 0 && row < speciesNames.length) {
                var name = speciesNames[row];
                var val = (hourly[name] && hourly[name][hour]) ? hourly[name][hour] : 0;
                tooltip.innerHTML = '<strong>' + name + '</strong><br>' + hour + ':00 — ' + val + ' detection' + (val !== 1 ? 's' : '');
                tooltip.style.display = 'block';
                var tipX = e.clientX - rect.left + 12;
                // Flip to left side if near right edge
                if (tipX + 180 > canvas.parentElement.clientWidth) {
                    tipX = e.clientX - rect.left - 12;
                    // Measure actual tooltip width and shift left
                    tooltip.style.left = 'auto';
                    tooltip.style.right = (rect.right - e.clientX + 12) + 'px';
                    tooltip.style.top = (e.clientY - rect.top - 30) + 'px';
                } else {
                    tooltip.style.right = 'auto';
                    tooltip.style.left = tipX + 'px';
                    tooltip.style.top = (e.clientY - rect.top - 30) + 'px';
                }
            } else {
                tooltip.style.display = 'none';
            }
        });

        canvas.addEventListener('mouseleave', function () {
            tooltip.style.display = 'none';
        });
    }

    // Cache last data for resize re-render
    var lastData = null;

    // Public API
    window.DashboardCharts = {
        refresh: function () {
            var barCanvas = document.getElementById('speciesBarChart');
            var heatCanvas = document.getElementById('hourlyHeatmap');

            if (!barCanvas && !heatCanvas) return;

            fetchChartData(function (data) {
                lastData = data;
                if (barCanvas) {
                    renderBarChart(barCanvas, data.species);
                }
                if (heatCanvas) {
                    renderHeatmap(heatCanvas, data.species, data.hourly, data.currentHour);
                    // Only add tooltip once
                    if (!heatCanvas.dataset.tooltipInit) {
                        addHeatmapTooltip(heatCanvas, data.species, data.hourly);
                        heatCanvas.dataset.tooltipInit = 'true';
                    }
                }
            });
        }
    };

    // Re-render heatmap on resize/zoom so it fits the new container width
    var heatResizeTimer;
    window.addEventListener('resize', function () {
        clearTimeout(heatResizeTimer);
        heatResizeTimer = setTimeout(function () {
            if (lastData) {
                var heatCanvas = document.getElementById('hourlyHeatmap');
                if (heatCanvas) {
                    renderHeatmap(heatCanvas, lastData.species, lastData.hourly, lastData.currentHour);
                }
            }
        }, 300);
    });

})();
