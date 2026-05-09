export function createGestureEngine(ctx) {
    let hands;
    let stream = null;
    let videoEl = null;
    let rafId = null;
    let lastGesture = "";
    let stableCount = 0;
    let canvasEl;
    let canvasCtx;
    let muted = false;
    let lastActionTime = 0; // debounce actions
    let lastTelemetryAt = 0;

    function stop(showToast = false) {
        ctx.controller.setMode("gesture", false);
        cancelAnimationFrame(rafId);
        if (stream) { ctx.controller.stopStream(stream); stream = null; }
        if (videoEl) { videoEl.remove(); videoEl = null; }
        const c = document.getElementById("gesture-canvas");
        if (c) c.style.display = "none";
        ctx.setDot("dot-gesture", "");
        ctx.setControlState("btn-gesture", "");
        if (showToast) ctx.showToast("✋ Gesture Control Off");
    }

    async function start({ stopFocus, stopEmotion }) {
        if (ctx.controller.getState().gestureActive) { stop(true); return; }
        if (ctx.controller.getState().focusActive) stopFocus(false);
        if (ctx.controller.getState().emotionActive) stopEmotion(false);
        ctx.showToast("✋ Starting Gesture Engine...");
        ctx.setDot("dot-gesture", "warn");
        ctx.setControlState("btn-gesture", "warn");
        try {
            stream = await ctx.controller.requestCameraStream();
            videoEl = document.createElement("video");
            videoEl.srcObject = stream;
            videoEl.style.display = "none";
            videoEl.playsInline = true;
            document.body.appendChild(videoEl);
            await videoEl.play();
            if (!hands) {
                canvasEl = document.getElementById("gesture-canvas");
                canvasCtx = canvasEl.getContext("2d");
                hands = new window.Hands({
                    locateFile: (f) => {
                        if (f.includes('face_mesh')) return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${f}`;
                        return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}`;
                    }
                });
                hands.setOptions({ maxNumHands: 1, modelComplexity: 0, minDetectionConfidence: 0.3, minTrackingConfidence: 0.3 });
                hands.onResults(onResults);
            }
            ctx.controller.setMode("gesture", true);
            lastGesture = "";
            stableCount = 0;
            document.getElementById("gesture-canvas").style.display = "block";
            ctx.setDot("dot-gesture", "active");
            ctx.setControlState("btn-gesture", "active");
            ctx.showToast("✋ Gesture Active | ✊=Play | ✋=Pause | 👍=+10s | ✌️=-10s | 🤙=Mute");
            loop();
        } catch (err) {
            stop(false);
            ctx.showToast("⚠️ Gesture camera error: " + ctx.controller.formatCameraError(err));
            console.error("[Gesture]", err);
        }
    }

    async function loop() {
        if (!ctx.controller.getState().gestureActive) return;
        if (videoEl && videoEl.readyState >= 2) await hands.send({ image: videoEl });
        rafId = requestAnimationFrame(loop);
    }

    function classify(lm) {
        // Extended fingers: tip y < mcp y (base of finger) is more reliable
        const indexUp  = lm[8].y  < lm[5].y;
        const middleUp = lm[12].y < lm[9].y;
        const ringUp   = lm[16].y < lm[13].y;
        const pinkyUp  = lm[20].y < lm[17].y;

        // Thumb: compare tip vs mcp
        const thumbUp  = lm[4].y < lm[3].y;
        const thumbOut = Math.abs(lm[4].x - lm[9].x) > 0.04;
        const pinchDist = Math.hypot(lm[4].x - lm[8].x, lm[4].y - lm[8].y);

        const extCount = [indexUp, middleUp, ringUp, pinkyUp].filter(Boolean).length;

        if (pinchDist < 0.045 && middleUp && ringUp) return "PINCH";
        // THUMBS UP: only thumb out, all fingers curled
        if (thumbOut && thumbUp && !indexUp && !middleUp && !ringUp && !pinkyUp) return "THUMBS_UP";
        // PEACE: index + middle up, ring + pinky down, thumb tucked
        if (indexUp && middleUp && !ringUp && !pinkyUp) return "PEACE";
        // OPEN: 4 fingers up
        if (extCount >= 4) return "OPEN";
        // FIST: all fingers curled
        if (extCount === 0 && !thumbOut) return "FIST";
        // POINT: only index up
        if (indexUp && !middleUp && !ringUp && !pinkyUp) return "POINT";
        return "";
    }

    function onResults(results) {
        if (!ctx.controller.getState().gestureActive) return;
        canvasCtx.save();
        canvasCtx.clearRect(0, 0, canvasEl.width, canvasEl.height);
        canvasCtx.drawImage(results.image, 0, 0, canvasEl.width, canvasEl.height);
        // Dark overlay
        canvasCtx.fillStyle = "rgba(6,8,17,0.4)";
        canvasCtx.fillRect(0, 0, canvasEl.width, canvasEl.height);

        const vid = document.getElementById("vid");
        const now = Date.now();

        if (results.multiHandLandmarks) {
            for (const lm of results.multiHandLandmarks) {
                window.drawConnectors(canvasCtx, lm, window.HAND_CONNECTIONS, { color: "#06B6D4", lineWidth: 3 });
                window.drawLandmarks(canvasCtx, lm, { color: "#F8FAFC", lineWidth: 1, radius: 2 });

                const current = classify(lm);

                // Gesture label HUD
                const GESTURE_LABELS = {
                    OPEN: "✋ PAUSE", FIST: "✊ PLAY", POINT: "☝️ MUTE",
                    THUMBS_UP: "👍 +10s", PEACE: "✌️ -10s"
                };
                GESTURE_LABELS.PINCH = "PINCH NOTE";
                const label = GESTURE_LABELS[current] || "";
                if (label) {
                    canvasCtx.fillStyle = "rgba(0,0,0,0.75)";
                    canvasCtx.fillRect(4, 4, 130, 26);
                    canvasCtx.fillStyle = "#C8FF00";
                    canvasCtx.font = "bold 13px Outfit, Arial";
                    canvasCtx.fillText(label, 8, 21);
                }

                if (current === lastGesture && current !== "") {
                    stableCount++;
                } else {
                    stableCount = 1;
                }
                lastGesture = current;
                const nowTelemetry = Date.now();
                if (current && window.CogniViewTelemetry && nowTelemetry - lastTelemetryAt > 2500) {
                    lastTelemetryAt = nowTelemetry;
                    window.CogniViewTelemetry.recordEvent("gesture_seen", {
                        signal: current,
                        value: 1
                    });
                }

                if (stableCount >= 2 && (now - lastActionTime) > 1500) {
                    lastActionTime = now;
                    stableCount = 0;
                    if (current) window.CogniViewTelemetry?.recordEvent("gesture_action", { signal: current, value: 1 });
                    if (current === "OPEN" && !vid.paused)  { vid.pause(); ctx.showToast("✋ PAUSED"); }
                    if (current === "FIST" && vid.paused)   { vid.play();  ctx.showToast("✊ PLAYING"); }
                    if (current === "THUMBS_UP")             { vid.currentTime = Math.min(vid.duration, vid.currentTime + 10); ctx.showToast("👍 +10 seconds"); }
                    if (current === "PEACE")                 { vid.currentTime = Math.max(0, vid.currentTime - 10); ctx.showToast("✌️ -10 seconds"); }
                    if (current === "PINCH") {
                        window.quickCaptureNote?.("Gesture checkpoint");
                        ctx.showToast("Checkpoint note captured");
                    }
                    if (current === "POINT") {
                        muted = !muted;
                        vid.muted = muted;
                        window.CogniViewTelemetry?.recordEvent("gesture_action", { signal: current, value: muted ? 1 : 0 });
                        ctx.showToast(muted ? "🔇 Muted" : "🔊 Unmuted");
                    }
                }
            }
        } else {
            canvasCtx.fillStyle = "rgba(148,163,184,0.5)";
            canvasCtx.font = "11px Arial";
            canvasCtx.fillText("No hand detected", 6, 20);
        }
        canvasCtx.restore();
    }

    return { start, stop };
}
