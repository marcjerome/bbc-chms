// Before the run: reset the E2E server's database to the fixed test data (manage.py seed_e2e).
import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "@playwright/test";

export default async function globalSetup(config) {
  const base = config.projects[0].use.baseURL;
  const cmd = process.env.E2E_RESET_CMD
    || "docker compose -f docker-compose.e2e.yml exec -T web python manage.py seed_e2e";
  execSync(cmd, { cwd: path.resolve(import.meta.dirname, ".."), stdio: "inherit" });
  await makeCameraVideo(path.resolve(import.meta.dirname, ".fixtures"));
  const resp = await fetch(`${base}/login/`).catch(() => null);
  if (!resp || !resp.ok) {
    throw new Error(`E2E server not reachable at ${base}. Start it: docker compose -f docker-compose.e2e.yml up -d --build`);
  }
}

/**
 * Turn the branded sticker (written by seed_e2e) into a Y4M video for Chrome's fake webcam: the sticker
 * on a white page, drawn by a real browser so it looks exactly like the printed one.
 */
async function makeCameraVideo(dir) {
  const svg = fs.readFileSync(path.join(dir, "qr-camera.svg"), "utf8");
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const { w, h, rgba } = await page.evaluate(async (svg) => {
    const img = new Image();
    img.src = "data:image/svg+xml;base64," + btoa(svg);
    await img.decode();
    const c = Object.assign(document.createElement("canvas"), { width: 640, height: 480 });
    const g = c.getContext("2d");
    g.fillStyle = "#f4f1ea"; g.fillRect(0, 0, 640, 480);   // a Bible's paper, not pure white
    const height = 330, width = height * img.width / img.height;
    g.drawImage(img, (640 - width) / 2, (480 - height) / 2, width, height);
    return { w: 640, h: 480, rgba: Array.from(g.getImageData(0, 0, 640, 480).data) };
  }, svg);
  await browser.close();
  // RGB -> YUV 4:2:0 (BT.601 full range, what C420jpeg means)
  const Y = Buffer.alloc(w * h), U = Buffer.alloc(w * h / 4), V = Buffer.alloc(w * h / 4);
  const clamp = (v) => Math.max(0, Math.min(255, Math.round(v)));
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = (y * w + x) * 4, r = rgba[i], gr = rgba[i + 1], b = rgba[i + 2];
    Y[y * w + x] = clamp(0.299 * r + 0.587 * gr + 0.114 * b);
    if (y % 2 === 0 && x % 2 === 0) {
      const j = (y / 2) * (w / 2) + x / 2;
      U[j] = clamp(128 - 0.168736 * r - 0.331264 * gr + 0.5 * b);
      V[j] = clamp(128 + 0.5 * r - 0.418688 * gr - 0.081312 * b);
    }
  }
  const frame = Buffer.concat([Buffer.from("FRAME\n"), Y, U, V]);
  const out = [Buffer.from(`YUV4MPEG2 W${w} H${h} F10:1 Ip A1:1 C420jpeg\n`), ...Array(10).fill(frame)];
  fs.writeFileSync(path.join(dir, "qr-camera.y4m"), Buffer.concat(out));
}
