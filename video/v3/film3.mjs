// v3 recorder: films every clip of a plan (plan-calm.json / plan-hype.json) against the film server (8003).
// Usage: node film3.mjs calm|blend|hype [clip]
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { renameSync, readdirSync, rmSync, mkdirSync, writeFileSync, readFileSync } from "node:fs";
const VERSION = process.argv[2], only = process.argv[3];
const P = JSON.parse(readFileSync(`${import.meta.dirname}/plan-${VERSION}.json`));
const WORDS = JSON.parse(readFileSync(`${import.meta.dirname}/audio/words.json`));
const B = "http://127.0.0.1:8003", OUT = `${import.meta.dirname}/raw-${VERSION}`;
const SIZE = { width: 1920, height: 1080 }, VIEW = { width: 1536, height: 864 };
const BEAT = P.beat, NEXT_SUNDAY = "2026-11-29", SERVICE = 13;
const DUR = Object.fromEntries(P.clips.map((c) => [c.name, c.dur]));
const wait = (s) => new Promise((r) => setTimeout(r, s * 1000));
const word = (key, w) => WORDS[`${VERSION}-${key}`].find((x) => x[0].replace(/[^\w']/g, "").toLowerCase() === w)[1];
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
const camBrowser = await chromium.launch({ args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
  `--use-file-for-fake-video-capture=${import.meta.dirname}/door-camera.y4m`] });
const login = await browser.newContext();
const lp = await login.newPage();
await lp.goto(`${B}/login/`); await lp.fill("#id_username", "pastor"); await lp.fill("#id_password", "flock");
await lp.check("input[name=remember]"); await lp.click("button:has-text('Sign in')"); await lp.waitForURL(`${B}/`);
const state = await login.storageState(); await login.close();

async function clip(name, fn, o = {}, stage = false, br = browser) {
  if (only && name !== only) return;
  const dir = `${OUT}/_${name}`; rmSync(dir, { recursive: true, force: true }); mkdirSync(dir, { recursive: true });
  const ctx = await br.newContext({ storageState: state, viewport: stage ? SIZE : VIEW, deviceScaleFactor: stage ? 1 : 1.25, recordVideo: { dir, size: SIZE } });
  await ctx.addInitScript(overlay(o));
  await ctx.addInitScript(() => { try { localStorage.setItem("flock-kiosk-mirror", "0"); } catch (e) {} });
  const page = await ctx.newPage(); const t0 = Date.now();
  let markAt = null, event = null;
  const mark = async () => { markAt = Date.now(); await page.evaluate(() => window.__go && window.__go()).catch(() => {}); };
  const at = async (b) => { const d = markAt + b * BEAT * 1000 - Date.now(); if (d > 0) await wait(d / 1000); };
  const ev = () => { event = (Date.now() - t0) / 1000; };
  await fn(page, mark, at, ev);
  const end = (markAt - t0) / 1000 + DUR[name] + 1.5 - (Date.now() - t0) / 1000;
  if (end > 0) await wait(end);
  if (event) { const extra = event + 12 - (Date.now() - t0) / 1000; if (extra > 0) await wait(extra); }
  await ctx.close();
  renameSync(`${dir}/${readdirSync(dir)[0]}`, `${OUT}/${name}.webm`); rmSync(dir, { recursive: true });
  writeFileSync(`${OUT}/${name}.json`, JSON.stringify({ offset: (markAt - t0) / 1000, event }));
  console.log("recorded", name, ((markAt - t0) / 1000).toFixed(2), event ? `event ${event.toFixed(2)}` : "");
}
async function tap(p, loc, at, beat, { click = true, lead = 1.4 } = {}) {
  const b = await loc.boundingBox(); const x = b.x + b.width / 2, y = b.y + b.height / 2;
  await at(beat - lead); await p.evaluate(([x, y]) => window.__cur(x, y), [x, y]);
  await at(beat); await p.evaluate(([x, y]) => window.__rip(x, y), [x, y]);
  if (click) await loc.click({ force: true });
}
const hideChrome = (f) => f.addStyleTag({ content: "aside,header{display:none!important} main{width:100%}" });
const stageClip = (name, url) => clip(name, async (p, mark) => { await p.goto(`${B}/static/film/${url}`); await mark(); }, {}, true);
const fast = VERSION === "hype", brisk = VERSION !== "calm";  // brisk: hype and blend

await stageClip("s1", "s1.html");
await stageClip("s2", "s2.html");
await stageClip("s3", "s3.html");
await stageClip("bible", "bible.html");

// The door: the kiosk's (fake) camera sees Marites's sticker; she is welcomed and appears on the usher's list.
await clip("door", async (p, mark, at, ev) => {
  execFileSync("/home/marcjerome/bbc-chms/.venv/bin/python", ["manage.py", "shell", "-c",
    `from attendance.models import Attendance; Attendance.objects.filter(member_id=2, service_id=${SERVICE}).delete()`],
    { cwd: "/home/marcjerome/bbc-chms", env: { ...process.env, DJANGO_SETTINGS_MODULE: "config.settings.film" }, stdio: "ignore" });
  await p.goto(`${B}/static/film/door.html?s=${SERVICE}`);
  const kiosk = p.frame({ url: /checkin\/kiosk/ }), chk = p.frame({ url: /attendance\/services/ });
  await kiosk.waitForLoadState(); await chk.waitForLoadState();
  await hideChrome(chk);
  await kiosk.addStyleTag({ content: "details{display:none!important}" });
  await kiosk.evaluate((v) => { document.getElementById("when").value = v; }, `${NEXT_SUNDAY}T09:16`);
  await kiosk.waitForFunction(() => document.getElementById("video").currentTime > 0, null, { timeout: 15000 });
  const streamAt = Date.now(); await mark();
  // the sticker enters the camera picture 6 s into the stream: move in on the kiosk just before
  await wait(Math.max(0, 2.6 - (Date.now() - streamAt) / 1000));
  await p.evaluate(() => window.cam("l", "#video", 1.32));
  await kiosk.waitForFunction(() => document.getElementById("result").textContent.includes("Welcome"), null, { timeout: 20000, polling: 30 });
  ev();
  await wait(0.3); await chk.evaluate((u) => htmx.ajax("GET", u, { swap: "none" }), `/attendance/services/${SERVICE}/live/`);
  await wait(fast ? 1.4 : brisk ? 1.8 : 2.2); await p.evaluate(() => window.cam("r", "#checked-in", 1.45, 80));
  await wait(0.9); await chk.evaluate(() => {
    const paint = () => {  // re-applied: the page's 5 s live refresh redraws the list
      const row = [...document.querySelectorAll("#checked-in li")].find((e) => e.textContent.includes("Marites"));
      if (row && !row.dataset.lit) { row.dataset.lit = 1; row.style.transition = "background .4s"; row.style.background = "#f6e7c4"; row.style.borderRadius = "10px"; row.style.boxShadow = "0 0 0 3px #e9c176"; }
    };
    paint(); setInterval(paint, 100);
  });
}, {}, false, camBrowser);

// Check-in modes: the real Modes page; the cursor ticks Fingerprint and Face as the narrator names them (not saved).
{
  const beatOf = (w) => (P.lead + word("modes", w)) / BEAT;
  await clip("modes", async (p, mark, at) => {
    await p.goto(`${B}/checkin/modes/`); await wait(0.4); await mark();
    if (fast) await tap(p, p.locator("#id_qr_enabled"), at, beatOf("qr"), { click: false, lead: 0.9 });
    await tap(p, p.locator("#id_fingerprint_enabled"), at, beatOf("fingerprint") + 0.6, { lead: fast ? 0.9 : brisk ? 1.0 : 1.2 });
    await tap(p, p.locator("#id_face_enabled"), at, beatOf("face") + 0.3, { lead: fast ? 0.7 : brisk ? 0.85 : 1.0 });
  }, { cursor: true, label: "Your choice: QR · fingerprint · face" });
}

// "No lines. No logbooks." slam in exactly as the narrator says each phrase.
{
  const lead = VERSION === "blend" ? 0.5 : BEAT, t1 = lead + word("lines", "no"), t2 = lead + WORDS[`${VERSION}-lines`][2][1];
  await clip("lines", async (p, mark) => {
    await p.goto(`${B}/static/film/kinetic.html?w=${encodeURIComponent("No lines.|No logbooks.")}&at=${t1.toFixed(2)},${t2.toFixed(2)}&ms=1000`);
    await mark(); await p.evaluate(() => start());
  }, {}, true);
}

await clip("dash", async (p, mark) => { await p.goto(`${B}/`); await wait(0.4); await mark(); }, { countup: true, label: "The state of the flock" });
await clip("visitor", async (p, mark, at) => {
  await p.goto(`${B}/attendance/services/${SERVICE}/`); await p.mouse.wheel(0, 120); await wait(0.5); await mark();
  await tap(p, p.locator("button:has-text('Add first-time visitor')"), at, 0.8, { lead: 0.8 });
  await at(1.6); await p.locator("input[name=first_name]").pressSequentially("Bea", { delay: fast ? 45 : brisk ? 55 : 70 });
  await p.locator("input[name=last_name]").pressSequentially("Santos", { delay: fast ? 40 : brisk ? 50 : 60 });
}, { cursor: true, label: "Welcoming first-time visitors" });
await clip("roll", async (p, mark, at) => {
  await p.goto(`${B}/members/`); await wait(0.4); await mark();
  await at(0.5); await p.evaluate(() => window.__cur(700, 380)); await at(1.5); await p.mouse.wheel(0, 260);
}, { cursor: true, label: "The church roll" });
await clip("bday", async (p, mark) => { await p.goto(`${B}/members/birthdays/`); await wait(0.4); await mark(); }, { label: "Birthdays · every Lord's Day" });
await clip("visit", async (p, mark, at) => {
  await p.goto(`${B}/members/visitation/`); await wait(0.4); await mark();
  await tap(p, p.locator("a[href^='tel:']").nth(6), at, 3, { click: false, lead: 1.2 });
}, { cursor: true, verse: "“I was sick, and ye visited me.”", ref: "Matthew 25:36" });
await stageClip("s8", "s8.html");
await browser.close(); await camBrowser.close();
