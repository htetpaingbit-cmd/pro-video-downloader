document.addEventListener("DOMContentLoaded", () => {
    const urlInput = document.getElementById("urlInput");
    const clearBtn = document.getElementById("clearBtn");
    const pasteBtn = document.getElementById("pasteBtn");
    const fetchBtn = document.getElementById("fetchBtn");
    const btnText = document.getElementById("btnText");
    const alertBox = document.getElementById("alertBox");
    const loadingBox = document.getElementById("loadingBox");
    const resultCard = document.getElementById("resultCard");
    const downloadProgressBar = document.getElementById("downloadProgressBar");

    let currentVideoData = null;

    // စာသား ရှိ/မရှိ ပေါ်မူတည်၍ Clear (X) ခလုတ် ပြ/ဖျောက်ခြင်း
    urlInput.addEventListener("input", () => {
        if (urlInput.value.trim().length > 0) {
            clearBtn.classList.remove("hidden");
        } else {
            clearBtn.classList.add("hidden");
        }
    });

    // Clear (X) နှိပ်သည့်အခါ စာဖျက်ခြင်း
    clearBtn.addEventListener("click", () => {
        urlInput.value = "";
        clearBtn.classList.add("hidden");
        hideAlert();
        resultCard.classList.add("hidden");
        urlInput.focus();
    });

    // Paste ခလုတ် နှိပ်သည့်အခါ
    pasteBtn.addEventListener("click", async () => {
        try {
            if (navigator.clipboard && navigator.clipboard.readText) {
                const text = await navigator.clipboard.readText();
                if (text) {
                    urlInput.value = text.trim();
                    clearBtn.classList.remove("hidden");
                    showAlert("Link ထည့်သွင်းပြီးပါပြီ!", "success");
                    return;
                }
            }
            throw new Error();
        } catch (err) {
            urlInput.focus();
            urlInput.select();
            showAlert("Input Box ထဲတွင် ဖိနှိပ်၍ 'Paste' လုပ်ပေးပါ", "info");
        }
    });

    // ⭐️ စစ်ဆေးမည် ခလုတ် နှိပ်သည့်အခါ အလုပ်လုပ်မည့် Function ⭐️
    fetchBtn.addEventListener("click", handleInspect);
    urlInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") handleInspect();
    });

    async function handleInspect() {
        const url = urlInput.value.trim();
        if (!url) {
            showAlert("ကျေးဇူးပြု၍ Video Link တစ်ခု ထည့်သွင်းပေးပါ", "error");
            return;
        }

        hideAlert();
        resultCard.classList.add("hidden");
        loadingBox.classList.remove("hidden");
        fetchBtn.disabled = true;
        btnText.innerText = "စစ်ဆေးနေသည်...";

        try {
            const response = await fetch("/api/inspect", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: url })
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.message || "ဗီဒီယိုအချက်အလက် မရရှိနိုင်ပါ");
            }

            currentVideoData = result.data;
            renderPreview(currentVideoData);

        } catch (error) {
            showAlert(error.message, "error");
        } finally {
            loadingBox.classList.add("hidden");
            fetchBtn.disabled = false;
            btnText.innerText = "စစ်ဆေးမည် →";
        }
    }

    // Preview Card ပြသပေးခြင်း
    function renderPreview(data) {
        document.getElementById("resThumb").src = data.thumbnail;
        document.getElementById("resTitle").innerText = data.title;
        document.getElementById("resUploader").innerText = data.uploader;
        document.getElementById("resDuration").innerText = data.duration;

        const formatGrid = document.getElementById("formatGrid");
        formatGrid.innerHTML = "";

        const sizes = data.sizes || {};
        const options = [
            { label: "1080p Full HD", quality: "1080", size: sizes["1080"], icon: "🎬" },
            { label: "720p HD", quality: "720", size: sizes["720"], icon: "📹" },
            { label: "480p Normal", quality: "480", size: sizes["480"], icon: "📱" },
            { label: "MP3 Audio", quality: "mp3", size: sizes["mp3"], icon: "🎧" }
        ];

        options.forEach(opt => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "format-btn";
            btn.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 16px;">${opt.icon}</span>
                    <div>
                        <div class="format-label">${opt.label}</div>
                        <div class="format-size">${opt.size}</div>
                    </div>
                </div>
                <span style="font-size: 14px; color: #2563eb;">⬇</span>
            `;

            btn.addEventListener("click", () => triggerDownload(opt.quality));
            formatGrid.appendChild(btn);
        });

        resultCard.classList.remove("hidden");
    }

    // Download ဆွဲယူခြင်း
    async function triggerDownload(quality) {
        if (!currentVideoData) return;

        downloadProgressBar.classList.remove("hidden");

        try {
            const response = await fetch("/api/download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: currentVideoData.original_url,
                    quality: quality
                })
            });

            if (!response.ok) {
                throw new Error("ဒေါင်းလုဒ်လုပ်နေစဉ် အမှားအယွင်း ဖြစ်ပေါ်ခဲ့သည်");
            }

            const blob = await response.blob();
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = "video." + (quality === "mp3" ? "mp3" : "mp4");
            if (contentDisposition && contentDisposition.includes('filename=')) {
                filename = contentDisposition.split('filename=')[1].replace(/["']/g, '');
            }

            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = decodeURIComponent(filename);
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(downloadUrl);

            showAlert("Download စတင်ပါပြီ!", "success");

        } catch (err) {
            showAlert(err.message, "error");
        } finally {
            downloadProgressBar.classList.add("hidden");
        }
    }

    function showAlert(msg, type) {
        alertBox.innerText = msg;
        alertBox.className = "alert-box alert-" + type;
    }

    function hideAlert() {
        alertBox.className = "alert-box hidden";
    }
});