async function uploadVideo() {
    const videoInput = document.getElementById('videoInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const translateBtn = document.getElementById('translateBtn');

    if (videoInput.files.length === 0) {
        alert("Please select a video file to upload.");
        return;
    }

    const formData = new FormData();
    formData.append('file', videoInput.files[0]);

    uploadBtn.disabled = true;
    translateBtn.disabled = true;

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Upload failed.");
        }

        alert(data.message);
        translateBtn.disabled = false;
        showVideoThumbnail(data.video_path);

    } catch (err) {
        alert("Upload failed: " + err.message);
        console.error(err);
    } finally {
        uploadBtn.disabled = false;
    }
}

function showVideoThumbnail(videoPath) {
    const videoElement = document.getElementById('videoPlayer');
    const subtitleTrack = document.getElementById('subtitleTrack');

    videoElement.src = `/get_video?video_path=${encodeURIComponent(videoPath)}`;
    subtitleTrack.src = `/get_subtitles?video_path=${encodeURIComponent(videoPath)}`;
}

async function translateSubtitles() {
    const videoInput = document.getElementById('videoInput');
    const translateBtn = document.getElementById('translateBtn');
    const downloadVideoBtn = document.getElementById('downloadBtn');
    const downloadSubtitleBtn = document.getElementById('downloadSubtitleBtn');
    const progressBar = document.getElementById('progressBar');
    const selectedLanguage = document.getElementById('languageSelect').value;

    if (videoInput.files.length === 0) {
        alert("Please upload a video first.");
        return;
    }

    translateBtn.disabled = true;
    downloadVideoBtn.disabled = true;
    downloadSubtitleBtn.disabled = true;
    progressBar.style.display = 'block';
    progressBar.value = 5;

    const videoFilename = videoInput.files[0].name;

    try {
        const progressCheck = checkProgress();

        const response = await fetch('/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                video_file_path: videoFilename,
                target_language: selectedLanguage
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Translation failed.");
        }

        alert(data.message);
        downloadVideoBtn.disabled = false;
        downloadSubtitleBtn.disabled = false;
        await progressCheck;

    } catch (err) {
        alert("Translation error: " + err.message);
        console.error(err);
    } finally {
        translateBtn.disabled = false;
        progressBar.style.display = 'none';
    }
}

async function checkProgress() {
    const progressBar = document.getElementById('progressBar');
    let progress = 0;

    while (progress < 100) {
        await new Promise(resolve => setTimeout(resolve, 2000));

        try {
            const res = await fetch('/progress');
            const data = await res.json();

            progress = data.progress || 0;
            progressBar.value = progress;

            if (progress >= 100) break;
        } catch (err) {
            console.error("Progress check failed:", err);
            break;
        }
    }

    progressBar.value = 100;
    alert("Translation is completed. You can download now.");
}

async function downloadTranslatedSubtitles() {
    try {
        const response = await fetch('/download_translated_subtitles');
        if (!response.ok) {
            throw new Error("Subtitle file not found.");
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'translated_subtitles.vtt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

    } catch (err) {
        alert("Error downloading subtitles: " + err.message);
        console.error(err);
    }
}

async function downloadVideoWithSubtitles() {
    try {
        const response = await fetch('/download_video_with_subtitles');
        if (!response.ok) {
            throw new Error("Download failed.");
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = "video_with_subtitles.mp4";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

    } catch (err) {
        alert("Download error: " + err.message);
        console.error(err);
    }
}
