export function setControlState(btnId, state) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.classList.remove("active", "warn");
    if (state === "active") btn.classList.add("active");
    if (state === "warn") btn.classList.add("warn");
}

export function setDot(id, state) {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = "feat-dot" + (state ? " " + state : "");
}

export function showToast(msg) {
    document.querySelectorAll(".cogni-toast").forEach((t) => t.remove());
    const t = document.createElement("div");
    t.className = "cogni-toast";
    t.style.cssText = [
        "position:fixed", "bottom:24px", "right:24px", "z-index:9999",
        "background:linear-gradient(135deg,rgba(15,23,42,0.98),rgba(30,41,59,0.98))",
        "border:1px solid rgba(6,182,212,0.4)",
        "color:var(--text-primary)",
        "padding:12px 20px",
        "border-radius:12px",
        "font-size:0.9rem", "font-weight:600",
        "box-shadow:0 8px 24px rgba(0,0,0,0.4),0 0 20px rgba(6,182,212,0.1)",
        "opacity:0", "transform:translateY(10px)",
        "transition:opacity 0.25s,transform 0.25s",
        "max-width:320px", "pointer-events:none"
    ].join(";");
    t.textContent = msg;
    document.body.appendChild(t);
    requestAnimationFrame(() => {
        t.style.opacity = "1";
        t.style.transform = "translateY(0)";
    });
    setTimeout(() => {
        t.style.opacity = "0";
        t.style.transform = "translateY(10px)";
        setTimeout(() => t.remove(), 300);
    }, 3000);
}
