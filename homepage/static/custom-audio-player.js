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
    play: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="white"><path d="M8 5v14l11-7z"/></svg>`,
    pause: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="white"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>`,
    dots: `<svg width="24" height="24" fill="white" xmlns="http://www.w3.org/2000/svg"><path d="M12 6a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM12 22a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"/></svg>`,
    spinner: `<div style="width: 40px; height: 40px; border: 4px solid rgba(255,255,255,0.3); border-top: 4px solid white; border-radius: 50%; box-sizing: border-box; animation: ring-spin 1s linear infinite;"><style>@keyframes ring-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style></div>`,
    error: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="white"><path d="M12 0C5.37 0 0 5.37 0 12s5.37 12 12 12 12-5.37 12-12S18.63 0 12 0zM1 12C1 6.48 6.48 1 12 1s11 5.48 11 11-5.48 11-11 11S1 17.52 1 12zm11-6c-.55 0-1 .45-1 1v5c0 .55.45 1 1 1s1-.45 1-1V7c0-.55-.45-1-1-1zm0 10c-.55 0-1 .45-1 1v1c0 .55.45 1 1 1s1-.45 1-1v-1c0-.55-.45-1-1-1z"/></svg>`,
  };

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

  const savedGain = safeGet("customAudioPlayerGain", "Off");
  const savedHighpass = safeGet("customAudioPlayerFilterHigh", "Off");
  const savedLowpass = safeGet("customAudioPlayerFilterLow", "Off");

  const applyStyles = (elem, styles) => Object.assign(elem.style, styles);

  const styleButton = (btn, styles = {}) => {
    applyStyles(btn, styles);
    btn.addEventListener("mouseover", () => (btn.style.background = "rgba(255,255,255,0.2)"));
    btn.addEventListener("mouseout", () => (btn.style.background = "none"));
  };

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

  // Common styles
  const iconBtnStyle = {
    background: "none",
    border: "none",
    cursor: "pointer",
    width: "36px",
    height: "36px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginRight: "0.6rem",
    padding: "0",
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
    // Basic data
    const audioSrc = player.dataset.audioSrc;
    const imageSrc = player.dataset.imageSrc;

    // Audio element
    const audioEl = document.createElement("audio");
    audioEl.preload = "none";
    //audioEl.setAttribute("onplay", "setLiveStreamVolume(0)");
    //audioEl.setAttribute("onended", "setLiveStreamVolume(1)");
    //audioEl.setAttribute("onpause", "setLiveStreamVolume(1)");
    player.appendChild(audioEl);

    // =================== Fetch+Decode Caching ===================
    let fetchAndDecodePromise = null;
    let decodedDataCache = null; // store the AudioBuffer info once decoded for sampleRate/channels

    // A helper to ensure the audio is loaded into <audio> so we have metadata for duration.
    const ensureAudioLoaded = async () => {
      // If we already have valid metadata, do nothing.
      if (audioEl.readyState >= HTMLMediaElement.HAVE_METADATA) {
        return;
      }

      // Show spinner
      loadingSpinner.style.display = "block";

      // Set .src if not set yet, then call .load()
      if (!audioEl.src) {
        audioEl.src = audioSrc;
      }
      audioEl.load();

      await new Promise((resolve, reject) => {
        const onLoadedMetadata = () => {
          audioEl.removeEventListener("loadedmetadata", onLoadedMetadata);
          audioEl.removeEventListener("error", onError);
          loadingSpinner.style.display = "none";
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

    // A helper to fetch+decode the full audio data for size, sampleRate, channels.
    const fetchAndDecodeAudioData = async () => {
      if (decodedDataCache) {
        // Already have decoded data
        return decodedDataCache;
      }
      if (!fetchAndDecodePromise) {
        fetchAndDecodePromise = (async () => {
          // Show spinner
          loadingSpinner.style.display = "block";

          // GET request; the browser may reuse from cache if audioEl has loaded it
          let getResp;
          try {
            getResp = await fetch(audioSrc, { method: "GET" });
            if (!getResp.ok) throw new Error("GET request not successful");
          } catch (err) {
            loadingSpinner.style.display = "none";
            throw err;
          }

          // Read into an ArrayBuffer
          const audioData = await getResp.arrayBuffer();

          // Compute size from byte length
          const sizeBytes = audioData.byteLength;
          const kb = sizeBytes / 1024;
          const sizeInfo =
            kb >= 1024 ? `${(kb / 1024).toFixed(2)} MB` : `${kb.toFixed(2)} KB`;

          // Decode the audio data for sampleRate & channels
          const decCtx = new (window.AudioContext || window.webkitAudioContext)();
          const decoded = await decCtx.decodeAudioData(audioData);

          loadingSpinner.style.display = "none";

          // Store the final info
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

    // Wrapper
    const wrapper = player.appendChild(document.createElement("div"));
    applyStyles(wrapper, { position: "relative" });

    // Handle image
    let indicator = null;
    if (imageSrc) {
      const img = wrapper.appendChild(document.createElement("img"));
      img.src = imageSrc;
      img.onerror = () => {
        wrapper.removeChild(img);
      };
      applyStyles(img, { width: "100%", borderRadius: "8px" });

      // Progress indicator
      indicator = wrapper.appendChild(document.createElement("div"));
      applyStyles(indicator, {
        position: "absolute",
        top: "0",
        bottom: "5%",
        left: `${CONFIG.LEFT_MARGIN_PERCENT}%`,
        width: "2px",
        background: "rgba(0,0,0)",
        pointerEvents: "none",
        borderRadius: "2px",
      });
    }

    // Overlay
    const overlay = wrapper.appendChild(document.createElement("div"));
    applyStyles(overlay, {
      position: "absolute",
      left: "0",
      bottom: "0",
      width: "100%",
      height: "14.6%",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 10px",
      borderRadius: "0 0 8px 8px",
      background: "rgba(0,0,0,0.3)",
      backdropFilter: "blur(1px)",
      visibility: "visible",
    });

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

    // =================== Overlay Buttons & Progress ===================
    let audioCtx = null,
      sourceNode,
      gainNode,
      filterNodeHigh,
      filterNodeLow;
    const gainOptions = ["Off", "6", "12", "18", "24"];
    const gainValues = { "Off": 1, "6": 2, "12": 4, "18": 8, "24": 16 };
    let activeGain = gainOptions.includes(savedGain) ? savedGain : "Off";

    const highpassOptions = ["Off", "250", "500", "1000"];
    let activeHighpassOption = highpassOptions.includes(savedHighpass)
      ? savedHighpass
      : "Off";

    const lowpassOptions = ["Off", "2000", "4000", "8000"];
    let activeLowpassOption = lowpassOptions.includes(savedLowpass)
      ? savedLowpass
      : "Off";

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
        b.style.textDecoration =
          b.dataset.filter === activeHighpassOption ? "underline" : "none";
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
        b.style.textDecoration =
          b.dataset.filter === activeLowpassOption ? "underline" : "none";
      });
      safeSet("customAudioPlayerFilterLow", activeLowpassOption);
    };

    // Debounced Play/Pause
    const debouncedPlayPause = debounce(async () => {
      await initAudioContext();

      // Make sure the audio is loaded
      try {
        await ensureAudioLoaded();
      } catch {
        // If ensureAudioLoaded failed, error is shown
        return;
      }

      // Actually play or pause
      if (audioEl.paused) {
        if (audioEl.currentTime >= audioEl.duration) {
          audioEl.currentTime = 0;
        }
        audioEl.currentTime += CONFIG.BUFFER_TIME;
        audioEl.play().catch(() => {
          errorMessage.style.display = "block";
        });
      } else {
        audioEl.pause();
      }
    }, 100);

    // Play Button
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
    applyStyles(progress, {
      flex: "1",
      margin: "0 0.5rem",
      verticalAlign: "middle",
    });
    overlay.appendChild(progress);

    // Menu button (dots)
    const dotsBtn = createButton(overlay, { html: icons.dots, styles: iconBtnStyle });

    // =================== Menu ===================
    const menu = wrapper.appendChild(document.createElement("div"));
    applyStyles(menu, {
      position: "absolute",
      right: "10px",
      bottom: "15%",
      background: "rgba(0,0,0,0.3)",
      backdropFilter: "blur(8px)",
      color: "white",
      borderRadius: "6px",
      padding: "0.5rem",
      visibility: "hidden",
      display: "flex",
      flexDirection: "column",
      alignItems: "flex-end",
      minWidth: "160px",
    });

    let menuOpen = false;
    const closeMenu = () => {
      menuOpen = false;
      menu.style.visibility = "hidden";
    };
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
      onClick: async (e) => {
        e.stopPropagation();
        audioEl.pause();
        closeMenu();

        // 1) Ensure we have at least the metadata (duration)
        try {
          await ensureAudioLoaded();
        } catch {
          // error shown if it fails
          return;
        }
        const duration = audioEl.duration
          ? `${audioEl.duration.toFixed(2)} s`
          : "Unknown";

        // 2) Decode audio data (for size, sampleRate, channels)
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
        } catch {
          // decoding failed => leave them as "Unknown"
        }

        // 3) Infer encoding from extension, etc.
        const guessContentType = audioSrc.split(".").pop()?.toUpperCase() || "";
        if (guessContentType) {
          enc = guessContentType;
        }

        alert(
          `Duration: ${duration}
