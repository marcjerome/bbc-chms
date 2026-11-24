// Runs in the "android" project (Pixel 7 screen): ushers use phones, kiosks use tablets.
import { test, expect, openCheckinService } from "./helpers.js";

async function expectNoSidewaysScroll(page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, "page is wider than the screen").toBeLessThanOrEqual(1);
}

test.describe("on a phone", () => {
  test.use({ role: "usher" });

  test("usher can open the menu and check someone in", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Open menu" }).click();
    await page.getByRole("link", { name: "Attendance", exact: true }).click();
    await expect(page.locator("h1")).toBeVisible();
    await openCheckinService(page);
    await expectNoSidewaysScroll(page);
    await page.fill("input[name=q]", "Pia");
    const row = page.locator("#search-results li", { hasText: "Pia Phone" });
    await row.getByRole("button", { name: /Check in|Present/ }).click();
    await expect(row.getByRole("button", { name: /Present/ })).toBeVisible();
  });

  for (const url of ["/", "/members/", "/members/birthdays/", "/members/visitation/", "/attendance/", "/checkin/", "/checkin/kiosk/"]) {
    test(`${url} fits the screen`, async ({ page }) => {
      await page.goto(url);
      await expectNoSidewaysScroll(page);
    });
  }
});
