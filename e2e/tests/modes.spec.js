// Check-in modes: QR (default), Fingerprint, Face. Runs last and in order (project "modes"), because switching a
// mode changes what every other test sees. Puts the defaults back at the end.
import { test, expect, openMember, openCheckinService, authFile } from "./helpers.js";

test.describe.configure({ mode: "serial" });

async function setModes(page, { qr = true, fingerprint = false, face = false } = {}) {
  await page.goto("/checkin/modes/");
  await page.locator("#id_qr_enabled").setChecked(qr);
  await page.locator("#id_fingerprint_enabled").setChecked(fingerprint);
  await page.locator("#id_face_enabled").setChecked(face);
  await page.getByRole("button", { name: "Save modes" }).click();
  await expect(page.getByText("Check-in modes saved")).toBeVisible();
}

test.afterAll(async ({ browser }) => {
  const page = await browser.newPage({ storageState: authFile("admin"), baseURL: test.info().project.use.baseURL });
  await setModes(page);
  await page.close();
});

test("QR is the only mode on by default", async ({ page }) => {
  await page.goto("/checkin/modes/");
  await expect(page.locator("#id_qr_enabled")).toBeChecked();
  await expect(page.locator("#id_fingerprint_enabled")).not.toBeChecked();
  await expect(page.locator("#id_face_enabled")).not.toBeChecked();
  await expect(page.getByRole("link", { name: "Door terminals" })).toHaveCount(0);
  await openMember(page, "Fernando Finger");
  await expect(page.getByRole("button", { name: "Record signed consent" })).toHaveCount(0);
});

test("the face match strictness is validated", async ({ page }) => {
  await page.goto("/checkin/modes/");
  await page.locator("main form").evaluate((f) => { f.noValidate = true; });
  await page.fill("#id_face_match_threshold", "0.9");
  await page.getByRole("button", { name: "Save modes" }).click();
  await expect(page.getByText("Use a number from 0.30 (strict) to 0.70 (loose)")).toBeVisible();
});

test("fingerprint: consent, terminal registration, a scan shows on the usher's list", async ({ page }) => {
  await setModes(page, { qr: true, fingerprint: true });
  await page.goto("/checkin/");
  await expect(page.getByText("Fingerprint · on")).toBeVisible();
  await openMember(page, "Fernando Finger");
  await page.getByPlaceholder("Form no. / where the signed copy is filed").fill("E2E-001");
  await page.getByRole("button", { name: "Record signed consent" }).click();
  await expect(page.getByText("Consent on file")).toBeVisible();
  await expect(page.getByRole("link", { name: "Enroll face" })).toHaveCount(0); // Face mode is off
  await page.getByRole("button", { name: "Register on terminals" }).click();
  await expect(page.getByText(/Device user/)).toBeVisible();

  await page.getByRole("link", { name: "Door terminals" }).click();
  await page.getByRole("link", { name: "Open device simulator" }).click();
  await expect(page.getByRole("button", { name: "Scan face" })).toHaveCount(0);
  await page.selectOption("#identity", await page.locator("#identity option", { hasText: "Fernando Finger" }).getAttribute("value"));
  await page.fill("#when", "2026-12-13T09:20");
  await page.getByRole("button", { name: "Scan finger" }).click();
  await expect(page.locator("#screen")).toContainText("Thank you, Bro. Fernando Finger!");

  await openCheckinService(page);
  const row = page.locator("#checked-in li", { hasText: "Fernando Finger" });
  await expect(row).toBeVisible();
  await expect(row.getByText("fingerprint")).toBeVisible();
});

test("face: enroll page and kiosk load the face models from the church server", async ({ page }) => {
  await setModes(page, { qr: true, fingerprint: true, face: true });
  const outside = [];
  const origin = new URL(test.info().project.use.baseURL).origin;
  page.on("request", (r) => { if (!r.url().startsWith(origin) && !r.url().startsWith("data:")) outside.push(r.url()); });
  await openMember(page, "Fernando Finger");
  await page.getByRole("link", { name: "Enroll face" }).click();
  await expect(page.getByRole("heading", { name: "Enroll face" })).toBeVisible();
  // The desktop test browser has no camera: the page says so instead of breaking.
  await expect(page.locator("#camera-msg")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save face" })).toBeDisabled();

  await page.goto("/checkin/kiosk/");
  await expect(page.getByText("Hold up your Bible's QR code, or look at the camera")).toBeVisible();
  await expect(page.locator("#face-status")).toContainText("Face recognition on", { timeout: 30_000 });
  expect(outside, "requests outside the church server").toEqual([]);
});

test("a kiosk station can use QR only", async ({ page }) => {
  await page.goto("/checkin/kiosk/?modes=qr");
  await expect(page.getByText("Hold your Bible's QR code up to the camera")).toBeVisible();
  await expect(page.locator("#face-status")).toHaveCount(0);
});

test("QR off: no stickers or code box, face kiosk still works", async ({ page }) => {
  await setModes(page, { qr: false, face: true });
  await page.goto("/checkin/kiosk/");
  await expect(page.getByText("Look at the camera to check in")).toBeVisible();
  await expect(page.locator("#code")).toBeHidden();
  expect((await page.request.get("/checkin/stickers/")).status()).toBe(404);
  await openMember(page, "Fernando Finger");
  await expect(page.getByRole("button", { name: "Give QR code" })).toHaveCount(0);
});

test("withdrawing consent removes the person from face and terminals", async ({ page }) => {
  await openMember(page, "Fernando Finger");
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "Withdraw consent" }).click();
  await expect(page.getByText(/^Consent withdrawn \w{3} \d+, \d{4}/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Enroll face" })).toHaveCount(0);
});

test("every mode off: only ushers check people in", async ({ page }) => {
  await setModes(page, { qr: false });
  await page.goto("/checkin/");
  await expect(page.getByText("Every check-in mode is off")).toBeVisible();
  expect((await page.request.get("/checkin/kiosk/")).status()).toBe(404);
});
