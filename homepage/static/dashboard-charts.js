/**
 * BirdNET-Pi Dashboard Charts
 * Renders interactive Chart.js charts for the Overview page,
 * replacing static PNG images from daily_plot.py.
 */

(function () {
    'use strict';

    var heatmapChart = null;

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

    function renderHeatmap(canvas, species, hourly, currentHour, weather) {
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
        var cellHeight = 32;
        var labelWidth = Math.min(180, width * 0.25);
        var chartWidth = width - labelWidth - 10;
        var cellWidth = chartWidth / 24;

        // Make space for the weather row and the hour header
        var headerHeight = weather ? 48 : 30;
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

        var textColor = isDark ? '#f1f5f9' : '#1e293b';
        var emptyColor = isDark ? '#1e293b' : '#e2e8f0';
        var borderColor = isDark ? '#334155' : '#cbd5e1';

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

        function getWeatherEmoji(code) {
            if (code === undefined || code === null) return '';
            if (code === 0) return '☀️';
            if (code >= 1 && code <= 3) return '⛅';
            if (code === 45 || code === 48) return '🌫️';
            if (code >= 51 && code <= 55) return '🌦️';
            if (code >= 61 && code <= 65) return '🌧️';
            if (code >= 71 && code <= 75) return '❄️';
            if (code >= 80 && code <= 82) return '🌦️';
            if (code >= 95) return '⛈️';
            return '☁️';
        }

        // Draw hour headers and weather if available
        ctx.fillStyle = textColor;
        ctx.textAlign = 'center';
        hours.forEach(function (h) {
            var x = labelWidth + (h * cellWidth) + (cellWidth / 2);
            var label = h < 10 ? '0' + h : h.toString();
            var yHour = headerHeight - 8;

            if (h === currentHour) {
                ctx.fillStyle = isDark ? '#ffd54f' : '#e65100';
                ctx.font = 'bold 12px Roboto Flex, sans-serif';
            } else {
                ctx.fillStyle = textColor;
                ctx.font = '12px Roboto Flex, sans-serif';
            }
            ctx.fillText(label, x, yHour);

            // Draw Weather
            if (weather && weather[h]) {
                var w = weather[h];
                var emoji = getWeatherEmoji(w.code);
                ctx.font = '13px sans-serif'; // Emoji font
                ctx.fillText(emoji, x, yHour - 16);
                ctx.font = '10px Roboto Flex, sans-serif';
                ctx.fillStyle = isDark ? '#aaaaaa' : '#666666';
                ctx.fillText(w.temp + '°', x, yHour - 28);
            }
        });

        // Draw grid
        speciesNames.forEach(function (name, rowIdx) {
            var y = headerHeight + (rowIdx * cellHeight);

            // Species label
            ctx.fillStyle = textColor;
            ctx.textAlign = 'right';
            ctx.font = '13px Roboto Flex, sans-serif';
            var displayName = name.length > 25 ? name.substring(0, 23) + '…' : name;
            ctx.fillText(displayName, labelWidth - 8, y + cellHeight / 2 + 4);

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
                var radius = 4;
                var rectX = x + 2.5;
                var rectY = y + 2.5;
                var rectW = cellWidth - 5;
                var rectH = cellHeight - 5;

                ctx.beginPath();
                ctx.moveTo(rectX + radius, rectY);
                ctx.arcTo(rectX + rectW, rectY, rectX + rectW, rectY + rectH, radius);
                ctx.arcTo(rectX + rectW, rectY + rectH, rectX, rectY + rectH, radius);
                ctx.arcTo(rectX, rectY + rectH, rectX, rectY, radius);
                ctx.arcTo(rectX, rectY, rectX + rectW, rectY, radius);
                ctx.fill();

                // Show count in cells
                if (val > 0) {
                    ctx.fillStyle = intensity > 0.4 ? '#fff' : textColor;
                    if (isDark) ctx.fillStyle = intensity > 0.4 ? '#fff' : '#94a3b8';
                    ctx.textAlign = 'center';
                    ctx.font = '600 12px Roboto Flex, sans-serif'; // Bolder font
                    ctx.fillText(val.toString(), x + cellWidth / 2, y + cellHeight / 2 + 4.5);
                }
            });
        });
    }

    // Tooltip for heatmap canvas
    function addHeatmapTooltip(canvas, species, hourly, weather) {
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
            var labelWidth = Math.min(180, width * 0.25);
            var cellWidth = (width - labelWidth - 10) / 24;
            var headerHeight = weather ? 48 : 30;
            var cellHeight = 32;

            var hour = Math.floor((x - labelWidth) / cellWidth);
            var row = Math.floor((y - headerHeight) / cellHeight);

            if (hour >= 0 && hour < 24 && row >= 0 && row < speciesNames.length) {
                var name = speciesNames[row];
                var val = (hourly[name] && hourly[name][hour]) ? hourly[name][hour] : 0;
                var weatherStr = "";
                if (weather && weather[hour]) {
                    var w = weather[hour];
                    var codes = { 0: 'Clear', 1: 'Mainly Clear', 2: 'Partly Cloudy', 3: 'Overcast', 45: 'Fog', 51: 'Drizzle', 61: 'Rain', 71: 'Snow', 95: 'Thunderstorm' };
                    var cond = codes[w.code] || 'Cloudy';
                    weatherStr = '<br><span style="color:#aaa;font-size:10px;">' + w.temp + '°F • ' + cond + '</span>';
                }
                tooltip.innerHTML = '<strong>' + name + '</strong><br>' + hour + ':00 — ' + val + ' detection' + (val !== 1 ? 's' : '') + weatherStr;
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
            var heatCanvas = document.getElementById('hourlyHeatmap');

            if (!heatCanvas) return;

            fetchChartData(function (data) {
                lastData = data;
                if (heatCanvas) {
                    renderHeatmap(heatCanvas, data.species, data.hourly, data.currentHour, data.weather);
                    // Only add tooltip once
                    if (!heatCanvas.dataset.tooltipInit) {
                        addHeatmapTooltip(heatCanvas, data.species, data.hourly, data.weather);
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
                    renderHeatmap(heatCanvas, lastData.species, lastData.hourly, lastData.currentHour, lastData.weather);
                }
            }
        }, 300);
    });

})();
