import { setControlState, showToast } from "./controls.js";

export function attachLayoutHandlers() {
    // Restore dock state
    try {
        const docked = localStorage.getItem("cogniview.videoDocked") === "1";
        if (docked) {
            document.body.classList.add("video-docked");
            setControlState("btn-dock", "active");
        }
    } catch (e) {}

    window.toggleVideoDock = function toggleVideoDock() {
        const docked = document.body.classList.toggle("video-docked");
        try { localStorage.setItem("cogniview.videoDocked", docked ? "1" : "0"); } catch (e) {}
        setControlState("btn-dock", docked ? "active" : "");
        showToast(docked ? "📺 Video docked to corner" : "📺 Video returned to main stage");
    };
}
