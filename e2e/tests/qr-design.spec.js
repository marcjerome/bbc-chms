// The branded QR (sheep logo + church name) must stay as easy to scan as a plain code.
// Each sticker is decoded with the kiosk's own reader (jsQR) at the sizes and blur a door camera sees.
import { test, expect, openMember } from "./helpers.js";

/** Decode one rendered <svg> at several sizes and blur levels. Returns e.g. {"140px blur 1": "FLOCK-…"}. */
async function decodeAtSizes(page, svgLocator, cases) {
  await page.addScriptTag({ url: "/static/js/vendor/jsQR.js" });
  return svgLocator.evaluate(async (svg, cases) => {
    const img = new Image();
    img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(new XMLSerializer().serializeToString(svg))));
    await img.decode();
    const results = {};
    for (const [px, blur] of cases) {
      const c = Object.assign(document.createElement("canvas"), { width: px * 1.4 + 60, height: px * 1.4 + 60 });
      const g = c.getContext("2d");
      g.fillStyle = "#fff"; g.fillRect(0, 0, c.width, c.height);
      g.filter = blur ? `blur(${blur}px)` : "none";
      g.drawImage(img, 30, 30, px, (px * img.height) / img.width);
      const d = g.getImageData(0, 0, c.width, c.height);
      results[`${px}px blur ${blur}`] = window.jsQR(d.data, d.width, d.height, { inversionAttempts: "dontInvert" })?.data ?? null;
    }
    return results;
  }, cases);
}

// A sticker held 20–40 cm from a tablet camera appears roughly 140–400 px wide; small and blurry is the hard case.
const MUST_SCAN = [[100, 0], [140, 0], [140, 1], [220, 0], [220, 1], [220, 2], [400, 0], [400, 1], [400, 2]];

test("a printed sticker scans at every distance and focus a door camera sees", async ({ page }) => {
  await openMember(page, "Bella Kiosk");
  await page.getByRole("link", { name: "Print sticker" }).click();
  const qr = page.locator(".sticker > svg");
  await expect(qr).toHaveAttribute("aria-label", "QR code FLOCK-KIOSKBBB");
  const results = await decodeAtSizes(page, qr, MUST_SCAN);
  for (const [setting, text] of Object.entries(results)) expect(text, setting).toBe("FLOCK-KIOSKBBB");
});

test("the sticker shows the sheep and the church name", async ({ page }) => {
  await openMember(page, "Bella Kiosk");
  await page.getByRole("link", { name: "Print sticker" }).click();
  const qr = page.locator(".sticker > svg");
  await expect(qr.locator("text")).toHaveText("BBC BARANI");
  await expect(qr.locator("svg[viewBox='0 0 100 100']")).toHaveCount(1); // the sheep logo
});

test("every sticker on a full sheet scans", async ({ page }) => {
  await page.goto("/checkin/stickers/?show=all");
  const codes = page.locator(".sticker > svg");
  const count = await codes.count();
  expect(count).toBeGreaterThan(5);
  for (let i = 0; i < count; i++) {
    const expected = (await codes.nth(i).getAttribute("aria-label")).replace("QR code ", "");
    const results = await decodeAtSizes(page, codes.nth(i), [[140, 1], [300, 0]]);
    for (const [setting, text] of Object.entries(results)) expect(text, `${expected} at ${setting}`).toBe(expected);
  }
});

test("the profile's QR image scans too", async ({ page }) => {
  await openMember(page, "Dina Kiosk");
  const src = await page.getByRole("img", { name: /QR code for/ }).getAttribute("src");
  const svgText = await (await page.request.get(src)).text();
  await page.setContent(svgText);
  const results = await decodeAtSizes(page, page.locator("body > svg"), [[200, 0], [200, 1]]);
  for (const text of Object.values(results)) expect(text).toBe("FLOCK-KIOSKDDD");
});
