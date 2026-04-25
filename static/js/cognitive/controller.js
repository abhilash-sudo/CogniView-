export class CognitiveController {
    constructor(opts = {}) {
        this.state = {
            activeMode: null,
            focusActive: false,
            gestureActive: false,
            emotionActive: false,
            hudActive: false
        };
        this.setControlState = opts.setControlState || (() => {});
        this.toast = opts.toast || (() => {});
    }

    getState() {
        return this.state;
    }

    setMode(modeName, active) {
        const isActive = Boolean(active);
        if (modeName === "focus") this.state.focusActive = isActive;
        if (modeName === "gesture") this.state.gestureActive = isActive;
        if (modeName === "emotion") this.state.emotionActive = isActive;
        this.state.activeMode = isActive ? modeName : this._currentActiveMode();
    }

    _currentActiveMode() {
        if (this.state.focusActive) return "focus";
        if (this.state.gestureActive) return "gesture";
        if (this.state.emotionActive) return "emotion";
        return null;
    }

    setHUDActive(active) {
        this.state.hudActive = Boolean(active);
    }

    stopStream(stream) {
        if (!stream) return;
        try {
            stream.getTracks().forEach((t) => t.stop());
        } catch (e) {}
    }

    async requestCameraStream() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error("Camera API unavailable in this browser/context.");
        }
        const constraints = [
            { video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" } },
            { video: { facingMode: "user" } },
            { video: true }
        ];
        let lastErr = null;
        for (const c of constraints) {
            try {
                return await navigator.mediaDevices.getUserMedia(c);
            } catch (e) {
                lastErr = e;
            }
        }
        throw lastErr || new Error("Could not access camera.");
    }

    formatCameraError(err) {
        const name = err?.name || "UnknownError";
        if (name === "NotAllowedError" || name === "PermissionDeniedError") {
            return "Camera access denied. Allow permission in browser settings.";
        }
        if (name === "NotFoundError" || name === "DevicesNotFoundError") {
            return "No camera device found.";
        }
        if (name === "NotReadableError" || name === "TrackStartError") {
            return "Camera is busy. Close other apps using camera.";
        }
        if (name === "OverconstrainedError" || name === "ConstraintNotSatisfiedError") {
            return "Camera constraints unsupported on this device.";
        }
        if (name === "SecurityError") {
            return "Blocked by browser security policy. Use localhost and allow camera.";
        }
        return err?.message || "Unknown camera error.";
    }
}
