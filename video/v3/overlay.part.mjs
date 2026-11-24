// Injected into every page: cursor, tap ripple, count-ups, feature label, verse lower-third, caption.
const overlay = (o = {}) => `(${(o) => {
  addEventListener("DOMContentLoaded", () => {
    const st = document.createElement("style");
    st.textContent = `.fixed.bottom-4{display:none}
      #fcur{position:fixed;left:0;top:0;z-index:9999;width:34px;height:34px;pointer-events:none;transition:transform .5s cubic-bezier(.3,.7,.2,1);transform:translate(1250px,760px);filter:drop-shadow(0 3px 6px rgba(0,0,0,.35))}
      .frip{position:fixed;z-index:9998;width:24px;height:24px;margin:-12px 0 0 -12px;border-radius:50%;border:3px solid #e9c176;background:rgba(233,193,118,.35);pointer-events:none;animation:frip .6s ease-out forwards}
      @keyframes frip{to{transform:scale(3.4);opacity:0}}
      #flab{position:fixed;top:22px;right:26px;z-index:9997;background:#041632;color:#fbf9f5;font:700 20px Inter,sans-serif;letter-spacing:.14em;text-transform:uppercase;padding:14px 22px;border-radius:12px;border-left:6px solid #e9c176;box-shadow:0 10px 30px rgba(4,22,50,.3);transform:translateX(140%);transition:transform .45s cubic-bezier(.2,.9,.25,1.1)}`;
    document.head.appendChild(st);
    if (window !== top) return;
    const css = document.createElement("link"); css.rel = "stylesheet"; css.href = "/static/film/overlay.css"; document.head.appendChild(css);
    if (o.verse) document.body.insertAdjacentHTML("beforeend", `<div class="lower"><p>${o.verse}</p><span>${o.ref}</span></div>`);
    if (o.caption) document.body.insertAdjacentHTML("beforeend", `<div class="caption" style="right:40px;bottom:26px">${o.caption}</div>`);
    if (o.cursor) document.body.insertAdjacentHTML("beforeend", `<svg id="fcur" viewBox="0 0 24 24"><path d="M4 2l15 9.5-6.6 1.4L16 20l-2.8 1.3-3.6-7.2L4 18z" fill="#fff" stroke="#041632" stroke-width="1.6" stroke-linejoin="round"/></svg>`);
    if (o.label) document.body.insertAdjacentHTML("beforeend", `<div id="flab">${o.label}</div>`);
    const nums = [], bars = [];
    if (o.countup) {
      document.querySelectorAll("p.font-serif.text-4xl").forEach((p) => { const n = parseInt(p.textContent); if (!isNaN(n)) { nums.push([p, n]); p.textContent = "0"; } });
      document.querySelectorAll(".card .h-1 > div, span.rounded-t").forEach((b) => { const prop = b.matches("span") ? "height" : "width"; bars.push([b, prop, b.style[prop]]); b.style[prop] = "0%"; });
    }
    window.__cur = (x, y) => (document.getElementById("fcur").style.transform = `translate(${x - 6}px,${y - 4}px)`);
    window.__rip = (x, y) => { const r = document.createElement("div"); r.className = "frip"; r.style.left = x + "px"; r.style.top = y + "px"; document.body.appendChild(r); setTimeout(() => r.remove(), 700); };
    window.__go = () => {
      const l = document.getElementById("flab"); if (l) setTimeout(() => (l.style.transform = "none"), 120);
      const t0 = performance.now();
      const tick = (now) => { const k = Math.min(1, (now - t0) / 1100), e = 1 - Math.pow(1 - k, 3);
        nums.forEach(([p, n]) => (p.textContent = Math.round(n * e))); if (k < 1) requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
      bars.forEach(([b, prop, v], i) => { b.style.transition = `${prop} .7s cubic-bezier(.2,.8,.2,1) ${i * 0.06}s`; requestAnimationFrame(() => (b.style[prop] = v)); });
    };
  });
}})(${JSON.stringify(o)})`;
