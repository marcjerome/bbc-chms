// Runs in the "camera" project: Chrome's fake webcam plays a video of the sticker FLOCK-CAMERAQR.
import { test, expect } from "./helpers.js";

test("the kiosk camera reads a QR sticker by itself", async ({ page }) => {
  await page.goto("/checkin/kiosk/");
  await expect(page.locator("#camera-msg")).toBeHidden();
  // Nobody types anything: the camera finds the code. The real time decides whether a service is on,
  // so either answer proves the sticker was read and matched to the right person.
  await expect(page.locator("#result")).toContainText("Camila Camera", { timeout: 15_000 });
});

test("the camera menu lists the camera and can mirror the picture", async ({ page }) => {
  await page.goto("/checkin/kiosk/");
  await page.getByRole("button", { name: "Camera", exact: true }).click();
  await expect(page.locator("#camera-list button")).not.toHaveCount(0);
  const video = page.locator("#video");
  await page.uncheck("#mirror");
  await expect(video).not.toHaveAttribute("style", /scaleX\(-1\)/);
  await page.check("#mirror");
  await expect(video).toHaveAttribute("style", /scaleX\(-1\)/);
});
