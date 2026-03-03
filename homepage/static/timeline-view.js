/**
 * BirdNET-Pi Timeline / Journal View
 * Renders daily detections as a visual timeline with smart clustering.
 */

const TimelineView = {
  container: null,
  currentDate: null,
  lat: null,
  lon: null,
  data: null,
  searchFilter: '',
  confidenceFilter: 0,
  tzOffsetHours: -(new Date().getTimezoneOffset() / 60),

  init: function (containerId, lat, lon) {
    this.container = document.getElementById(containerId);
    this.lat = parseFloat(lat);
    this.lon = parseFloat(lon);

    // Get date from URL or use today
    const urlParams = new URLSearchParams(window.location.search);
    this.currentDate = urlParams.get('date') || this.formatDate(new Date());

    this.renderSkeleton();
    this.fetchData();
  },

  formatDate: function (dateStrOrObj) {
    const d = new Date(dateStrOrObj);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  },

  // Sunrise/Sunset Math (approximate bounds for visual markers)
  getSolarTimes: function (dateStr) {
    if (!this.lat || !this.lon) return { sunrise: null, sunset: null };

    const date = new Date(dateStr + "T12:00:00"); // Midday local
    const startOfYear = new Date(date.getFullYear(), 0, 0);
    const diff = date - startOfYear;
    const dayOfYear = Math.floor(diff / 86400000);

    // Fractional year in radians
    const gamma = (2 * Math.PI / 365) * (dayOfYear - 1 + ((12 - 12) / 24));
    // Equation of time (minutes)
    const eqTime = 229.18 * (0.000075 + 0.001868 * Math.cos(gamma) - 0.032077 * Math.sin(gamma) - 0.014615 * Math.cos(2 * gamma) - 0.040849 * Math.sin(2 * gamma));
    // Solar declination (radians)
    const decl = 0.006918 - 0.399912 * Math.cos(gamma) + 0.070257 * Math.sin(gamma) - 0.006758 * Math.cos(2 * gamma) + 0.000907 * Math.sin(2 * gamma) - 0.002697 * Math.cos(3 * gamma) + 0.00148 * Math.sin(3 * gamma);

    // Hour angle
    const latRad = this.lat * Math.PI / 180;
    const zenith = 90.833 * Math.PI / 180; // Official zenith

    const cosHa = (Math.cos(zenith) / (Math.cos(latRad) * Math.cos(decl))) - Math.tan(latRad) * Math.tan(decl);

    if (cosHa > 1) return { sunrise: null, sunset: null }; // Polar night
    if (cosHa < -1) return { sunrise: null, sunset: null }; // Midnight sun

    const ha = Math.acos(cosHa);
    const haDeg = ha * 180 / Math.PI;

    // Sunrise/sunset in UTC minutes
    const sunriseUTC = 720 - 4 * (this.lon + haDeg) - eqTime;
    const sunsetUTC = 720 - 4 * (this.lon - haDeg) - eqTime;

    // Convert to local hours
    const tzOffsetMins = this.tzOffsetHours * 60;
    const sRiseL = (sunriseUTC + tzOffsetMins) / 60;
    const sSetL = (sunsetUTC + tzOffsetMins) / 60;

    const formatHr = (decimalHr) => {
      let h = Math.floor(decimalHr);
      if (h < 0) h += 24;
      if (h > 23) h -= 24;
      let m = Math.round((decimalHr - Math.floor(decimalHr)) * 60);
      if (m === 60) { h++; m = 0; }
      return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
    };

    return {
      sunrise: formatHr(sRiseL),
      sunset: formatHr(sSetL),
      rawRiseHr: sRiseL,
      rawSetHr: sSetL
    };
  },

  renderSkeleton: function () {
    this.container.innerHTML = `
      <div class="timeline-container">
        <div class="timeline-header">
          <div class="tl-date-nav">
            <button onclick="TimelineView.changeDate(-1)">◀</button>
            <span>${this.currentDate}</span>
            <button onclick="TimelineView.changeDate(1)">▶</button>
          </div>
          <div class="tl-filters">
            <input type="text" id="tlSearch" placeholder="Filter species..." onkeyup="TimelineView.applyFilters()">
          </div>
        </div>
        <div id="tlContent" class="timeline-body">
          <div class="tl-loading">Loading timeline...</div>
        </div>
      </div>
    `;
  },

  changeDate: function (offsetDays) {
    const d = new Date(this.currentDate + "T12:00:00");
    d.setDate(d.getDate() + offsetDays);
    const newDate = this.formatDate(d);
    window.location.href = `views.php?view=Todays+Detections&date=${newDate}&timeline=1`;
  },

  applyFilters: function () {
    const searchEl = document.getElementById('tlSearch');
    if (searchEl) this.searchFilter = searchEl.value.toLowerCase();
    this.render();
  },

  fetchData: function () {
    const xhr = new XMLHttpRequest();
    xhr.onload = () => {
      if (xhr.status === 200) {
        try {
          this.data = JSON.parse(xhr.responseText);
          this.render();
        } catch (e) {
          document.getElementById('tlContent').innerHTML = `<div class="tl-error">Error parsing timeline data.</div>`;
        }
      } else {
        document.getElementById('tlContent').innerHTML = `<div class="tl-error">Failed to load timeline.</div>`;
      }
    };
    xhr.open('GET', `/api/v1/detections/timeline?date=${this.currentDate}`, true);
    xhr.send();
  },

  formatTimeAmPm: function (timeStr) {
    const [h, m] = timeStr.split(':');
    let hour = parseInt(h);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    hour = hour % 12;
    if (hour === 0) hour = 12;
    return `${hour}:${m} ${ampm}`;
  },

  render: function () {
    if (!this.data) return;
    const c = document.getElementById('tlContent');
    let html = '';

    const solar = this.getSolarTimes(this.currentDate);

    // Apply filters
    const filteredHours = this.data.hours.map(hBlock => {
      const filteredClusters = hBlock.clusters.filter(c => {
        const nameMatch = this.searchFilter === '' || c.species.toLowerCase().includes(this.searchFilter) || c.sci_name.toLowerCase().includes(this.searchFilter);
        return nameMatch && (c.best_confidence * 100 >= this.confidenceFilter);
      });
      return { ...hBlock, clusters: filteredClusters, detection_count: filteredClusters.reduce((sum, cl) => sum + cl.count, 0) };
    }).filter(hBlock => hBlock.detection_count > 0);

    if (filteredHours.length === 0) {
      if (this.searchFilter) {
        html += `<div class="tl-empty">No detections matched your filters.</div>`;
      } else {
        html += `
          <div class="tl-empty">
            <div style="font-size:3em;margin-bottom:10px;">🐧</div>
            <h3>No detections yet.</h3>
            <p>Your station is listening. Detections will appear here as birds are identified.</p>
          </div>
        `;
      }
      c.innerHTML = html;
      return;
    }

    let sunRiseRendered = false;
    let sunSetRendered = false;

    // Helper to render sun marker if needed
    const checkSunMarker = (currentHour) => {
      let mHtml = '';
      if (solar.sunrise && !sunRiseRendered && (currentHour >= Math.floor(solar.rawRiseHr))) {
        mHtml += `<div class="tl-sun-marker"><span class="tl-sun-icon">🌅</span> Sunrise ${this.formatTimeAmPm(solar.sunrise)}</div>`;
        sunRiseRendered = true;
      }
      if (solar.sunset && !sunSetRendered && (currentHour >= Math.floor(solar.rawSetHr))) {
        mHtml += `<div class="tl-sun-marker tl-moon-marker"><span class="tl-sun-icon">🌙</span> Sunset ${this.formatTimeAmPm(solar.sunset)}</div>`;
        sunSetRendered = true;
      }
      return mHtml;
    };

    let prevHour = -1;
    const latestHour = Math.max(...filteredHours.map(h => h.hour));

    filteredHours.forEach(hBlock => {
      // Quiet periods
      if (prevHour !== -1 && hBlock.hour > prevHour + 1) {
        html += checkSunMarker(prevHour + 1);
        const gap = hBlock.hour - prevHour - 1;
        const startAmPm = this.formatTimeAmPm(`${prevHour + 1}:00:00`).split(':')[0] + ' ' + (prevHour + 1 >= 12 ? 'PM' : 'AM');
        const endAmPm = this.formatTimeAmPm(`${hBlock.hour}:00:00`).split(':')[0] + ' ' + (hBlock.hour >= 12 ? 'PM' : 'AM');
        html += `<div class="tl-quiet-block">${gap} ${gap === 1 ? 'hour' : 'hours'} quiet (${startAmPm} - ${endAmPm})</div>`;
      }

      html += checkSunMarker(hBlock.hour);

      const isExpanded = (hBlock.hour === latestHour) ? 'expanded' : '';
      const hourAmPm = this.formatTimeAmPm(`${hBlock.hour}:00:00`).split(':')[0] + ' ' + (hBlock.hour >= 12 ? 'PM' : 'AM');

      html += `
        <div class="tl-hour-block ${isExpanded}" id="tl-hr-${hBlock.hour}">
          <div class="tl-hour-header" onclick="TimelineView.toggleBlock(${hBlock.hour})">
            <div class="tl-hour-title">
              <span class="tl-chevron">▶</span>
              <strong>${hourAmPm}</strong>
            </div>
            <div class="tl-hour-stats">${hBlock.detection_count} detections</div>
          </div>
          <div class="tl-hour-content">
      `;

      hBlock.clusters.forEach((cl, idx) => {
        let confClass = 'low';
        const bestPct = Math.round(cl.best_confidence * 100);
        if (bestPct >= 90) confClass = 'high';
        else if (bestPct >= 50) confClass = 'med';

        let countBadge = cl.count > 1 ? `<span class="tl-badge-count">×${cl.count}</span>` : '';
        const clId = `cl-${hBlock.hour}-${idx}`;

        const shortComName = cl.species.replace("'", "\\'");
        const uriComName = encodeURIComponent(cl.species);

        html += `
          <div class="tl-cluster">
            <div class="tl-cluster-summary" onclick="TimelineView.toggleCluster('${clId}')">
              <div class="tl-cluster-bird">
                <span class="tl-bird-name">
                  <a href="#" onclick="event.stopPropagation(); window.location='?view=Species+Stats&species=${uriComName}';">${cl.species}</a>
                  <img src="images/chart.svg" class="tl-inline-icon" title="Stats" onclick="event.stopPropagation(); generateMiniGraph(this, '${shortComName}')">
                </span>
                <span class="tl-bird-sci">${cl.sci_name}</span>
              </div>
              <div class="tl-cluster-meta">
                <span class="tl-badge-conf ${confClass}">${bestPct}%</span>
                ${countBadge}
                <span class="tl-cluster-time">${this.formatTimeAmPm(cl.first_time)}</span>
              </div>
            </div>
            <div class="tl-cluster-details" id="${clId}">
              <table>
        `;

        cl.detections.forEach(d => {
          const dConf = Math.round(d.confidence * 100);
          const safeComName = cl.species.replace(/ /g, '_').replace(/'/g, '');
          const audioSrc = `By_Date/${this.currentDate}/${safeComName}/${d.file}`;
          const safeAudioSrc = audioSrc.replace(/'/g, "\\'");
          html += `
                <tr>
                  <td width="70">${this.formatTimeAmPm(d.time)}</td>
                  <td width="50">${dConf}%</td>
                  <td class="tl-actions">
                    <img src="images/play.svg" class="tl-icon-btn" title="Play/Spectrogram" onclick="TimelineView.mountPlayer(this, '${safeAudioSrc}')">
                    <img src="images/copy.png" class="tl-icon-btn" title="Open in new tab" onclick="window.open('?filename=${d.file}', '_blank')">
                  </td>
                </tr>
          `;
        });

        html += `
              </table>
              <div class="tl-player-mount"></div>
            </div>
          </div>
        `;
      });

      html += `
          </div>
        </div>
      `;
      prevHour = hBlock.hour;
    });

    html += checkSunMarker(24);

    html += `
      <div class="tl-summary-footer">
        ${this.data.total_detections} detections · ${this.data.total_species} species
      </div>
    `;

    c.innerHTML = html;

    // Auto-expand clusters if it's the latest hour and there are few 
    const latestBlock = document.getElementById(`tl-hr-${latestHour}`);
    if (latestBlock) {
      const details = latestBlock.querySelectorAll('.tl-cluster-details');
      if (details.length <= 3) {
        details.forEach(d => d.style.display = 'block');
      }
    }
  },

  toggleBlock: function (hourObjId) {
    const el = document.getElementById(`tl-hr-${hourObjId}`);
    if (el) el.classList.toggle('expanded');
  },

  toggleCluster: function (clId) {
    const el = document.getElementById(clId);
    if (!el) return;
    if (el.style.display === 'block') {
      el.style.display = 'none';
      el.querySelector('.tl-player-mount').innerHTML = ''; // Unmount player
    } else {
      el.style.display = 'block';
    }
  },

  mountPlayer: function (btnEl, audioSrc) {
    const mount = btnEl.closest('.tl-cluster-details').querySelector('.tl-player-mount');
    const imgSrc = audioSrc + ".png";
    mount.innerHTML = `<div class='custom-audio-player' data-audio-src="${audioSrc}" data-image-src="${imgSrc}"></div>`;
    // Re-init the external custom audio player script on this element
    if (typeof initCustomAudioPlayers === 'function') {
      initCustomAudioPlayers();
    }
  }

};
