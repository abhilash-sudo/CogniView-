import { CognitiveController } from "./controller.js";
import { createFocusEngine } from "./focus.js";
import { createGestureEngine } from "./gesture.js";
import { createEmotionEngine } from "./emotion.js";
import { setControlState, setDot, showToast } from "../ui/controls.js";
import { attachLayoutHandlers } from "../ui/layout.js";

const controller = new CognitiveController({
    setControlState,
    toast: showToast
});

const shared = {
    controller,
    setControlState,
    setDot,
    showToast
};

const focusEngine = createFocusEngine(shared);
const gestureEngine = createGestureEngine(shared);
const emotionEngine = createEmotionEngine(shared);

window.toggleFocusGuard = () => focusEngine.start({
    stopGesture: gestureEngine.stop,
    stopEmotion: emotionEngine.stop
});
window.toggleGestures = () => gestureEngine.start({
    stopFocus: focusEngine.stop,
    stopEmotion: emotionEngine.stop
});
window.toggleEmotion = () => emotionEngine.start({
    stopFocus: focusEngine.stop,
    stopGesture: gestureEngine.stop
});
window.toggleHUD = () => focusEngine.toggleHUD();
window.cal = (el) => focusEngine.cal(el);
window.stopFocusGuard = focusEngine.stop;
window.stopGestures = gestureEngine.stop;
window.stopEmotion = emotionEngine.stop;
window.setControlState = setControlState;
window.setDot = setDot;
window.showToast = showToast;

attachLayoutHandlers();
