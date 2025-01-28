function initCustomAudioPlayers() {
  // =================== Config & Helpers ===================
  const CONFIG = { LEFT_MARGIN_PERCENT: 6, RIGHT_MARGIN_PERCENT: 9, PROGRESS_BAR_UPDATE_INTERVAL: 20, BUFFER_TIME: 0.1 };

  const debounce = (func, wait) => {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  };

  const icons = {
    play: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="white"><path d="M8 5v14l11-7z"/></svg>`,
    pause: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="white"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>`,
    dots: `<svg width="24" height="24" fill="white" xmlns="http://www.w3.org/2000/svg"><path d="M12 6a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM12 22a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"/></svg>`,
    spinner: `<div style="width: 40px; height: 40px; border: 4px solid rgba(255,255,255,0.3); border-top: 4px solid white; border-radius: 50%; box-sizing: border-box; animation: ring-spin 1s linear infinite;"><style>@keyframes ring-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style></div>`
  };

  const safeGet = (k, fb) => {
    try { return localStorage.getItem(k) || fb; } catch { return fb; }
  };
  const safeSet = (k, v) => {
    try { localStorage.setItem(k, v); } catch {}
  };

  const savedGain = safeGet("customAudioPlayerGain", "Off");
  const savedHighpass = safeGet("customAudioPlayerFilterHigh", "Off");
  const savedLowpass = safeGet("customAudioPlayerFilterLow", "Off");

  const applyStyles = (elem, styles) => Object.assign(elem.style, styles);

  const styleButton = (btn, styles = {}) => {
    applyStyles(btn, styles);
    btn.addEventListener("mouseover", () => (btn.style.background = "rgba(255,255,255,0.2)"));
    btn.addEventListener("mouseout", () => (btn.style.background = "none"));
  };

  const createButton = (parent, { text = "", html = "", styles = {}, data = {}, onClick = null } = {}) => {
    const btn = document.createElement("button");
    btn.type = "button";
    if (text) btn.textContent = text;
    if (html) btn.innerHTML = html;
    Object.entries(data).forEach(([k, v]) => (btn.dataset[k] = v));
    styleButton(btn, styles);
    if (onClick) btn.addEventListener("click", onClick);
    parent.appendChild(btn);
    return btn;
  };

  // Common styles
  const iconBtnStyle = {
    background: "none", border: "none", cursor: "pointer",
    width: "36px", height: "36px", display: "flex",
    alignItems: "center", justifyContent: "center",
    marginRight: "0.6rem", padding: "0"
  };
  const textBtnStyle = {
    background: "none", border: "none", cursor: "pointer",
    color: "white", fontSize: "14px", textAlign: "right",
    width: "100%", padding: "6px 12px", margin: "2px 0", borderRadius: "4px"
  };
  const optionBtnStyle = {
    background: "none", border: "none", cursor: "pointer",
    color: "white", fontSize: "14px", textAlign: "center",
    width: "auto", padding: "6px 8px", margin: "2px 4px", borderRadius: "4px"
  };

  // =================== Main Loop ===================
  document.querySelectorAll(".custom-audio-player").forEach((player) => {
    // Basic data
    const audioSrc = player.dataset.audioSrc;
    const imageSrc = player.dataset.imageSrc;

    // Audio element
    const audioEl = document.createElement("audio");
    audioEl.preload = "none";
    audioEl.setAttribute("onplay", "setLiveStreamVolume(0)");
    audioEl.setAttribute("onended", "setLiveStreamVolume(1)");
    audioEl.setAttribute("onpause", "setLiveStreamVolume(1)");
    player.appendChild(audioEl);

    // Wrapper + image
    const wrapper = player.appendChild(document.createElement("div"));
    applyStyles(wrapper, { position: "relative" });
    const img = wrapper.appendChild(document.createElement("img"));
    img.src = imageSrc;
    applyStyles(img, { width: "100%", borderRadius: "8px" });

    // Progress indicator
    const indicator = wrapper.appendChild(document.createElement("div"));
    applyStyles(indicator, {
      position: "absolute", top: "0", bottom: "5%",
      left: `${CONFIG.LEFT_MARGIN_PERCENT}%`, width: "2px",
      background: "rgba(0,0,0)", pointerEvents: "none", borderRadius: "2px",
    });

    // Overlay
    const overlay = wrapper.appendChild(document.createElement("div"));
    applyStyles(overlay, {
      position: "absolute", left: "0", bottom: "0",
      width: "100%", height: "14.6%", display: "flex",
      alignItems: "center", justifyContent: "space-between",
      padding: "0 10px", borderRadius: "0 0 8px 8px",
      background: "rgba(0,0,0,0.3)", backdropFilter: "blur(1px)",
      visibility: "visible",
    });

    // Loading spinner
    const loadingSpinner = document.createElement("div");
    loadingSpinner.innerHTML = icons.spinner;
    applyStyles(loadingSpinner, {
      position: "absolute", top: "50%", left: "50%",
      transform: "translate(-50%, -50%)", display: "none"
    });
    wrapper.appendChild(loadingSpinner);

    // =================== Overlay Buttons & Progress ===================
    let audioCtx = null, sourceNode, gainNode, filterNodeHigh, filterNodeLow;
    const gainOptions = ["Off", "x2", "x4", "x8", "x16"];
    const gainValues = { Off: 1, x2: 2, x4: 4, x8: 8, x16: 16 };
    let activeGain = gainOptions.includes(savedGain) ? savedGain : "Off";

    const highpassOptions = ["Off", "250", "500", "1000"];
    let activeHighpassOption = highpassOptions.includes(savedHighpass) ? savedHighpass : "Off";

    const lowpassOptions = ["Off", "2000", "4000", "8000"];
    let activeLowpassOption = lowpassOptions.includes(savedLowpass) ? savedLowpass : "Off";

    const initAudioContext = async () => {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        sourceNode = audioCtx.createMediaElementSource(audioEl);
        gainNode = audioCtx.createGain();
        gainNode.gain.value = 1;
        sourceNode.connect(gainNode).connect(audioCtx.destination);
      }
      if (audioCtx.state === "suspended") await audioCtx.resume();
    };

    const rebuildAudioChain = () => {
      if (!audioCtx) return;
      sourceNode.disconnect();
      gainNode.disconnect();
      if (filterNodeHigh) filterNodeHigh.disconnect();
      if (filterNodeLow) filterNodeLow.disconnect();

      let currentChain = sourceNode;
      if (filterNodeHigh) { currentChain.connect(filterNodeHigh); currentChain = filterNodeHigh; }
      if (filterNodeLow) { currentChain.connect(filterNodeLow); currentChain = filterNodeLow; }
      currentChain.connect(gainNode).connect(audioCtx.destination);
    };

    const setActiveGain = async (val) => {
      activeGain = val;
      if (activeGain !== "Off") {
        await initAudioContext();
        gainNode.gain.value = gainValues[activeGain];
      } else if (gainNode) {
        gainNode.gain.value = 1;
      }
      gainButtons.forEach(b => b.style.textDecoration = b.dataset.gain === activeGain ? "underline" : "none");
      safeSet("customAudioPlayerGain", activeGain);
    };

    const setActiveHighpass = async (val) => {
      activeHighpassOption = val;
      if (activeHighpassOption !== "Off") {
        await initAudioContext();
        if (!filterNodeHigh) {
          filterNodeHigh = audioCtx.createBiquadFilter();
          filterNodeHigh.type = "highpass";
        }
        filterNodeHigh.frequency.value = parseFloat(activeHighpassOption);
      } else if (filterNodeHigh) {
        filterNodeHigh.disconnect();
        filterNodeHigh = null;
      }
      rebuildAudioChain();
      highpassButtons.forEach(b => b.style.textDecoration = b.dataset.filter === activeHighpassOption ? "underline" : "none");
      safeSet("customAudioPlayerFilterHigh", activeHighpassOption);
    };

    const setActiveLowpass = async (val) => {
      activeLowpassOption = val;
      if (activeLowpassOption !== "Off") {
        await initAudioContext();
        if (!filterNodeLow) {
          filterNodeLow = audioCtx.createBiquadFilter();
          filterNodeLow.type = "lowpass";
        }
        filterNodeLow.frequency.value = parseFloat(activeLowpassOption);
      } else if (filterNodeLow) {
        filterNodeLow.disconnect();
        filterNodeLow = null;
      }
      rebuildAudioChain();
      lowpassButtons.forEach(b => b.style.textDecoration = b.dataset.filter === activeLowpassOption ? "underline" : "none");
      safeSet("customAudioPlayerFilterLow", activeLowpassOption);
    };

    // Play/Pause with Debounce
    const debouncedPlayPause = debounce(async () => {
      await initAudioContext();
      if (audioEl.paused) {
        if (!audioEl.src) {
          audioEl.src = audioSrc;
          await audioEl.load();
        }
        audioEl.currentTime += CONFIG.BUFFER_TIME;
        audioEl.play();
      } else {
        audioEl.pause();
      }
    }, 100);

    const playBtn = createButton(overlay, {
      html: icons.play,
      styles: iconBtnStyle,
      onClick: debouncedPlayPause,
    });

    // Progress bar
    const progress = document.createElement("input");
    progress.type = "range";
    progress.value = "0";
    progress.min = "0";
    progress.max = "100";
    applyStyles(progress, { flex: "1", margin: "0 0.5rem", verticalAlign: "middle" });
    overlay.appendChild(progress);

    // Menu button (dots)
    const dotsBtn = createButton(overlay, { html: icons.dots, styles: iconBtnStyle });

    // =================== Menu ===================
    const menu = wrapper.appendChild(document.createElement("div"));
    applyStyles(menu, {
      position: "absolute", right: "10px", bottom: "15%",
      background: "rgba(0,0,0,0.3)", backdropFilter: "blur(8px)",
      color: "white", borderRadius: "6px", padding: "0.5rem",
      visibility: "hidden", display: "flex", flexDirection: "column",
      alignItems: "flex-end", minWidth: "160px",
    });

    const closeMenu = () => {
      menuOpen = false;
      menu.style.visibility = "hidden";
    };
    let menuOpen = false;
    dotsBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      menuOpen = !menuOpen;
      menu.style.visibility = menuOpen ? "visible" : "hidden";
    });
    document.addEventListener("click", (e) => {
      if (!menu.contains(e.target) && e.target !== dotsBtn) closeMenu();
    });

    // Info & Download
    createButton(menu, {
      text: "Info",
      styles: textBtnStyle,
      onClick: async () => {
        let size = "unknown", enc = "unknown", sampleRate = "unknown", channels = "unknown";
        try {
          const resp = await fetch(audioSrc, { method: "HEAD" });
          if (resp.ok) {
            const cl = resp.headers.get("content-length");
            if (cl) {
              const kb = parseInt(cl, 10) / 1024;
              size = kb >= 1024 ? `${(kb / 1024).toFixed(2)} MB` : `${kb.toFixed(2)} KB`;
            }
            const ct = resp.headers.get("content-type");
            if (ct) enc = ct.split("/")[1]?.toUpperCase() || "unknown";
          }
          const audioData = await fetch(audioSrc).then(r => r.arrayBuffer());
          const decCtx = new (window.AudioContext || window.webkitAudioContext)();
          const decoded = await decCtx.decodeAudioData(audioData);
          sampleRate = decoded.sampleRate;
          channels = decoded.numberOfChannels;
        } catch {}
        const duration = audioEl.duration ? `${audioEl.duration.toFixed(2)} s` : "unknown";
        alert(`Duration: ${duration}
Type: ${enc}
Size: ${size}
Sampling Rate: ${sampleRate} Hz
Channels: ${channels}`);
        closeMenu();
      },
    });
    createButton(menu, {
      text: "Download",
      styles: textBtnStyle,
      onClick: async () => {
        try {
          const blob = await fetch(audioSrc).then(r => r.blob());
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = audioSrc.split("/").pop() || "audio_file";
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        } catch {
          alert("Failed to download audio.");
        }
        closeMenu();
      },
    });

    // Gain & Filter Containers
    const createOptionSection = (labelText) => {
      const container = menu.appendChild(document.createElement("div"));
      applyStyles(container, {
        display: "flex", alignItems: "center", padding: "4px 0",
        borderTop: "1px solid rgba(255,255,255,0.2)", width: "100%",
        justifyContent: "flex-end", flexWrap: "wrap",
      });
      const label = container.appendChild(document.createElement("div"));
      label.textContent = labelText;
      applyStyles(label, { marginRight: "8px", fontSize: "14px", color: "#ccc", flexShrink: "0" });
      return container;
    };

    const gainContainer = createOptionSection("Gain:");
    const highpassContainer = createOptionSection("HighPass (Hz):");
    const lowpassContainer = createOptionSection("LowPass (Hz):");

    // Create gain buttons
    const gainButtons = gainOptions.map((opt) =>
      createButton(gainContainer, {
        text: opt, data: { gain: opt }, styles: optionBtnStyle,
        onClick: () => setActiveGain(opt),
      })
    );
    // Create highpass buttons
    const highpassButtons = highpassOptions.map((opt) =>
      createButton(highpassContainer, {
        text: opt, data: { filter: opt }, styles: optionBtnStyle,
        onClick: () => setActiveHighpass(opt),
      })
    );
    // Create lowpass buttons
    const lowpassButtons = lowpassOptions.map((opt) =>
      createButton(lowpassContainer, {
        text: opt, data: { filter: opt }, styles: optionBtnStyle,
        onClick: () => setActiveLowpass(opt),
      })
    );

    // Sync with saved or default
    setActiveGain(activeGain);
    setActiveHighpass(activeHighpassOption);
    setActiveLowpass(activeLowpassOption);

    // =================== Play/Pause/Progress Listeners ===================
    let intervalId;
    const updateProgress = () => {
      if (!audioEl.duration) return;
      const frac = audioEl.currentTime / audioEl.duration;
      const pc = frac * 100;
      progress.value = pc;
      indicator.style.left = CONFIG.LEFT_MARGIN_PERCENT +
        (pc * (100 - CONFIG.LEFT_MARGIN_PERCENT - CONFIG.RIGHT_MARGIN_PERCENT) / 100) + "%";
    };
    const clearProgressInterval = () => { if (intervalId) clearInterval(intervalId); };

    audioEl.addEventListener("play", () => {
      overlay.style.visibility = "hidden";
      playBtn.innerHTML = icons.pause;
      intervalId = setInterval(updateProgress, CONFIG.PROGRESS_BAR_UPDATE_INTERVAL);
    });
    audioEl.addEventListener("pause", () => {
      overlay.style.visibility = "visible";
      playBtn.innerHTML = icons.play;
      clearProgressInterval();
    });
    audioEl.addEventListener("ended", () => clearProgressInterval());
    audioEl.addEventListener("waiting", () => {
      loadingSpinner.style.display = "block";
    });
    audioEl.addEventListener("canplay", () => {
      loadingSpinner.style.display = "none";
    });

    progress.addEventListener("input", () => {
      if (!audioEl.duration) return;
      audioEl.currentTime = (progress.value / 100) * audioEl.duration;
      updateProgress();
    });

    // Click on image seeks & plays
    wrapper.addEventListener("click", async (e) => {
      if (menu.style.visibility === "visible" || overlay.contains(e.target) || !audioEl.duration) return;
      await initAudioContext();
      const { left, width } = wrapper.getBoundingClientRect();
      const x = Math.max(0, Math.min(1, (e.clientX - left) / width));
      progress.value = x * 100;
      audioEl.currentTime = x * audioEl.duration;
      updateProgress();
      audioEl.play();
    });

    // Overlay show/hide by hover/touch
    player.addEventListener("mouseenter", () => (overlay.style.visibility = "visible"));
    wrapper.addEventListener("mouseleave", () => (overlay.style.visibility = "hidden"));
    wrapper.addEventListener("mousemove", () => (overlay.style.visibility = "visible"));
    document.addEventListener("touchstart", (ev) => {
      overlay.style.visibility = wrapper.contains(ev.target) ? "visible" : "hidden";
    });
  });
}

document.addEventListener("DOMContentLoaded", initCustomAudioPlayers);
