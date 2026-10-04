function toggleMenu() {
    const menu = document.getElementById("navigation");
    menu.classList.toggle("show");
}

function copyText(elementId) {
    const el = document.getElementById(elementId);
    const text = el.textContent.trim();
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showCopied(el);
        });
    } else {

        const range = document.createRange();
        range.selectNodeContents(el);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.execCommand("copy");
        sel.removeAllRanges();
        showCopied(el);
    }
}

function showCopied(el) {
    const original = el.style.background;
    el.style.background = "#e6f4ea";
    el.style.transition = "background 0.3s";
    setTimeout(() => { el.style.background = original; }, 800);
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".flash:not(.flash-creds)").forEach(el => {
        setTimeout(() => {
            el.style.transition = "opacity 0.5s";
            el.style.opacity = "0";
            setTimeout(() => el.remove(), 500);
        }, 4000);
    });
});

function togglePw(btn) {
    const input = btn.parentElement.querySelector("input");
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.textContent = show ? "Hide" : "Show";
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("[data-auth-form]");
    if (!form) return;
    const confirm = form.querySelector("#confirm");
    const pw = form.querySelector("#password");
    if (confirm && pw) {
        const check = () => confirm.setCustomValidity(
            confirm.value && confirm.value !== pw.value ? "Passwords do not match" : "");
        pw.addEventListener("input", check);
        confirm.addEventListener("input", check);
    }
});

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-gallery]").forEach(g => {
        const hero = g.querySelector(".pg-hero");
        const counter = g.querySelector(".pg-counter");
        const caption = g.querySelector(".pg-caption");
        const thumbs = Array.from(g.querySelectorAll(".pg-thumb"));
        let index = 0;

        function show(i) {
            index = (i + thumbs.length) % thumbs.length;
            const t = thumbs[index];
            hero.src = t.dataset.src;
            hero.alt = t.dataset.caption;
            caption.textContent = t.dataset.caption;
            counter.textContent = (index + 1) + " / " + thumbs.length;
            thumbs.forEach(x => x.classList.remove("active"));
            t.classList.add("active");
            t.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
        }
        thumbs.forEach((t, i) => t.addEventListener("click", () => show(i)));
        g.querySelector(".pg-prev").addEventListener("click", () => show(index - 1));
        g.querySelector(".pg-next").addEventListener("click", () => show(index + 1));
        if (thumbs.length < 2) g.querySelectorAll(".pg-nav, .pg-counter").forEach(e => e.style.display = "none");

        let x0 = null;
        hero.addEventListener("touchstart", e => { x0 = e.touches[0].clientX; }, { passive: true });
        hero.addEventListener("touchend", e => {
            if (x0 === null) return;
            const dx = e.changedTouches[0].clientX - x0;
            if (Math.abs(dx) > 40) show(index + (dx < 0 ? 1 : -1));
            x0 = null;
        });

        hero.addEventListener("click", () => {
            const box = document.createElement("div");
            box.className = "lightbox";
            box.innerHTML = '<img alt=""><div class="lb-cap"></div>' +
                '<button class="lb-close" aria-label="Close">×</button>' +
                '<button class="lb-prev" aria-label="Previous">‹</button>' +
                '<button class="lb-next" aria-label="Next">›</button>';
            const img = box.querySelector("img"), cap = box.querySelector(".lb-cap");
            const paint = () => { img.src = thumbs[index].dataset.src; cap.textContent = thumbs[index].dataset.caption; };
            const close = () => { box.remove(); document.removeEventListener("keydown", onKey); };
            const step = d => { show(index + d); paint(); };
            const onKey = e => {
                if (e.key === "Escape") close();
                if (e.key === "ArrowRight") step(1);
                if (e.key === "ArrowLeft") step(-1);
            };
            box.querySelector(".lb-close").onclick = close;
            box.querySelector(".lb-prev").onclick = () => step(-1);
            box.querySelector(".lb-next").onclick = () => step(1);
            box.addEventListener("click", e => { if (e.target === box) close(); });
            document.addEventListener("keydown", onKey);
            document.body.appendChild(box);
            paint();
        });
    });
});
