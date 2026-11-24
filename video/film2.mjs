// v2 "hype" recorder: every action is timed in beats from a per-clip mark, so cuts and effects land on the music.
import { chromium } from "playwright";
import { renameSync, readdirSync, rmSync, mkdirSync, writeFileSync } from "node:fs";
const B = "http://127.0.0.1:8003", OUT = "/home/marcjerome/bbc-chms/video/raw2";
const SIZE = { width: 1920, height: 1080 }, VIEW = { width: 1536, height: 864 };
const BEAT = 0.418, NEXT_SUNDAY = "2026-11-29", SERVICE = 13, PROFILE = 11;
const only = process.argv[2];
const wait = (s) => new Promise((r) => setTimeout(r, s * 1000));
mkdirSync(OUT, { recursive: true });

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

const browser = await chromium.launch();
const login = await browser.newContext();
const lp = await login.newPage();
await lp.goto(`${B}/login/`); await lp.fill("#id_username", "pastor"); await lp.fill("#id_password", "flock");
await lp.check("input[name=remember]"); await lp.click("button:has-text('Sign in')"); await lp.waitForURL(`${B}/`);
const state = await login.storageState(); await login.close();

async function clip(name, beats, fn, o = {}, stage = false) {
  if (only && !name.startsWith(only)) return;
  const dir = `${OUT}/_${name}`; rmSync(dir, { recursive: true, force: true }); mkdirSync(dir, { recursive: true });
  const ctx = await browser.newContext({ storageState: state, viewport: stage ? SIZE : VIEW, deviceScaleFactor: stage ? 1 : 1.25, recordVideo: { dir, size: SIZE } });
  await ctx.addInitScript(overlay(o));
  const page = await ctx.newPage(); const t0 = Date.now();
  let markAt = null;
  const mark = async () => { markAt = Date.now(); await page.evaluate(() => window.__go && window.__go()).catch(() => {}); };
  const at = async (b) => { const d = markAt + b * BEAT * 1000 - Date.now(); if (d > 0) await wait(d / 1000); };
  await fn(page, mark, at);
  await at(beats + 1);
  await ctx.close();
  renameSync(`${dir}/${readdirSync(dir)[0]}`, `${OUT}/${name}.webm`); rmSync(dir, { recursive: true });
  writeFileSync(`${OUT}/${name}.json`, JSON.stringify({ offset: (markAt - t0) / 1000 }));
  console.log("recorded", name, ((markAt - t0) / 1000).toFixed(2));
}
async function tap(p, loc, at, beat, { click = true, lead = 1.4 } = {}) {
  const b = await loc.boundingBox(); const x = b.x + b.width / 2, y = b.y + b.height / 2;
  await at(beat - lead); await p.evaluate(([x, y]) => window.__cur(x, y), [x, y]);
  await at(beat); await p.evaluate(([x, y]) => window.__rip(x, y), [x, y]);
  if (click) await loc.click({ force: true });
}
const hideChrome = (f) => f.addStyleTag({ content: "aside,header{display:none!important} main{width:100%}" });
const stageClip = (name, beats, url, extra) => clip(name, beats, async (p, mark) => { await p.goto(`${B}/static/film/${url}`); await mark(); if (extra) await p.evaluate(extra); }, {}, true);

await stageClip("s1", 12, "s1.html");
await stageClip("s2", 20, "s2.html");
await stageClip("s3", 8, "s3.html");