Type: ${enc}
Size: ${size}
Sampling Rate: ${sampleRate} Hz
Channels: ${channels}`
        );
      },
    });

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

    // Gain & Filter Containers
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

    const gainContainer = createOptionSection("Gain (dB):");
    const highpassContainer = createOptionSection("HighPass (Hz):");
    const lowpassContainer = createOptionSection("LowPass (Hz):");

    // Create gain buttons
    const gainButtons = gainOptions.map((opt) =>
      createButton(gainContainer, {
        text: opt,
        data: { gain: opt },
        styles: optionBtnStyle,
        onClick: () => setActiveGain(opt),
      })
    );
    // Create highpass buttons
    const highpassButtons = highpassOptions.map((opt) =>
      createButton(highpassContainer, {
        text: opt,
        data: { filter: opt },
        styles: optionBtnStyle,
        onClick: () => setActiveHighpass(opt),
      })
    );
    // Create lowpass buttons
    const lowpassButtons = lowpassOptions.map((opt) =>
      createButton(lowpassContainer, {
        text: opt,
        data: { filter: opt },
        styles: optionBtnStyle,
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
      if (indicator) {
        indicator.style.left =
          CONFIG.LEFT_MARGIN_PERCENT +
          (pc * (100 - CONFIG.LEFT_MARGIN_PERCENT - CONFIG.RIGHT_MARGIN_PERCENT)) /
            100 +
          "%";
      }
    };

    const clearProgressInterval = () => {
      if (intervalId) clearInterval(intervalId);
    };

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

    // Clicking on the image: move the playhead & play
    wrapper.addEventListener("click", async (e) => {
      // If user clicked the menu or the overlay, ignore
      if (menu.style.visibility === "visible" || overlay.contains(e.target) || menu.contains(e.target)) return;
      // If we have no duration (not loaded yet), ignore
      if (!audioEl.duration) return;

      // Seek
      const { left, width } = wrapper.getBoundingClientRect();
      const x = Math.max(0, Math.min(1, (e.clientX - left) / width));
      progress.value = x * 100;
      audioEl.currentTime = x * audioEl.duration;
      updateProgress();

      // Then play
      audioEl.play().catch(() => {
        errorMessage.style.display = "block";
      });
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

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", initCustomAudioPlayers);
