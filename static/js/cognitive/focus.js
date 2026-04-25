export function createFocusEngine(ctx) {
    let calPoints = 0;
    let focusScore = 100;
    let gazeBuffer = [];
    let lookAwayFrames = 0;
    let permissionStream = null;

    function resetCalibrationDots() {
        document.querySelectorAll(".calibration-dot").forEach((el) => {
            delete el.dataset.calDone;
            el.style.backgroundColor = "";
            el.style.transform = "";
            el.style.display = "none";
        });
    }

    function stop(showToast = true) {
        try { window.webgazer?.end(); } catch (e) {}
        if (permissionStream) {
            ctx.controller.stopStream(permissionStream);
            permissionStream = null;
        }
        const vid = document.getElementById("vid");
        if (vid?.paused) vid.play();
        document.getElementById("focus-overlay").style.display = "none";
        document.getElementById("hud-layer").style.display = "none";
        ctx.controller.setHUDActive(false);
        ctx.setDot("dot-focus", "");
        ctx.setControlState("btn-focus", "");
        ctx.setControlState("btn-hud", "");
        ctx.controller.setMode("focus", false);
        resetCalibrationDots();
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
            permissionStream = await ctx.controller.requestCameraStream();
            ctx.controller.stopStream(permissionStream);
            permissionStream = null;
            if (!window.webgazer || typeof window.webgazer.begin !== "function") {
                throw new Error("Focus engine failed to load. Refresh page and try again.");
            }
            await window.webgazer
                .setRegression("ridge")
                .showVideoPreview(false)
                .showPredictionPoints(false)
                .begin();
            window.webgazer.setGazeListener(onGazeData);

            calPoints = 0;
            focusScore = 100;
            lookAwayFrames = 0;
            gazeBuffer = [];
            document.querySelectorAll(".calibration-dot").forEach((el) => el.style.display = "block");
            ctx.controller.setMode("focus", true);
            ctx.setDot("dot-focus", "active");
            ctx.setControlState("btn-focus", "active");
            ctx.showToast("✅ Camera Active! Click all 9 dots to calibrate.");
        } catch (err) {
            if (permissionStream) {
                ctx.controller.stopStream(permissionStream);
                permissionStream = null;
            }
            ctx.setDot("dot-focus", "");
            ctx.setControlState("btn-focus", "");
            ctx.showToast("⚠️ Focus camera error: " + ctx.controller.formatCameraError(err));
            console.error("[FocusGuard]", err);
        }
    }

    function onGazeData(data) {
        if (!data || !ctx.controller.getState().focusActive) return;
        gazeBuffer.push({ x: data.x, y: data.y });
        if (gazeBuffer.length > 5) gazeBuffer.shift();
        const sx = gazeBuffer.reduce((a, b) => a + b.x, 0) / gazeBuffer.length;
        const sy = gazeBuffer.reduce((a, b) => a + b.y, 0) / gazeBuffer.length;

        const vid = document.getElementById("vid");
        const overlay = document.getElementById("focus-overlay");
        const rect = vid.getBoundingClientRect();
        if (ctx.controller.getState().hudActive) {
            const reticle = document.getElementById("hud-reticle");
            reticle.style.left = (sx - rect.left) + "px";
            reticle.style.top = (sy - rect.top) + "px";
        }
        const hit = sx > rect.left - 120 && sx < rect.right + 120 && sy > rect.top - 80 && sy < rect.bottom + 80;
        focusScore = hit ? Math.min(100, focusScore + 0.3) : Math.max(0, focusScore - 0.4);
        if (ctx.controller.getState().hudActive) {
            document.getElementById("hud-score").innerText = `FOCUS: ${Math.floor(focusScore)}%`;
            document.getElementById("hud-reticle").style.borderColor = hit ? "var(--accent)" : "var(--red)";
            document.getElementById("hud-msg").innerText = hit ? "LOCKED ON" : "TARGET LOST";
            document.getElementById("hud-msg").style.color = hit ? "var(--accent)" : "var(--red)";
        }
        if (hit) {
            lookAwayFrames = 0;
            overlay.style.display = "none";
            if (vid.paused && calPoints >= 9) vid.play();
        } else {
            lookAwayFrames++;
            if (lookAwayFrames > 8) {
                overlay.style.display = "flex";
                if (!vid.paused) vid.pause();
            }
        }
    }

    function cal(el) {
        if (el.dataset.calDone === "1") return;
        el.dataset.calDone = "1";
        el.style.backgroundColor = "#34D399";
        el.style.transform = "scale(1.5)";
        setTimeout(() => { el.style.transform = "scale(1)"; }, 200);
        calPoints++;
        if (calPoints >= 9) {
            document.querySelectorAll(".calibration-dot").forEach((e) => e.style.display = "none");
            ctx.showToast("🎯 Calibration Complete! Focus Guard is ACTIVE.");
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

    return { start, stop, cal, toggleHUD };
}