await clip("s4a", 13, async (p, mark, at) => {
  await p.goto(`${B}/static/film/split.html?s=${SERVICE}`); await wait(1.2);
  const sim = p.frame({ url: /simulator/ }), chk = p.frame({ url: /attendance\/services/ });
  await hideChrome(sim); await hideChrome(chk);
  const prep = async (idx, t) => { await sim.selectOption("#identity", { index: idx }); await sim.fill("#when", `${NEXT_SUNDAY}T${t}`); };
  const live = () => chk.evaluate((u) => htmx.ajax("GET", u, { swap: "none" }), `/attendance/services/${SERVICE}/live/`);
  const cam = (...a) => p.evaluate((a) => window.cam(...a), a);
  await prep(3, "09:16"); await wait(0.6); await mark();
  const finger = p.frameLocator("#l").locator("button[value=finger]");
  await tap(p, finger, at, 3.5, { lead: 2.2 });               // "a simple touch"
  await at(4.3); await cam("l", "#screen", 1.75);              // "greeted by name": hold on the terminal
  await at(8.6); await live();
  await at(9.2); await cam("r", "#checked-in", 1.6, 80);       // "and checked in": her row on the usher's list
  await at(10.1); await chk.evaluate(() => {
    const row = [...document.querySelectorAll("#checked-in *")].find((e) => e.textContent.includes("Marites") && e.offsetHeight > 28 && e.offsetHeight < 70 && e.children.length > 1);
    if (row) { row.style.transition = "background .4s"; row.style.background = "#f6e7c4"; row.style.borderRadius = "10px"; row.style.boxShadow = "0 0 0 3px #e9c176"; }
  });
}, { cursor: true, caption: "" });
await clip("s4b", 6, async (p, mark) => { await p.goto(`${B}/static/film/kinetic.html?w=${encodeURIComponent("No lines.|No logbooks.")}&at=1,3`); await mark(); await p.evaluate(() => start()); }, {}, true);
await clip("s4c", 9, async (p, mark, at) => {
  await p.goto(`${B}/static/film/phone.html?u=${encodeURIComponent(`/attendance/services/${SERVICE}/?q=Co`)}&t=${encodeURIComponent("Ushers check in<br>with a tap.")}`);
  await wait(2.2); await mark();
  await tap(p, p.frameLocator("#f").locator("button:has-text('Check in')").first(), at, 3.5);
}, { cursor: true });

await clip("s5", 20, async (p, mark) => { await p.goto(`${B}/biometrics/`); await wait(0.4); await mark(); },
  { countup: true, caption: "Demonstration · terminal simulator", label: "Live at the door" });

await clip("s6a", 7, async (p, mark) => { await p.goto(`${B}/`); await wait(0.4); await mark(); }, { countup: true, label: "The state of the flock" });
await clip("s6b", 5, async (p, mark, at) => {
  await p.goto(`${B}/attendance/services/${SERVICE}/`); await p.mouse.wheel(0, 120); await wait(0.5); await mark();
  await tap(p, p.locator("button:has-text('Add first-time visitor')"), at, 0.8, { lead: 0.8 });
  await at(1.6); await p.locator("input[name=first_name]").pressSequentially("Bea", { delay: 70 });
  await p.locator("input[name=last_name]").pressSequentially("Santos", { delay: 60 });
}, { cursor: true, label: "Welcoming first-time visitors" });
await clip("s6c", 7, async (p, mark, at) => {
  await p.goto(`${B}/members/`); await wait(0.4); await mark();
  await at(1); await p.evaluate(() => window.__cur(700, 380)); await at(3); await p.mouse.wheel(0, 260);
}, { cursor: true, label: "The church roll" });
await clip("s6d", 9, async (p, mark) => { await p.goto(`${B}/members/birthdays/`); await wait(0.4); await mark(); }, { label: "Birthdays · every Lord's Day" });

await clip("s7a", 4, async (p, mark) => { await p.goto(`${B}/static/film/kinetic.html?w=${encodeURIComponent("Who did we miss?")}&at=0`); await mark(); await p.evaluate(() => start()); }, {}, true);
await clip("s7b", 8, async (p, mark, at) => {
  await p.goto(`${B}/members/visitation/`); await wait(0.4); await mark();
  await tap(p, p.locator("a[href^='tel:']").nth(6), at, 3, { click: false, lead: 1.2 });
}, { cursor: true, verse: "“I was sick, and ye visited me.”", ref: "Matthew 25:36" });
await stageClip("s8", 20, "s8.html");
await browser.close();
