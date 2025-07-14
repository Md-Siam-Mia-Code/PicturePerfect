document.addEventListener("DOMContentLoaded", () => {
  // --- DOM ELEMENT SELECTORS ---
  const DOMElements = {
    gpuName: document.getElementById("gpu-name"),
    halfPrecision: document.getElementById("half-precision"),
    modal: {
      overlay: document.getElementById("modal-overlay"),
      title: document.getElementById("modal-title"),
      text: document.getElementById("modal-text"),
      list: document.getElementById("model-download-list"),
    },
    dropZone: document.getElementById("drop-zone"),
    fileInput: document.getElementById("file-input"),
    enhanceBtn: document.getElementById("enhance-btn"),
    clearBtn: document.getElementById("clear-btn"),
    downloadAllBtn: document.getElementById("download-all-btn"),
    tabs: document.querySelectorAll(".tab"),
    originalGrid: document.getElementById("original-grid"),
    enhancedGrid: document.getElementById("enhanced-grid"),
    noOriginals: document.getElementById("no-originals"),
    noEnhanced: document.getElementById("no-enhanced"),
    notificationContainer: document.getElementById("notification-container"),
  };

  // --- STATE ---
  let filesToUpload = [];
  let isAppReady = false;

  // --- INITIALIZATION ---
  const init = async () => {
    setupEventListeners();
    updateButtonStates();
    try {
      const response = await fetch("/api/status");
      const data = await response.json();
      updateSystemInfo(data.system_info);

      if (data.missing_models && data.missing_models.length > 0) {
        showDownloadModal(data.missing_models);
      } else if (!data.system_info.models_loaded) {
        await loadModelsIntoGPU();
      } else {
        isAppReady = true;
        updateButtonStates();
      }
    } catch (error) {
      createNotification(
        "error",
        "Cannot connect to the server. Please refresh.",
        -1
      );
    }
  };

  // --- MODEL MANAGEMENT ---
  const showDownloadModal = (missingModels) => {
    DOMElements.modal.list.innerHTML = "";
    missingModels.forEach((model) => {
      const li = document.createElement("li");
      li.className = "model-item";
      li.id = `model-${model.name.replace(/\s+/g, "-")}`;
      li.innerHTML = `<span class="model-name">${model.name}</span><div class="model-status">Queued</div>`;
      DOMElements.modal.list.appendChild(li);
    });
    DOMElements.modal.overlay.classList.remove("modal-hidden");
    processDownloadQueue(missingModels);
  };

  const processDownloadQueue = async (queue) => {
    for (const model of queue) {
      await startDownload(model);
    }
    // After all downloads are attempted, check if any failed
    const failedItems = DOMElements.modal.list.querySelectorAll(".retry-btn");
    if (failedItems.length === 0) {
      await loadModelsIntoGPU();
    }
  };

  const startDownload = (modelInfo) => {
    return new Promise((resolve) => {
      const modelId = `model-${modelInfo.name.replace(/\s+/g, "-")}`;
      const item = document.getElementById(modelId);
      const statusDiv = item.querySelector(".model-status");
      statusDiv.innerHTML = `<div class="progress-bar"><div class="progress-fill"></div></div>`;

      const eventSource = new EventSource(
        `/api/download_model?model_info=${encodeURIComponent(
          JSON.stringify(modelInfo)
        )}`
      );

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.status === "downloading") {
          item.querySelector(
            ".progress-fill"
          ).style.width = `${data.progress}%`;
        } else if (data.status === "completed") {
          statusDiv.innerHTML = '<i class="fa-solid fa-check-circle"></i>';
          eventSource.close();
          resolve();
        } else if (data.status === "error") {
          statusDiv.innerHTML = `<button class="retry-btn" data-model='${JSON.stringify(
            modelInfo
          )}'>Retry</button>`;
          createNotification("error", `Failed to download ${modelInfo.name}`);
          eventSource.close();
          resolve();
        }
      };
      eventSource.onerror = () => {
        statusDiv.innerHTML = `<button class="retry-btn" data-model='${JSON.stringify(
          modelInfo
        )}'>Retry</button>`;
        createNotification(
          "error",
          `Connection error during download of ${modelInfo.name}`
        );
        eventSource.close();
        resolve();
      };
    });
  };

  const loadModelsIntoGPU = async () => {
    DOMElements.modal.title.textContent = "Finalizing Setup";
    DOMElements.modal.text.textContent =
      "Loading models into memory. This may take a moment...";
    DOMElements.modal.list.innerHTML = "";
    DOMElements.modal.overlay.classList.remove("modal-hidden");
    try {
      await fetch("/api/load_models", { method: "POST" });
      DOMElements.modal.overlay.classList.add("modal-hidden");
      isAppReady = true;
      updateButtonStates();
      createNotification("info", "Application is ready!", 5000);
    } catch (error) {
      DOMElements.modal.text.textContent =
        "A critical error occurred while loading models. Please restart the application.";
      createNotification("error", "Failed to load models into memory.", -1);
    }
  };

  // --- EVENT LISTENERS & UI ---
  const setupEventListeners = () => {
    DOMElements.dropZone.addEventListener("click", () =>
      DOMElements.fileInput.click()
    );
    DOMElements.dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      DOMElements.dropZone.classList.add("drag-over");
    });
    DOMElements.dropZone.addEventListener("dragleave", () =>
      DOMElements.dropZone.classList.remove("drag-over")
    );
    DOMElements.dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      DOMElements.dropZone.classList.remove("drag-over");
      handleFileSelection(e.dataTransfer.files);
    });
    DOMElements.fileInput.addEventListener("change", () =>
      handleFileSelection(DOMElements.fileInput.files)
    );
    DOMElements.enhanceBtn.addEventListener("click", handleEnhance);
    DOMElements.clearBtn.addEventListener("click", handleClearAll);
    DOMElements.downloadAllBtn.addEventListener("click", handleDownloadAll);
    DOMElements.tabs.forEach((tab) =>
      tab.addEventListener("click", () => switchTab(tab.dataset.tab))
    );
    DOMElements.modal.list.addEventListener("click", (e) => {
      if (e.target.classList.contains("retry-btn")) {
        const modelInfo = JSON.parse(e.target.dataset.model);
        startDownload(modelInfo);
      }
    });
  };

  const handleEnhance = async () => {
    if (!isAppReady || filesToUpload.length === 0) return;
    const notifId = createNotification(
      "info",
      "Enhancement in progress...",
      -1
    );
    DOMElements.enhanceBtn.disabled = true;

    const formData = new FormData();
    filesToUpload.forEach((file) => formData.append("files", file));

    try {
      const response = await fetch("/enhance", {
        method: "POST",
        body: formData,
      });
      if (!response.ok)
        throw new Error((await response.json()).detail || "Enhancement failed");

      const result = await response.json();
      displayEnhancedImages(result.images);
      updateNotification(
        notifId,
        "info",
        `Successfully enhanced ${result.images.length} image(s).`,
        5000
      );
    } catch (error) {
      updateNotification(notifId, "error", error.message, 5000);
    } finally {
      updateButtonStates();
    }
  };

  const handleFileSelection = (selectedFiles) => {
    filesToUpload = Array.from(selectedFiles);
    DOMElements.originalGrid.innerHTML = "";
    DOMElements.noOriginals.style.display =
      filesToUpload.length > 0 ? "none" : "flex";
    filesToUpload.forEach((file) => {
      DOMElements.originalGrid.appendChild(
        createImageCard(file.name, URL.createObjectURL(file), "original")
      );
    });
    updateButtonStates();
    if (filesToUpload.length > 0) switchTab("original");
  };

  // Other UI handlers (createImageCard, removeFile, switchTab, etc.) remain largely the same.
  const updateButtonStates = () => {
    const hasOriginals = filesToUpload.length > 0;
    const hasEnhanced =
      DOMElements.enhancedGrid.querySelector(".image-card") !== null;
    DOMElements.enhanceBtn.disabled = !isAppReady || !hasOriginals;
    DOMElements.clearBtn.disabled = !hasOriginals && !hasEnhanced;
    DOMElements.downloadAllBtn.disabled = !hasEnhanced;
  };

  const updateSystemInfo = (info) => {
    DOMElements.gpuName.textContent = info.gpu_detected;
    DOMElements.halfPrecision.textContent = info.half_precision
      ? "Enabled"
      : "Disabled";
  };

  const createNotification = (type, message, duration = 4000) => {
    const id = `notif_${Date.now()}`;
    const icon = type === "error" ? "fa-circle-xmark" : "fa-circle-info";
    const notif = document.createElement("div");
    notif.className = `notification ${type}`;
    notif.id = id;
    notif.innerHTML = `<i class="fa-solid ${icon}"></i> <p>${message}</p>`;
    DOMElements.notificationContainer.appendChild(notif);
    if (duration > 0) setTimeout(() => notif.remove(), duration);
    return id;
  };

  const updateNotification = (id, type, message, duration = 4000) => {
    const notif = document.getElementById(id);
    if (!notif) return createNotification(type, message, duration);
    const icon = type === "error" ? "fa-circle-xmark" : "fa-circle-info";
    notif.className = `notification ${type}`;
    notif.querySelector("p").textContent = message;
    notif.querySelector("i").className = `fa-solid ${icon}`;
    if (duration > 0) setTimeout(() => notif.remove(), duration);
  };

  // --- (Paste other UI helper functions here like createImageCard, etc.)
  const createImageCard = (filename, src, type) => {
    const card = document.createElement("div");
    card.className = "image-card";
    card.innerHTML = `
            <img src="${src}" alt="${filename}" class="image-preview">
            <div class="image-actions">
                ${
                  type === "original"
                    ? `<button class="action-btn-icon" data-remove="${filename}" title="Remove"><i class="fa-solid fa-xmark"></i></button>`
                    : `<a href="${src}" download="${filename}" class="action-btn-icon" title="Download"><i class="fa-solid fa-download"></i></a>`
                }
            </div>`;
    if (type === "original") {
      card.querySelector("[data-remove]").addEventListener("click", (e) => {
        e.stopPropagation();
        removeFile(filename);
      });
    }
    return card;
  };

  const removeFile = (filename) => {
    filesToUpload = filesToUpload.filter((f) => f.name !== filename);
    document
      .querySelector(`.image-card [data-remove="${filename}"]`)
      .closest(".image-card")
      .remove();
    if (filesToUpload.length === 0)
      DOMElements.noOriginals.style.display = "flex";
    updateButtonStates();
  };

  const displayEnhancedImages = (enhancedFiles) => {
    DOMElements.enhancedGrid.innerHTML = "";
    DOMElements.noEnhanced.style.display =
      enhancedFiles.length > 0 ? "none" : "flex";
    enhancedFiles.forEach((filename) => {
      const src = `/output/${filename}?t=${Date.now()}`;
      DOMElements.enhancedGrid.appendChild(
        createImageCard(filename, src, "enhanced")
      );
    });
    updateButtonStates();
    if (enhancedFiles.length > 0) switchTab("enhanced");
  };

  const switchTab = (tabName) => {
    DOMElements.tabs.forEach((t) =>
      t.classList.toggle("active", t.dataset.tab === tabName)
    );
    document.querySelectorAll(".image-grid").forEach((grid) => {
      grid.classList.toggle("active", grid.id.includes(tabName));
    });
  };

  const handleClearAll = async () => {
    try {
      await fetch("/clear_history", { method: "POST" });
      filesToUpload = [];
      DOMElements.originalGrid.innerHTML = "";
      DOMElements.enhancedGrid.innerHTML = "";
      DOMElements.noOriginals.style.display = "flex";
      DOMElements.noEnhanced.style.display = "flex";
      updateButtonStates();
    } catch (error) {
      createNotification("error", "Failed to clear server history.");
    }
  };

  const handleDownloadAll = () => {
    fetch("/download_all", { method: "POST" })
      .then((res) =>
        res.ok ? res.blob() : Promise.reject("Failed to create ZIP.")
      )
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "PicturePerfect_Enhanced.zip";
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch((err) => createNotification("error", err));
  };

  // --- START THE APP ---
  init();
});
