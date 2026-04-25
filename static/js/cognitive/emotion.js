export function createEmotionEngine(ctx) {
    let faceMesh;
    let stream = null;
    let videoEl = null;
    let rafId = null;
    let active = false;
    let canvasEl;
    let canvasCtx;
    let confusionFrames = 0;
    let isExplaining = false;

    function stop(showToast = true) {
        active = false;
        ctx.controller.setMode("emotion", false);
        cancelAnimationFrame(rafId);
        if (stream) {
            ctx.controller.stopStream(stream);
            stream = null;
        }
        if (videoEl) {
            videoEl.remove();
            videoEl = null;
        }
        const canvas = document.getElementById("emotion-canvas");
        if (canvas) canvas.style.display = "none";
        ctx.setDot("dot-emotion", "");
        ctx.setControlState("btn-emotion", "");
        if (showToast) ctx.showToast("🎭 Emotion Engine Off");
    }

    async function start({ stopFocus, stopGesture }) {
        if (active) {
            stop(true);
            return;
        }
        if (ctx.controller.getState().focusActive) stopFocus(false);
        if (ctx.controller.getState().gestureActive) stopGesture(false);
        ctx.showToast("📷 Starting Emotion Engine...");
        ctx.setDot("dot-emotion", "warn");
        ctx.setControlState("btn-emotion", "warn");
        try {
            stream = await ctx.controller.requestCameraStream();
            videoEl = document.createElement("video");
            videoEl.srcObject = stream;
            videoEl.style.display = "none";
            videoEl.playsInline = true;
            document.body.appendChild(videoEl);
            await videoEl.play();
            if (!faceMesh) {
                canvasEl = document.getElementById("emotion-canvas");
                canvasCtx = canvasEl.getContext("2d");
                faceMesh = new window.FaceMesh({
                    locateFile: (file) => new URL(file, "https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/").toString()
                });
                faceMesh.setOptions({
                    maxNumFaces: 1,
                    refineLandmarks: true,
                    minDetectionConfidence: 0.5,
                    minTrackingConfidence: 0.5
                });
                faceMesh.onResults(onResults);
            }
            active = true;
            ctx.controller.setMode("emotion", true);
            document.getElementById("emotion-canvas").style.display = "block";
            ctx.setDot("dot-emotion", "active");
            ctx.setControlState("btn-emotion", "active");
            ctx.showToast("🎭 Emotion Engine Active");
            loop();
        } catch (err) {
            stop(false);
            ctx.showToast("⚠️ Emotion camera error: " + ctx.controller.formatCameraError(err));
            console.error("[EmotionEngine]", err);
        }
    }

    async function loop() {
        if (!active) return;
        if (videoEl && videoEl.readyState >= 2) {
            await faceMesh.send({ image: videoEl });
        }
        rafId = requestAnimationFrame(loop);
    }

    function onResults(results) {
        if (!active || isExplaining) return;
        canvasCtx.save();
        canvasCtx.clearRect(0, 0, canvasEl.width, canvasEl.height);
        canvasCtx.drawImage(results.image, 0, 0, canvasEl.width, canvasEl.height);
        canvasCtx.fillStyle = "rgba(6, 8, 17, 0.45)";
        canvasCtx.fillRect(0, 0, canvasEl.width, canvasEl.height);
        if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
            const lm = results.multiFaceLandmarks[0];
            const leftBrow = lm[105], rightBrow = lm[334], leftFace = lm[234], rightFace = lm[454];
            const faceWidth = Math.hypot(rightFace.x - leftFace.x, rightFace.y - leftFace.y);
            const browDist = Math.hypot(rightBrow.x - leftBrow.x, rightBrow.y - leftBrow.y);
            const browRatio = browDist / (faceWidth + 0.001);
            const browSignal = browRatio < 0.18 ? 1 : (browRatio < 0.22 ? 0.4 : 0);
            const lEyeH = Math.hypot(lm[159].x - lm[145].x, lm[159].y - lm[145].y);
            const lEyeW = Math.hypot(lm[33].x - lm[133].x, lm[33].y - lm[133].y);
            const rEyeH = Math.hypot(lm[386].x - lm[374].x, lm[386].y - lm[374].y);
            const rEyeW = Math.hypot(lm[362].x - lm[263].x, lm[362].y - lm[263].y);
            const avgEAR = ((lEyeH / (lEyeW + 0.001)) + (rEyeH / (rEyeW + 0.001))) / 2;
            const eyeSignal = avgEAR < 0.12 ? 1 : (avgEAR < 0.18 ? 0.3 : 0);
            const mouthH = Math.hypot(lm[13].x - lm[14].x, lm[13].y - lm[14].y);
            const mouthW = Math.hypot(lm[61].x - lm[291].x, lm[61].y - lm[291].y);
            const mouthSignal = (mouthH / (mouthW + 0.001)) > 0.15 ? Math.min(1, (mouthH / (mouthW + 0.001)) * 4) : 0;
            const confusionScore = (browSignal * 0.55) + (eyeSignal * 0.25) + (mouthSignal * 0.2);
            const confusionPct = Math.round(confusionScore * 100);
            let label = "✅ Focused", color = "#34D399";
            if (confusionScore > 0.55) { label = "😕 Confused"; color = "#FB7185"; confusionFrames++; }
            else if (confusionScore > 0.3) { label = "🤔 Thinking"; color = "#F59E0B"; confusionFrames = Math.max(0, confusionFrames - 1); }
            else { confusionFrames = Math.max(0, confusionFrames - 3); }
            canvasCtx.fillStyle = "rgba(0,0,0,0.75)";
            canvasCtx.fillRect(6, 6, 210, 26);
            canvasCtx.fillStyle = color;
            canvasCtx.font = "bold 13px Outfit, Arial";
            canvasCtx.fillText(`${label}  ${confusionPct}%`, 12, 23);
            if (confusionFrames > 45) triggerExplanation();
        } else {
            canvasCtx.fillStyle = "rgba(0,0,0,0.6)";
            canvasCtx.fillRect(6, 6, 170, 24);
            canvasCtx.fillStyle = "#94A3B8";
            canvasCtx.font = "12px Arial";
            canvasCtx.fillText("👤 No face detected", 12, 22);
        }
        canvasCtx.restore();
    }

    async function triggerExplanation() {
        isExplaining = true;
        confusionFrames = 0;
        const vid = document.getElementById("vid");
        vid.pause();
        ctx.showToast("🧠 CONFUSION DETECTED");
        const c = document.getElementById("chat");
        c.innerHTML += `<div class="bubble ai" style="color:var(--red);">Analyzing facial expressions... High Cognitive Load detected. Asking AI for an explanation...</div>`;
        c.scrollTop = c.scrollHeight;
        try {
            const r = await fetch("/explain_context", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ timestamp: vid.currentTime })
            });
            const d = await r.json();
            c.innerHTML += `<div class="bubble ai" style="border: 1px solid var(--red); box-shadow: 0 0 10px var(--red);">${(d.explanation || "").replace(/\n/g, "<br>")}</div>`;
        } catch (e) {
            c.innerHTML += `<div class="bubble ai" style="color:var(--red)">Connection Failure.</div>`;
        }
        c.scrollTop = c.scrollHeight;
        setTimeout(() => { isExplaining = false; }, 10000);
    }

    return { start, stop };
}
