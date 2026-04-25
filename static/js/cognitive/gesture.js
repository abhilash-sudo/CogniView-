export function createGestureEngine(ctx) {
    let hands;
    let stream = null;
    let videoEl = null;
    let rafId = null;
    let lastGesture = "";
    let stableCount = 0;
    let canvasEl;
    let canvasCtx;

    function stop(showToast = false) {
        ctx.controller.setMode("gesture", false);
        cancelAnimationFrame(rafId);
        if (stream) {
            ctx.controller.stopStream(stream);
            stream = null;
        }
        if (videoEl) {
            videoEl.remove();
            videoEl = null;
        }
        const c = document.getElementById("gesture-canvas");
        if (c) c.style.display = "none";
        ctx.setDot("dot-gesture", "");
        ctx.setControlState("btn-gesture", "");
        if (showToast) ctx.showToast("✋ Gesture Control Off");
    }

    async function start({ stopFocus, stopEmotion }) {
        if (ctx.controller.getState().gestureActive) {
            stop(true);
            return;
        }
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
                    locateFile: (f) => new URL(f, "https://cdn.jsdelivr.net/npm/@mediapipe/hands/").toString()
                });
                hands.setOptions({ maxNumHands: 1, modelComplexity: 1, minDetectionConfidence: 0.6, minTrackingConfidence: 0.5 });
                hands.onResults(onResults);
            }
            ctx.controller.setMode("gesture", true);
            lastGesture = "";
            stableCount = 0;
            document.getElementById("gesture-canvas").style.display = "block";
            ctx.setDot("dot-gesture", "active");
            ctx.setControlState("btn-gesture", "active");
            ctx.showToast("✋ Gesture Control Active");
            loop();
        } catch (err) {
            stop(false);
            ctx.showToast("⚠️ Gesture camera error: " + ctx.controller.formatCameraError(err));
            console.error("[Gesture]", err);
        }
    }

    async function loop() {
        if (!ctx.controller.getState().gestureActive) return;
        if (videoEl && videoEl.readyState >= 2) {
            await hands.send({ image: videoEl });
        }
        rafId = requestAnimationFrame(loop);
    }

    function onResults(results) {
        if (!ctx.controller.getState().gestureActive) return;
        canvasCtx.save();
        canvasCtx.clearRect(0, 0, canvasEl.width, canvasEl.height);
        canvasCtx.drawImage(results.image, 0, 0, canvasEl.width, canvasEl.height);
        const vid = document.getElementById("vid");
        if (results.multiHandLandmarks) {
            for (const lm of results.multiHandLandmarks) {
                window.drawConnectors(canvasCtx, lm, window.HAND_CONNECTIONS, { color: "#06B6D4", lineWidth: 5 });
                window.drawLandmarks(canvasCtx, lm, { color: "#F8FAFC", lineWidth: 2 });
                let fingers = 0;
                if (lm[8].y < lm[5].y) fingers++;
                if (lm[12].y < lm[9].y) fingers++;
                if (lm[16].y < lm[13].y) fingers++;
                if (lm[20].y < lm[17].y) fingers++;
                let current = "";
                if (fingers >= 4) current = "OPEN";
                else if (fingers === 0) current = "FIST";
                else if (fingers === 1 || fingers === 2) current = "POINT";
                canvasCtx.fillStyle = "white";
                canvasCtx.font = "30px Arial";
                canvasCtx.fillText(current, 10, 30);
                stableCount = current === lastGesture ? stableCount + 1 : 1;
                lastGesture = current;
                if (stableCount >= 3) {
                    if (current === "OPEN" && !vid.paused) { vid.pause(); ctx.showToast("✋ PAUSED"); }
                    if (current === "FIST" && vid.paused) { vid.play(); ctx.showToast("✊ PLAYING"); }
                    stableCount = 0;
                }
            }
        }
        canvasCtx.restore();
    }

    return { start, stop };
}
