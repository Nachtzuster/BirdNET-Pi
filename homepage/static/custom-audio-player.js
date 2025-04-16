function initCustomAudioPlayers() {
  // =================== Config & Helpers ===================
  const CONFIG = {
    LEFT_MARGIN_PERCENT: 6,
    RIGHT_MARGIN_PERCENT: 9,
    PROGRESS_BAR_UPDATE_INTERVAL: 20,
    BUFFER_TIME: 0.1,
  };

  const debounce = (func, wait) => {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  };

  const icons = {
    play: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="white">
             <path d="M8 5v14l11-7z"/>
           </svg>`,
    pause: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="white">
              <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
            </svg>`,
    dots: `<svg width="24" height="24" fill="white" xmlns="http://www.w3.org/2000/svg">
             <path d="M12 6a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM12 22a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"/>
           </svg>`,
    spinner: `<div style="width: 40px; height: 40px; border: 4px solid rgba(255,255,255,0.3); border-top: 4px solid white; border-radius: 50%; box-sizing: border-box; animation: ring-spin 1s linear infinite;">
                <style>@keyframes ring-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
              </div>`,
    error: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="white">
              <path d="M12 0C5.37 0 0 5.37 0 12s5.37 12 12 12 12-5.37 12-12S18.63 0 12 0zM1 12C1 6.48 6.48 1 12 1s11 5.48 11 11-5.48 11-11 11S1 17.52 1 12zm11-6c-.55 0-1 .45-1 1v5c0 .55.45 1 1 1s1-.45 1-1V7c0-.55-.45-1-1-1zm0 10c-.55 0-1 .45-1 1v1c0 .55.45 1 1 1s1-.45 1-1v-1c0-.55-.45-1-1-1z"/>
            </svg>`,
  };

  // For user preferences (gain, filters, etc.)
  const safeGet = (k, fb) => {
    try {
      return localStorage.getItem(k) || fb;
    } catch {
      return fb;
    }
  };
  const safeSet = (k, v) => {
    try {
      localStorage.setItem(k, v);
    } catch {}
  };

  // Retrieve saved user preferences
  const savedGain = safeGet("customAudioPlayerGain", "Off");
  const savedHighpass = safeGet("customAudioPlayerFilterHigh", "Off");
  const savedLowpass = safeGet("customAudioPlayerFilterLow", "Off");

  // Helper to apply multiple style properties
  const applyStyles = (elem, styles) => Object.assign(elem.style, styles);

  // Basic styling for small control buttons
  const styleButton = (btn, styles = {}) => {
    applyStyles(btn, styles);
    // Subtle hover highlight
    btn.addEventListener("mouseover", () => (btn.style.background = "rgba(255,255,255,0.1)"));
    btn.addEventListener("mouseout", () => (btn.style.background = "transparent"));
  };

  // Helper to create a button
  const createButton = (
    parent,
    { text = "", html = "", styles = {}, data = {}, onClick = null } = {}
  ) => {
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

  // Common small‐button styling
  const iconBtnStyle = {
    background: "transparent",
    border: "none",
    cursor: "pointer",
    width: "36px",
    height: "36px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginRight: "0.6rem",
    padding: "0",
    borderRadius: "50%",
  };
  const textBtnStyle = {
    background: "none",
    border: "none",
    cursor: "pointer",
    color: "white",
    fontSize: "14px",
    textAlign: "right",
    width: "100%",
    padding: "6px 12px",
    margin: "2px 0",
    borderRadius: "4px",
  };
  const optionBtnStyle = {
    background: "none",
    border: "none",
    cursor: "pointer",
    color: "white",
    fontSize: "14px",
    textAlign: "center",
    width: "auto",
    padding: "6px 8px",
    margin: "2px 4px",
    borderRadius: "4px",
  };

  // =================== Main Loop over all .custom-audio-player ===================
  document.querySelectorAll(".custom-audio-player").forEach((player) => {
    let hasLoaded = false; // set to true once metadata is available

    // Audio/player data
    const audioSrc = player.dataset.audioSrc;
    const imageSrc = player.dataset.imageSrc;

    // <audio> element
    const audioEl = document.createElement("audio");
    audioEl.preload = "none";
    player.appendChild(audioEl);

    // =================== Fetch+Decode Caching (for “Info”) ===================
    let fetchAndDecodePromise = null;
    let decodedDataCache = null;

    const ensureAudioLoaded = async () => {
      if (audioEl.readyState >= HTMLMediaElement.HAVE_METADATA) return;
      loadingSpinner.style.display = "block";
      if (!audioEl.src) {
        audioEl.src = audioSrc;
      }
      audioEl.load();
      await new Promise((resolve, reject) => {
        const onLoadedMetadata = () => {
          audioEl.removeEventListener("loadedmetadata", onLoadedMetadata);
          audioEl.removeEventListener("error", onError);
          loadingSpinner.style.display = "none";
          hasLoaded = true;
          resolve();
        };
        const onError = (e) => {
          audioEl.removeEventListener("loadedmetadata", onLoadedMetadata);
          audioEl.removeEventListener("error", onError);
          loadingSpinner.style.display = "none";
          errorMessage.style.display = "block";
          reject(e);
        };
        audioEl.addEventListener("loadedmetadata", onLoadedMetadata);
        audioEl.addEventListener("error", onError);
      });
    };

    const fetchAndDecodeAudioData = async () => {
      if (decodedDataCache) return decodedDataCache;
      if (!fetchAndDecodePromise) {
        fetchAndDecodePromise = (async () => {
          loadingSpinner.style.display = "block";
          let getResp;
          try {
            getResp = await fetch(audioSrc, { method: "GET" });
            if (!getResp.ok) throw new Error("GET request not successful");
          } catch (err) {
            loadingSpinner.style.display = "none";
            throw err;
          }
          const audioData = await getResp.arrayBuffer();
          const sizeBytes = audioData.byteLength;
          const kb = sizeBytes / 1024;
          const sizeInfo = kb >= 1024 ? `${(kb / 1024).toFixed(2)} MB` : `${kb.toFixed(2)} KB`;
          const decCtx = new (window.AudioContext || window.webkitAudioContext)();
          const decoded = await decCtx.decodeAudioData(audioData);
          loadingSpinner.style.display = "none";
          decodedDataCache = {
            size: sizeInfo,
            sampleRate: decoded.sampleRate,
            channels: decoded.numberOfChannels,
          };
          return decodedDataCache;
        })();
      }
      return fetchAndDecodePromise;
    };

    // Wrapper for spectrogram & overlays
    const wrapper = player.appendChild(document.createElement("div"));
    applyStyles(wrapper, {
      position: "relative",
      overflow: "hidden",
      borderRadius: "12px",
    });

    // Spectrogram image
    let indicator = null;
    if (imageSrc) {
      const img = wrapper.appendChild(document.createElement("img"));
      img.src = imageSrc;
      img.onerror = () => wrapper.removeChild(img);
      applyStyles(img, {
        width: "100%",
        display: "block",
        borderRadius: "12px",
      });

      // Dark vertical progression bar
      img.addEventListener("load", () => {
        indicator = document.createElement("div");
        applyStyles(indicator, {
          position: "absolute",
          top: "0",
          bottom: "0",
          // Start at left margin
          left: CONFIG.LEFT_MARGIN_PERCENT + "%",
          width: "2px",
          background: "rgba(0,0,0,0.8)",
          pointerEvents: "none",
          borderRadius: "2px",
        });
        wrapper.appendChild(indicator);
      });
    }

    // Loading spinner
    const loadingSpinner = document.createElement("div");
    loadingSpinner.innerHTML = icons.spinner;
    applyStyles(loadingSpinner, {
      position: "absolute",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      display: "none",
    });
    wrapper.appendChild(loadingSpinner);

    // Error message
    const errorMessage = document.createElement("div");
    errorMessage.innerHTML = icons.error + " Audio not available";
    applyStyles(errorMessage, {
      position: "absolute",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      display: "none",
      color: "white",
      background: "rgba(255,0,0,0.8)",
      padding: "10px",
      borderRadius: "8px",
    });
    wrapper.appendChild(errorMessage);

    // =================== Audio Context & Processing ===================
    let audioCtx = null, sourceNode, gainNode, filterNodeHigh, filterNodeLow;

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
      if (filterNodeHigh) {
        currentChain.connect(filterNodeHigh);
        currentChain = filterNodeHigh;
      }
      if (filterNodeLow) {
        currentChain.connect(filterNodeLow);
        currentChain = filterNodeLow;
      }
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
      gainButtons.forEach((b) => {
        b.style.textDecoration = b.dataset.gain === activeGain ? "underline" : "none";
      });
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
      highpassButtons.forEach((b) => {
        b.style.textDecoration = b.dataset.filter === activeHighpassOption ? "underline" : "none";
      });
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
      lowpassButtons.forEach((b) => {
        b.style.textDecoration = b.dataset.filter === activeLowpassOption ? "underline" : "none";
      });
      safeSet("customAudioPlayerFilterLow", activeLowpassOption);
    };

    // =================== Debounced Play/Pause ===================
    const debouncedPlayPause = debounce(async () => {
      await initAudioContext();
      try {
        await ensureAudioLoaded();
      } catch {
        return;
      }
      if (audioEl.paused) {
        if (audioEl.currentTime >= audioEl.duration) audioEl.currentTime = 0;
        audioEl.currentTime += CONFIG.BUFFER_TIME;
        audioEl.play().catch(() => {
          errorMessage.style.display = "block";
        });
      } else {
        audioEl.pause();
      }
    }, 100);

    // =================== Overlays & Controls ===================
    // Big Play Overlay (centered)
    const bigPlayOverlay = document.createElement("div");
    applyStyles(bigPlayOverlay, {
      position: "absolute",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      display: "none",
    });
    // Big center play button
    const bigPlayBtn = document.createElement("button");
    bigPlayBtn.type = "button";
    bigPlayBtn.innerHTML = icons.play;
    applyStyles(bigPlayBtn, {
      background: "rgba(0, 0, 0, 0.5)",
      border: "none",
      cursor: "pointer",
      width: "64px",
      height: "64px",
      borderRadius: "50%",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      transition: "background 0.2s ease",
    });
    // On hover, darken it slightly
    bigPlayBtn.addEventListener("mouseover", () => {
      bigPlayBtn.style.background = "rgba(0, 0, 0, 0.7)";
    });
    bigPlayBtn.addEventListener("mouseout", () => {
      bigPlayBtn.style.background = "rgba(0, 0, 0, 0.5)";
    });
    bigPlayBtn.addEventListener("click", debouncedPlayPause);
    bigPlayOverlay.appendChild(bigPlayBtn);
    wrapper.appendChild(bigPlayOverlay);

    // Bottom control overlay
    const controlOverlay = document.createElement("div");
    applyStyles(controlOverlay, {
      position: "absolute",
      left: "0",
      bottom: "0",
      zIndex: 1,
      width: "100%",
      height: "15%",
      display: "none",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 10px",
      borderRadius: "0 0 10px 10px",
      background: "rgba(0,0,0,0.2)",
      backdropFilter: "blur(8px)",
      WebkitBackdropFilter: "blur(8px)",
    });

    // Hidden small play/pause button
    const controlPlayBtn = createButton(controlOverlay, {
      html: icons.play,
      styles: {
        ...iconBtnStyle,
        display: "none", // hide it
      },
      onClick: debouncedPlayPause,
    });

    // Progress bar
    const progress = document.createElement("input");
    progress.type = "range";
    progress.value = "0";
    progress.min = "0";
    progress.max = "100";
    applyStyles(progress, {
      flex: "1",
      margin: "0 1rem", // bigger margin
      verticalAlign: "middle",
    });
    controlOverlay.appendChild(progress);

    // Dots (menu) button
    const dotsBtn = createButton(controlOverlay, {
      html: icons.dots,
      styles: iconBtnStyle,
    });

    // Menu container
    const menu = document.createElement("div");
    applyStyles(menu, {
      position: "absolute",
      right: "10px",
      bottom: "calc(20% + 30px)", // place above the 20% overlay
      background: "rgba(0,0,0,0.7)", // 0.7 transparency
      backdropFilter: "blur(8px)",
      WebkitBackdropFilter: "blur(8px)",
      boxShadow: "0 2px 8px rgba(0,0,0,0.5)", // 0.5 shadow
      color: "white",
      borderRadius: "8px",
      padding: "0.75rem",
      display: "none",
      flexDirection: "column",
      alignItems: "flex-end",
      minWidth: "160px",
    });
    controlOverlay.appendChild(menu);
    wrapper.appendChild(controlOverlay);

    // =================== Menu & Options ===================
    let menuOpen = false;
    const closeMenu = () => {
      menuOpen = false;
      menu.style.display = "none";
    };
    dotsBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      menuOpen = !menuOpen;
      menu.style.display = menuOpen ? "flex" : "none";
    });
    document.addEventListener("click", (e) => {
      if (!menu.contains(e.target) && e.target !== dotsBtn) closeMenu();
    });

    // Info button
    createButton(menu, {
      text: "Info",
      styles: textBtnStyle,
      onClick: async (e) => {
        e.stopPropagation();
        audioEl.pause();
        closeMenu();
        try {
          await ensureAudioLoaded();
        } catch {
          return;
        }
        const duration = audioEl.duration ? `${audioEl.duration.toFixed(2)} s` : "Unknown";
        let size = "Unknown",
          enc = "Unknown",
          sampleRate = "Unknown",
          channels = "Unknown";
        try {
          const data = await fetchAndDecodeAudioData();
          if (data) {
            size = data.size;
            sampleRate = data.sampleRate;
            channels = data.channels;
          }
        } catch {}
        const guessContentType = audioSrc.split(".").pop()?.toUpperCase() || "";
        if (guessContentType) enc = guessContentType;
        alert(
          `Duration: ${duration}
Type: ${enc}
Size: ${size}
Sampling Rate: ${sampleRate} Hz
Channels: ${channels}`
        );
      },
    });

    // Download button
    createButton(menu, {
      text: "Download",
      styles: textBtnStyle,
      onClick: async (e) => {
        e.stopPropagation();
        audioEl.pause();
        closeMenu();
        try {
          loadingSpinner.style.display = "block";
          const blob = await fetch(audioSrc).then((r) => r.blob());
          loadingSpinner.style.display = "none";
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = audioSrc.split("/").pop() || "audio_file";
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        } catch {
          loadingSpinner.style.display = "none";
          alert("Failed to download audio.");
        }
      },
    });

    // Gain & Filter sections
    const createOptionSection = (labelText) => {
      const container = menu.appendChild(document.createElement("div"));
      applyStyles(container, {
        display: "flex",
        alignItems: "center",
        padding: "4px 0",
        borderTop: "1px solid rgba(255,255,255,0.2)",
        width: "100%",
        justifyContent: "flex-end",
        flexWrap: "wrap",
      });
      const label = container.appendChild(document.createElement("div"));
      label.textContent = labelText;
      applyStyles(label, {
        marginRight: "8px",
        fontSize: "14px",
        color: "#ccc",
        flexShrink: "0",
      });
      return container;
    };

    const gainOptions = ["Off", "6", "12", "18", "24"];
    const gainValues = { Off: 1, "6": 2, "12": 4, "18": 8, "24": 16 };
    let activeGain = gainOptions.includes(savedGain) ? savedGain : "Off";
    const gainContainer = createOptionSection("Gain (dB):");
    const gainButtons = gainOptions.map((opt) =>
      createButton(gainContainer, {
        text: opt,
        data: { gain: opt },
        styles: optionBtnStyle,
        onClick: () => setActiveGain(opt),
      })
    );

    const highpassOptions = ["Off", "250", "500", "1000"];
    let activeHighpassOption = highpassOptions.includes(savedHighpass) ? savedHighpass : "Off";
    const highpassContainer = createOptionSection("HighPass (Hz):");
    const highpassButtons = highpassOptions.map((opt) =>
      createButton(highpassContainer, {
        text: opt,
        data: { filter: opt },
        styles: optionBtnStyle,
        onClick: () => setActiveHighpass(opt),
      })
    );

    const lowpassOptions = ["Off", "2000", "4000", "8000"];
    let activeLowpassOption = lowpassOptions.includes(savedLowpass) ? savedLowpass : "Off";
    const lowpassContainer = createOptionSection("LowPass (Hz):");
    const lowpassButtons = lowpassOptions.map((opt) =>
      createButton(lowpassContainer, {
        text: opt,
        data: { filter: opt },
        styles: optionBtnStyle,
        onClick: () => setActiveLowpass(opt),
      })
    );

    // Set initial user preference states
    setActiveGain(activeGain);
    setActiveHighpass(activeHighpassOption);
    setActiveLowpass(activeLowpassOption);

    // =================== Play/Pause/Progress Events ===================
    let intervalId;
    const updateProgress = () => {
      if (!audioEl.duration) return;
      const frac = audioEl.currentTime / audioEl.duration;
      // Update horizontal progress bar
      progress.value = frac * 100;

      // Update vertical bar if we have an indicator
      if (indicator) {
        const leftPosition =
          CONFIG.LEFT_MARGIN_PERCENT +
          frac * (100 - CONFIG.LEFT_MARGIN_PERCENT - CONFIG.RIGHT_MARGIN_PERCENT);
        indicator.style.left = leftPosition + "%";
      }
    };

    const clearProgressInterval = () => {
      if (intervalId) clearInterval(intervalId);
    };

    audioEl.addEventListener("play", () => {
      bigPlayOverlay.style.display = "none";
      controlOverlay.style.display = "flex";
      controlPlayBtn.innerHTML = icons.pause;
      intervalId = setInterval(updateProgress, CONFIG.PROGRESS_BAR_UPDATE_INTERVAL);
    });

    audioEl.addEventListener("pause", () => {
      clearProgressInterval();
      // If paused, show both overlays
      bigPlayOverlay.style.display = "flex";
      controlOverlay.style.display = "flex";
      controlPlayBtn.innerHTML = icons.play;
    });

    audioEl.addEventListener("ended", () => {
      clearProgressInterval();
      // On end, show both so user can replay
      bigPlayOverlay.style.display = "flex";
      controlOverlay.style.display = "flex";
      controlPlayBtn.innerHTML = icons.play;
    });

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

    // Clicking on the spectrogram toggles play/pause (no seeking)
    wrapper.addEventListener("click", (e) => {
      if (
        bigPlayOverlay.contains(e.target) ||
        controlOverlay.contains(e.target) ||
        menu.contains(e.target)
      ) {
        return;
      }
      debouncedPlayPause();
    });

    // ========== Overlay Show/Hide (Hover/Touch) ==========
    const showOverlays = () => {
      if (audioEl.paused) {
        bigPlayOverlay.style.display = "flex";
      }
      controlOverlay.style.display = "flex";
    };
    const hideOverlays = () => {
      if (!menuOpen) {
        bigPlayOverlay.style.display = "none";
        controlOverlay.style.display = "none";
      }
    };

    // Desktop hover
    wrapper.addEventListener("mouseenter", showOverlays);
    wrapper.addEventListener("mouseleave", hideOverlays);

    // Re‐show if user moves mouse inside while paused
    wrapper.addEventListener("mousemove", () => {
      if (audioEl.paused) showOverlays();
    });

    // Touch
    document.addEventListener("touchstart", (ev) => {
      if (wrapper.contains(ev.target)) {
        showOverlays();
      } else {
        hideOverlays();
      }
    });

    // Clicking outside the player hides overlays
    document.addEventListener("click", (e) => {
      if (!wrapper.contains(e.target) && !menu.contains(e.target)) {
        hideOverlays();
      }
    });
  });
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", initCustomAudioPlayers);
