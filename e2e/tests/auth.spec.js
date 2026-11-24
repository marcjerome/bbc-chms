import { test, expect, PASSWORD, memberLink, expectNoAccess } from "./helpers.js";

test.describe("signing in", () => {
  test.use({ role: null });

  test("pages need a login and send you back afterwards", async ({ page }) => {
    await page.goto("/members/");
    await expect(page).toHaveURL(/\/login\/\?next=(%2F|\/)members(%2F|\/)$/);
    await page.fill("#id_username", "secretary");
    await page.fill("#id_password", PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/members\/$/);
  });

  test("wrong password shows an error and keeps the username", async ({ page }) => {
    await page.goto("/login/");
    await page.fill("#id_username", "admin");
    await page.fill("#id_password", "not-the-password");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByText(/correct username and password/i)).toBeVisible();
    await expect(page.locator("#id_username")).toHaveValue("admin");
    await expect(page.locator("#id_password")).toHaveValue("");
  });

  test("username and password are required", async ({ page }) => {
    await page.goto("/login/");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/login\//);
    expect(await page.locator("#id_username").evaluate((e) => e.validity.valueMissing)).toBe(true);
  });

  test("show password button reveals what was typed", async ({ page }) => {
    await page.goto("/login/");
    await page.fill("#id_password", "secret");
    await expect(page.locator("#id_password")).toHaveAttribute("type", "password");
    await page.getByRole("button", { name: "Show password" }).click();
    await expect(page.locator("#id_password")).toHaveAttribute("type", "text");
  });

  test("log out ends the session", async ({ page }) => {
    await page.goto("/login/");
    await page.fill("#id_username", "usher");
    await page.fill("#id_password", PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).not.toHaveURL(/\/login\//);
    await page.getByRole("button", { name: "Log out" }).click();
    await page.goto("/");
    await expect(page).toHaveURL(/\/login\//);
  });
});

test.describe("roles", () => {
  // A 403 page makes the browser log "Failed to load resource", which is expected here.
  test.use({ allowErrors: true });

  test.describe("usher", () => {
    test.use({ role: "usher" });
    test("can look people up but not add or edit them", async ({ page }) => {
      await page.goto("/members/");
      await expect(page.getByRole("link", { name: "Add member" })).toHaveCount(0);
      await expectNoAccess(page, "/members/new/");
    });
    test("cannot give out QR codes", async ({ page }) => {
      await page.goto("/members/?q=Victor");
      await memberLink(page, "Victor Visita").first().click();
      await expect(page.getByRole("button", { name: "Give QR code" })).toHaveCount(0);
    });
  });

  test.describe("secretary", () => {
    test.use({ role: "secretary" });
    test("can add members but not manage service types", async ({ page }) => {
      await page.goto("/members/new/");
      await expect(page.locator("h1")).toHaveText("Add member");
      await expectNoAccess(page, "/attendance/service-types/new/");
    });
  });

  test.describe("check-in kiosk account", () => {
    test.use({ role: "kiosk" });
    test("can only use the kiosk", async ({ page }) => {
      await page.goto("/checkin/kiosk/");
      await expect(page.getByText("Hold your Bible's QR code up to the camera")).toBeVisible();
      await page.goto("/");  // never the dashboard: it shows names, birthdays and who was missed
      await expect(page).toHaveURL(/\/checkin\/kiosk\/$/);
      await expect(page.getByRole("link", { name: "Leave kiosk" })).toHaveCount(0);
      for (const url of ["/members/", "/members/1/", "/checkin/", "/checkin/stickers/", "/attendance/", "/members/birthdays/"]) {
        await expectNoAccess(page, url);
      }
    });
  });
});
