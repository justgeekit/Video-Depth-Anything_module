(() => {
    "use strict";

    // --- State ---
    let uploadedFilename = "";
    let progressPollId = null;
    const STAGE_ORDER = [
        "extracting_audio",
        "reading_frames",
        "estimating_depth",
        "saving_source",
        "saving_depth",
        "merging_rgbd",
        "complete",
    ];

    // --- DOM refs ---
    const $ = (sel) => document.querySelector(sel);
    const sections = {
        upload: $("#sectionUpload"),
        settings: $("#sectionSettings"),
        progress: $("#sectionProgress"),
        results: $("#sectionResults"),
    };
    const dropzone = $("#dropzone");
    const fileInput = $("#fileInput");
    const errorBanner = $("#errorBanner");
    const headerStatus = $("#headerStatus");

    // --- Section management ---
    function showSection(name) {
        Object.values(sections).forEach((s) => s.classList.remove("active"));
        sections[name].classList.add("active");
    }

    function showError(msg) {
        errorBanner.textContent = msg;
        errorBanner.classList.add("visible");
        setTimeout(() => errorBanner.classList.remove("visible"), 8000);
    }

    function clearError() {
        errorBanner.classList.remove("visible");
    }

    // --- Drag & drop ---
    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("drag-over");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("drag-over");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("drag-over");
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFile(files[0]);
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
    });

    // --- Upload ---
    async function handleFile(file) {
        clearError();
        headerStatus.textContent = "Uploading...";

        const formData = new FormData();
        formData.append("file", file);

        try {
            const resp = await fetch("/upload", { method: "POST", body: formData });
            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.detail || "Upload failed");
            }
            const data = await resp.json();
            uploadedFilename = data.filename;

            // Show settings
            $("#fileName").textContent = data.filename;
            $("#fileSize").textContent = `${data.size_mb} MB`;
            headerStatus.textContent = "Ready";
            showSection("settings");
        } catch (e) {
            headerStatus.textContent = "Ready";
            showError(e.message);
        }
    }

    // --- Settings buttons ---
    $("#changeFile").addEventListener("click", () => {
        showSection("upload");
        fileInput.value = "";
    });

    $("#btnBack").addEventListener("click", () => {
        showSection("upload");
        fileInput.value = "";
    });

    $("#btnProcess").addEventListener("click", startProcessing);

    // --- Processing ---
    async function startProcessing() {
        clearError();
        showSection("progress");
        headerStatus.textContent = "Processing...";
        resetProgressUI();

        const params = new URLSearchParams({
            filename: uploadedFilename,
            encoder: $("#encoder").value,
            input_size: $("#inputSize").value,
            max_res: $("#maxRes").value,
            target_fps: $("#targetFps").value,
        });

        // Start progress polling
        startProgressPolling();

        try {
            const resp = await fetch(`/process?${params}`, { method: "POST" });
            stopProgressPolling();

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.detail || "Processing failed");
            }

            const data = await resp.json();
            showResults(data);
        } catch (e) {
            stopProgressPolling();
            headerStatus.textContent = "Error";
            showError(e.message);
            showSection("settings");
        }
    }

    // --- Progress polling ---
    function startProgressPolling() {
        progressPollId = setInterval(async () => {
            try {
                const resp = await fetch("/progress");
                if (!resp.ok) return;
                const data = await resp.json();
                updateProgressUI(data);
            } catch {
                // ignore poll errors
            }
        }, 500);
    }

    function stopProgressPolling() {
        if (progressPollId) {
            clearInterval(progressPollId);
            progressPollId = null;
        }
    }

    function resetProgressUI() {
        $("#progressBar").style.width = "0%";
        $("#progressMessage").textContent = "Initializing...";
        document.querySelectorAll(".stage").forEach((el) => {
            el.classList.remove("active", "done");
        });
    }

    function updateProgressUI(data) {
        const { stage, progress, message } = data;

        // Update message
        if (message) {
            $("#progressMessage").textContent = message;
        }

        // Compute overall progress from stage + stage progress
        const stageIdx = STAGE_ORDER.indexOf(stage);
        const stagesTotal = STAGE_ORDER.length - 1; // exclude "complete"
        let overall = 0;
        if (stageIdx >= 0 && stageIdx < stagesTotal) {
            overall = ((stageIdx + progress) / stagesTotal) * 100;
        } else if (stage === "complete") {
            overall = 100;
        }
        $("#progressBar").style.width = `${Math.min(overall, 100)}%`;

        // Update stage dots
        document.querySelectorAll(".stage").forEach((el) => {
            const elStage = el.dataset.stage;
            const elIdx = STAGE_ORDER.indexOf(elStage);
            el.classList.remove("active", "done");
            if (elIdx < stageIdx) {
                el.classList.add("done");
            } else if (elIdx === stageIdx) {
                el.classList.add("active");
            }
        });
    }

    // --- Results ---
    function showResults(data) {
        headerStatus.textContent = "Complete";
        const downloads = data.downloads;

        // Set video sources with cache-bust
        const ts = Date.now();
        $("#videoSrc").src = `${downloads.src}?t=${ts}`;
        $("#videoDepth").src = `${downloads.depth}?t=${ts}`;
        $("#videoRgbd").src = `${downloads.rgbd}?t=${ts}`;

        // Download button
        $("#downloadBtn").href = downloads.rgbd;

        showSection("results");
    }

    // --- New job ---
    $("#btnNewJob").addEventListener("click", () => {
        headerStatus.textContent = "Ready";
        fileInput.value = "";
        showSection("upload");
    });
})();
