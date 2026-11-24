import { test, expect, KIOSK_SUNDAY, openMember, openCheckinService } from "./helpers.js";

/** Open the kiosk; as staff who manage QR codes, pretend it's 9:15 on the kiosk test Sunday. */
async function openKiosk(page, { demoTime = `${KIOSK_SUNDAY}T09:15` } = {}) {
  await page.goto("/checkin/kiosk/?station=E2E door");
  if (demoTime) {
    await page.getByText("Demo: pretend it's another time").click();
    await page.fill("#when", demoTime);
  }
}

async function typeCode(page, code) {
  await page.fill("#code", code);
  await page.press("#code", "Enter");
}

const overlay = (page) => page.locator("#result");

test.describe("QR codes and stickers", () => {
  test("give a QR code, see it on the profile and print the sticker", async ({ page }) => {
    await openMember(page, "Victor Visita");
    await page.getByRole("button", { name: "Give QR code" }).click();
    await expect(page.getByText("Victor Visita has a QR code.")).toBeVisible();
    const code = await page.locator("p.font-mono").innerText();
    expect(code).toMatch(/^FLOCK-[2-9A-HJKMNP-Z]{8}$/);
    const img = page.getByRole("img", { name: /QR code for Victor Visita/ });
    await expect(img).toBeVisible();
    expect(await img.evaluate((i) => i.naturalWidth)).toBeGreaterThan(0);
    await page.getByRole("link", { name: "Print sticker" }).click();
    await expect(page.locator(".sticker")).toHaveCount(1);
    await expect(page.locator(".sticker")).toContainText(code);
    await expect(page.locator(".sticker > svg")).toBeVisible();
  });

  test("a lost sticker gets a new code and the old one stops working", async ({ page }) => {
    await openMember(page, "Rafael Reissue");
    await expect(page.getByText("FLOCK-REISSUEX")).toBeVisible();
    page.once("dialog", (d) => d.accept());
    await page.getByRole("button", { name: "Lost sticker? New code" }).click();
    await expect(page.getByText(/The old sticker no longer works/)).toBeVisible();
    await expect(page.getByText("FLOCK-REISSUEX")).toHaveCount(0);
    await expect(page.getByText("Not printed yet")).toBeVisible();
    await openKiosk(page);
    await typeCode(page, "FLOCK-REISSUEX");
    await expect(overlay(page)).toContainText("We don't know this code");
  });

  test("cancelling the new-code question changes nothing", async ({ page }) => {
    await openMember(page, "Dina Kiosk");
    page.once("dialog", (d) => d.dismiss());
    await page.getByRole("button", { name: "Lost sticker? New code" }).click();
    await expect(page.getByText("FLOCK-KIOSKDDD")).toBeVisible();
  });

  test("give codes to everyone without one from the sticker page", async ({ page }) => {
    await page.goto("/checkin/stickers/");
    await page.selectOption("#household", { label: "Santos Family" });
    await page.getByRole("button", { name: "Show" }).click();
    await expect(page.getByText(/have no QR code yet|has no QR code yet/)).toBeVisible();
    await page.getByRole("button", { name: "Give them QR codes" }).click();
    await expect(page.getByText(/Gave QR codes to \d+/)).toBeVisible();
    await expect(page.getByText(/no QR code yet/)).toHaveCount(0);
    await expect(page.locator(".sticker", { hasText: "Pedro" })).toBeVisible();
  });
});

test.describe("kiosk", () => {
  test("typed code (or USB scanner) checks the person in", async ({ page }) => {
    await openKiosk(page);
    await typeCode(page, "FLOCK-KIOSKAAA");
    await expect(overlay(page)).toContainText("Welcome, Bro. Andres Kiosk!");
    await expect(overlay(page)).toContainText("Sunday Worship");
    await expect(page.locator("#code")).toHaveValue("");
  });

  test("scanning twice says already checked in", async ({ page }) => {
    await openKiosk(page);
    await typeCode(page, "FLOCK-KIOSKBBB");
    await expect(overlay(page)).toContainText("Welcome, Sis. Bella Kiosk!");
    await expect(overlay(page)).toBeHidden({ timeout: 6000 });
    await typeCode(page, "FLOCK-KIOSKBBB");
    await expect(overlay(page)).toContainText("Already checked in");
  });

  test("codes typed in lower case or with spaces still work", async ({ page }) => {
    await openKiosk(page);
    await typeCode(page, "  flock-kiosk ccc ");
    await expect(overlay(page)).toContainText("Welcome, Bro. Carlo Kiosk!");
  });

  test("unknown codes are refused politely", async ({ page }) => {
    await openKiosk(page);
    await typeCode(page, "https://example.com/not-ours");
    await expect(overlay(page)).toContainText("We don't know this code");
  });

  test("outside service hours says there's no service", async ({ page }) => {
    await openKiosk(page, { demoTime: "2026-12-08T03:00" }); // Tuesday 3 AM
    await typeCode(page, "FLOCK-KIOSKDDD");
    await expect(overlay(page)).toContainText("There's no service at this time");
  });

  test("two people scanning back to back are both checked in", async ({ page }) => {
    // At a busy door the next person scans while the previous welcome is still showing.
    await openKiosk(page, { demoTime: `${KIOSK_SUNDAY}T08:20` }); // Sunday School
    await typeCode(page, "FLOCK-KIOSKAAA");
    await expect(overlay(page)).toContainText("Andres Kiosk");
    await typeCode(page, "FLOCK-KIOSKCCC");
    await expect(overlay(page)).toContainText("Welcome, Bro. Carlo Kiosk!");
  });

  test("an empty code does nothing", async ({ page }) => {
    await openKiosk(page);
    await typeCode(page, "   ");
    await expect(overlay(page)).toBeHidden();
  });

  test("the camera help appears when the browser blocks the camera", async ({ page }) => {
    await page.goto("/checkin/kiosk/");
    // The desktop test browser has no camera; the kiosk must still be usable.
    await expect(page.locator("#camera-msg")).toBeVisible();
    await expect(page.locator("#code")).toBeEditable();
  });

  test("scans appear on the usher's check-in page by themselves", async ({ page, context }) => {
    await openCheckinService(page);
    const kiosk = await context.newPage();
    await openKiosk(kiosk, { demoTime: "2026-12-13T09:20" });
    await typeCode(kiosk, "FLOCK-KIOSKEEE");
    await expect(overlay(kiosk)).toContainText("Elias Kiosk");
    const row = page.locator("#checked-in li", { hasText: "Elias Kiosk" });
    await expect(row).toBeVisible({ timeout: 10_000 });
    await expect(row.getByText("qr_code_2")).toBeVisible();
  });

  test("the self check-in page lists recent scans", async ({ page }) => {
    await openKiosk(page);
    await typeCode(page, "FLOCK-NOPE2345");
    await expect(overlay(page)).toContainText("We don't know this code");
    await page.goto("/checkin/");
    await expect(page.getByText("Unknown code FLOCK-NOPE2345")).toBeVisible();
  });

  test.describe("as an usher", () => {
    test.use({ role: "usher" });
    test("cannot fake the scan time", async ({ page }) => {
      await page.goto("/checkin/kiosk/");
      await expect(page.getByText("Demo: pretend it's another time")).toHaveCount(0);
    });
  });
});
