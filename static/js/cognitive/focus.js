export function createFocusEngine(ctx) {
    let focusScore = 100;
    let lookAwayFrames = 0;
    let stream = null;
    let videoEl = null;
    let rafId = null;
    let active = false;
    let faceDetection;
    let pausedByFocusGuard = false;
    let lastTelemetryAt = 0;

    function stop(showToast = true) {
        active = false;
        ctx.controller.setMode("focus", false);
        cancelAnimationFrame(rafId);
        if (stream) { ctx.controller.stopStream(stream); stream = null; }
        if (videoEl) { videoEl.remove(); videoEl = null; }
        
        const vid = document.getElementById("vid");
        if (pausedByFocusGuard && vid?.paused) vid.play();
        pausedByFocusGuard = false;
        
        document.getElementById("focus-overlay").style.display = "none";
        document.getElementById("hud-layer").style.display = "none";
        ctx.controller.setHUDActive(false);
        ctx.setDot("dot-focus", "");
        ctx.setControlState("btn-focus", "");
        ctx.setControlState("btn-hud", "");
        
        if (window.cwUpdateFocus) window.cwUpdateFocus(0, false);
        if (showToast) ctx.showToast("👁️ Focus Guard Deactivated");
    }

    async function start({ stopGesture, stopEmotion }) {
        if (ctx.controller.getState().focusActive) {
            stop(true);
            return;
        }
        if (ctx.controller.getState().gestureActive) stopGesture(false);
        if (ctx.controller.getState().emotionActive) stopEmotion(false);

        ctx.showToast("📷 Requesting camera access…");
        ctx.setDot("dot-focus", "warn");
        ctx.setControlState("btn-focus", "warn");
        
        try {
            stream = await ctx.controller.requestCameraStream();
            videoEl = document.createElement("video");
            videoEl.srcObject = stream;
            videoEl.style.display = "none";
            videoEl.playsInline = true;
            document.body.appendChild(videoEl);
            await videoEl.play();
            
            if (!faceDetection) {
                faceDetection = new window.FaceDetection({
                    locateFile: (f) => {
                        if (f.includes('face_mesh')) return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${f}`;
                        if (f.includes('hands')) return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}`;
                        return `https://cdn.jsdelivr.net/npm/@mediapipe/face_detection/${f}`;
                    }
                });
                faceDetection.setOptions({
                    model: 'short',
                    minDetectionConfidence: 0.4
                });
                faceDetection.onResults(onResults);
            }
            
            active = true;
            focusScore = 100;
            lookAwayFrames = 0;
            
            ctx.controller.setMode("focus", true);
            ctx.setDot("dot-focus", "active");
            ctx.setControlState("btn-focus", "active");
            ctx.showToast("✅ Focus Guard Active! (Zero Calibration)");
            loop();
        } catch (err) {
            stop(false);
            ctx.showToast("⚠️ Focus camera error: " + ctx.controller.formatCameraError(err));
            console.error("[FocusGuard]", err);
        }
    }

    async function loop() {
        if (!ctx.controller.getState().focusActive) return;
        if (videoEl && videoEl.readyState >= 2) await faceDetection.send({ image: videoEl });
        rafId = requestAnimationFrame(loop);
    }

    function onResults(results) {
        if (!ctx.controller.getState().focusActive) return;
        
        const vid = document.getElementById("vid");
        const overlay = document.getElementById("focus-overlay");
        
        // If a face is detected, focus is high. If no face is detected, focus drops.
        const hit = results.detections && results.detections.length > 0;
        
        // Rapid focus drop to immediately pause the video
        focusScore = hit ? Math.min(100, focusScore + 1.0) : Math.max(0, focusScore - 5.0);

        if (window.cwUpdateFocus) window.cwUpdateFocus(focusScore, true);
        const now = Date.now();
        if (window.CogniViewTelemetry && now - lastTelemetryAt > 4500) {
            lastTelemetryAt = now;
            window.CogniViewTelemetry.recordEvent("focus_sample", {
                signal: hit ? "face_locked" : "face_lost",
                value: Math.round(focusScore),
                state: hit ? "locked" : "lost"
            });
        }

        if (ctx.controller.getState().hudActive) {
            document.getElementById("hud-score").innerText = `FOCUS: ${Math.floor(focusScore)}%`;
            document.getElementById("hud-reticle").style.borderColor = hit ? "var(--accent)" : "var(--red)";
            document.getElementById("hud-msg").innerText = hit ? "LOCKED ON" : "TARGET LOST";
            document.getElementById("hud-msg").style.color = hit ? "var(--accent)" : "var(--red)";
            
            // Just place reticle at center of screen for effect since we don't track eye gaze X/Y anymore
            const rect = vid.getBoundingClientRect();
            const reticle = document.getElementById("hud-reticle");
            reticle.style.left = (rect.width / 2) + "px";
            reticle.style.top = (rect.height / 2) + "px";
        }
        
        if (focusScore > 30) {
            lookAwayFrames = 0;
            overlay.style.display = "none";
            if (pausedByFocusGuard && vid.paused) {
                vid.play();
                pausedByFocusGuard = false;
            }
        } else {
            lookAwayFrames++;
            if (lookAwayFrames > 3) {
                overlay.style.display = "flex";
                if (!vid.paused) {
                    vid.pause();
                    pausedByFocusGuard = true;
                    window.CogniViewTelemetry?.recordEvent("focus_guard_pause", {
                        signal: "low_focus",
                        value: Math.round(focusScore)
                    });
                    if (window.cwAlertTick) window.cwAlertTick();
                }
            }
        }
    }

    function toggleHUD() {
        if (!ctx.controller.getState().focusActive) {
            ctx.showToast("👁️ Enable FOCUS GUARD first");
            return;
        }
        const next = !ctx.controller.getState().hudActive;
        ctx.controller.setHUDActive(next);
        document.getElementById("hud-layer").style.display = next ? "block" : "none";
        ctx.setControlState("btn-hud", next ? "active" : "");
    }

    return { start, stop, toggleHUD };
}
