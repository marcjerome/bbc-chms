// Stills for the v3 film: the real printed sticker for Sis. Marites Agbayani (member 2), and the fake
// webcam video of that sticker being held up at the door.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
const B = "http://127.0.0.1:8003", STAGE = "/home/marcjerome/bbc-chms/video/stage", OUT = import.meta.dirname;
const FF = "/home/marcjerome/YAHSHUA/numbers-walkthroughs/recast-rig/bin/ffmpeg";
const browser = await chromium.launch();
const page = await browser.newPage({ deviceScaleFactor: 3 });
await page.goto(`${B}/login/`); await page.fill("#id_username", "pastor"); await page.fill("#id_password", "flock");
await page.click("button:has-text('Sign in')"); await page.waitForURL(`${B}/`);
await page.goto(`${B}/checkin/stickers/?member=2`);
await page.addStyleTag({ content: ".sticker{border:0!important;box-shadow:none!important}" });
await page.locator(".sticker").first().screenshot({ path: `${STAGE}/sticker-marites.png`, omitBackground: true });
await browser.close();
// Fake webcam: 0-6 s an empty view of the pews, the sticker comes up at 6 s and is held (with a little hand
// shake) until 14 s, then leaves; loops every 16 s.
const y = "if(lt(t,6),H,if(lt(t,6.7),H-(t-6)/0.7*(H-(H-h)/2+6),if(lt(t,14),(H-h)/2+6+4*sin(t*2.3),(H-h)/2+6+(t-14)/0.6*H)))";
execFileSync(FF, ["-v", "error", "-y", "-loop", "1", "-i", `${STAGE}/pews.jpg`, "-loop", "1", "-i", `${STAGE}/sticker-marites.png`,
  "-filter_complex", `[0]scale=640:480:force_original_aspect_ratio=increase,crop=640:480,boxblur=8,eq=brightness=-0.05[b];` +
  `[1]scale=470:-1,rotate=-0.035:c=none:ow=rotw(-0.035):oh=roth(-0.035)[s];[b][s]overlay=x='(W-w)/2+3*sin(t*1.7)':y='${y}'`,
  "-t", "16", "-r", "15", "-pix_fmt", "yuv420p", `${OUT}/door-camera.y4m`]);
console.log("ok");
