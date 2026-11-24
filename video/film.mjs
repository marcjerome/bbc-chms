// Records each scene of the Flock pitch video from the film server (port 8003) into raw/<scene>.webm
import { chromium } from "playwright";
import { renameSync, readdirSync, rmSync, mkdirSync } from "node:fs";
const B = "http://127.0.0.1:8003", OUT = "/home/marcjerome/bbc-chms/video/raw";
const SIZE = { width: 1920, height: 1080 }, VIEW = { width: 1536, height: 864 };
const NEXT_SUNDAY = "2026-11-29", SERVICE = 13, NO_CONSENT = 67, PROFILE = 11;
const only = process.argv[2];
const wait = (s) => new Promise((r) => setTimeout(r, s * 1000));

// Overlays (zoom for app pages, optional caption / lower-third verse) injected on every page load.
const overlay = (o = {}) => `(${(o) => {
  addEventListener("DOMContentLoaded", () => {
    const s = document.createElement("style"); s.textContent = ".fixed.bottom-4{display:none}"; document.head.appendChild(s);
    if (window !== top) return;
    const css = document.createElement("link"); css.rel = "stylesheet"; css.href = "/static/film/overlay.css";
    document.head.appendChild(css);
    if (o.verse) document.body.insertAdjacentHTML("beforeend", `<div class="lower"><p>${o.verse}</p><span>${o.ref}</span></div>`);
    if (o.caption) document.body.insertAdjacentHTML("beforeend", `<div class="caption" style="right:40px;bottom:26px">${o.caption}</div>`);
  });
}})(${JSON.stringify(o)})`;

const browser = await chromium.launch();
const login = await browser.newContext();
const lp = await login.newPage();
await lp.goto(`${B}/login/`); await lp.fill("#id_username", "pastor"); await lp.fill("#id_password", "flock");
await lp.check("input[name=remember]"); await lp.click("button:has-text('Sign in')"); await lp.waitForURL(`${B}/`);
const state = await login.storageState(); await login.close();

async function scene(name, fn, o) {
  if (only && only !== name) return;
  const dir = `${OUT}/_${name}`; rmSync(dir, { recursive: true, force: true }); mkdirSync(dir, { recursive: true });
  const stage = name === "s1" || name === "s2" || name === "s3" || name === "s8";
  const ctx = await browser.newContext({ storageState: state, viewport: stage ? SIZE : VIEW,
    deviceScaleFactor: stage ? 1 : 1.25, recordVideo: { dir, size: SIZE } });
  await ctx.addInitScript(overlay(o));
  const page = await ctx.newPage();
  await fn(page);
  await ctx.close();
  renameSync(`${dir}/${readdirSync(dir)[0]}`, `${OUT}/${name}.webm`); rmSync(dir, { recursive: true });
  console.log("recorded", name);
}
const hideChrome = async (frame) => frame.addStyleTag({ content: "aside,header{display:none!important} main{width:100%}" });

await scene("s1", async (p) => { await p.goto(`${B}/static/film/s1.html`); await wait(7); });
await scene("s2", async (p) => { await p.goto(`${B}/static/film/s2.html`); await wait(9.5); });
await scene("s3", async (p) => { await p.goto(`${B}/static/film/s3.html`); await wait(5); });

await scene("s4", async (p) => {
  await p.goto(`${B}/static/film/split.html?s=${SERVICE}`); await wait(1.5);
  const sim = p.frame({ url: /simulator/ }), chk = p.frame({ url: /attendance\/services/ });
  await hideChrome(sim); await hideChrome(chk); await wait(1);
  for (const [idx, t] of [[3, "09:16"], [8, "09:18"], [15, "09:19"]]) {
    await sim.selectOption("#identity", { index: idx });
    await sim.fill("#when", `${NEXT_SUNDAY}T${t}`); await wait(0.6);
    await sim.click("button[value=finger]"); await wait(0.9);
    await chk.evaluate((u) => htmx.ajax("GET", u, { swap: "none" }), `/attendance/services/${SERVICE}/live/`);
    await wait(2.6);
  }
  await wait(1.5);
});

await scene("s5", async (p) => { await p.goto(`${B}/biometrics/`); await wait(9.5); },
  { caption: "Demonstration · terminal simulator" });

await scene("s6", async (p) => {
  await p.goto(`${B}/`); await wait(2.9);
  await p.goto(`${B}/static/film/phone.html?u=${encodeURIComponent(`/attendance/services/${SERVICE}/?q=Ra`)}&t=${encodeURIComponent("Ushers check in<br>with a tap.")}`); await wait(3);
  await p.goto(`${B}/members/${PROFILE}/`); await wait(2.9);
  await p.goto(`${B}/members/birthdays/`); await wait(3.8);
});

await scene("s7", async (p) => { await p.goto(`${B}/members/visitation/`); await wait(6); },
  { verse: "“I was sick, and ye visited me.”", ref: "Matthew 25:36" });
await scene("s8", async (p) => { await p.goto(`${B}/static/film/s8.html`); await wait(10); });
await browser.close();
