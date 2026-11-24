import { test, expect, uniq, fieldError, submitWithoutBrowserChecks, openCheckinService } from "./helpers.js";

test.describe("households", () => {
  test("create a household and add a family member to it", async ({ page }) => {
    const name = uniq("Reyes") + " Family";
    await page.goto("/members/households/");
    await page.getByRole("link", { name: "Add household" }).click();
    await page.fill("#id_name", name);
    await page.fill("#id_address_line", "Purok 5");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText(`${name} was added.`)).toBeVisible();
    await page.getByRole("link", { name: "Add family member" }).click();
    await expect(page.locator("#id_household option:checked")).toHaveText(name);
    await page.fill("#id_first_name", "Nena");
    await page.fill("#id_last_name", "Reyes");
    await page.selectOption("#id_household_role", "head");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByRole("link", { name: name })).toBeVisible();
  });

  test("household name is required", async ({ page }) => {
    await page.goto("/members/households/new/");
    await submitWithoutBrowserChecks(page);
    await page.getByRole("button", { name: "Save" }).click();
    await expect(fieldError(page, "name")).toContainText("required");
  });
});

test.describe("service types", () => {
  test("add a service type with its usual day and time", async ({ page }) => {
    const name = uniq("Bible Study ");
    await page.goto("/attendance/service-types/");
    await page.getByRole("link", { name: "Add service type" }).click();
    await page.fill("#id_name", name);
    await page.selectOption("#id_weekday", "4");
    await page.fill("#id_start_time", "18:30");
    await page.getByRole("button", { name: "Save" }).click();
    const row = page.getByRole("row", { name: new RegExp(name) });
    await expect(row).toContainText("Friday");
    await expect(row).toContainText(/6:30 (PM|p\.m\.)/);
  });

  test("service type names must be unique", async ({ page }) => {
    await page.goto("/attendance/service-types/new/");
    await page.fill("#id_name", "Sunday Worship");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(fieldError(page, "name")).toContainText(/already exists/i);
  });
});

test.describe("services", () => {
  test("schedule a service, then reschedule it", async ({ page }) => {
    await page.goto("/attendance/");
    await page.selectOption("#id_service_type", { label: "Prayer Meeting" });
    await page.fill("#id_date", "2027-01-06");
    await page.fill("#id_title", "New Year Prayer");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.locator("h1")).toHaveText("New Year Prayer");
    await page.getByRole("link", { name: "Change" }).click();
    await page.fill("#id_start_time", "20:00");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Rescheduled")).toBeVisible();
    await expect(page.getByText(/8:00 (PM|p\.m\.)/)).toBeVisible();
  });

  test("the same service twice on one date is refused", async ({ page }) => {
    await page.goto("/attendance/");
    await page.selectOption("#id_service_type", { label: "Sunday Worship" });
    await page.fill("#id_date", "2026-12-13");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("That service already exists for this date.")).toBeVisible();
  });

  test("a service needs a date", async ({ page }) => {
    await page.goto("/attendance/");
    await submitWithoutBrowserChecks(page);
    await page.fill("#id_date", "");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(fieldError(page, "date")).toContainText("required");
  });
});

test.describe("usher check-in", () => {
  test.use({ role: "usher" });

  test("search a name, check in, then undo", async ({ page }) => {
    await openCheckinService(page);
    await page.fill("input[name=q]", "Rosa");
    const row = page.locator("#search-results li", { hasText: "Rosa Santos" });
    await row.getByRole("button", { name: "Check in" }).click();
    await expect(row.getByRole("button", { name: /Present/ })).toBeVisible();
    const list = page.locator("#checked-in");
    await expect(list).toContainText("Rosa Santos");
    await list.locator("li", { hasText: "Rosa Santos" }).getByRole("button", { name: "Undo" }).click();
    await expect(list).not.toContainText("Rosa Santos");
  });

  test("searching someone unknown suggests adding a visitor", async ({ page }) => {
    await openCheckinService(page);
    await page.fill("input[name=q]", "Qwertyuiop");
    await expect(page.getByText(/No one named “Qwertyuiop”/)).toBeVisible();
  });

  test("add a first-time visitor, who is checked in", async ({ page }) => {
    const first = uniq("Vic");
    await openCheckinService(page);
    await page.getByRole("button", { name: "Add first-time visitor" }).click();
    const form = page.locator("#visitor-form");
    await form.locator("#id_first_name").fill(first);
    await form.locator("#id_last_name").fill("Bagong");
    await form.locator("#id_phone").fill("09181234567");
    await form.getByRole("button", { name: "Add & check in" }).click();
    await expect(page.locator("#checked-in")).toContainText(`${first} Bagong`);
  });

  test("visitor form validates names", async ({ page }) => {
    await openCheckinService(page);
    await page.getByRole("button", { name: "Add first-time visitor" }).click();
    const form = page.locator("#visitor-form");
    await form.evaluate((f) => { f.noValidate = true; });
    await form.getByRole("button", { name: "Add & check in" }).click();
    await expect(page.locator("#visitor-form #id_first_name_error")).toContainText("required");
    await expect(page.locator("#visitor-form #id_last_name_error")).toContainText("required");
  });

  test("visitor phone must look like a phone number", async ({ page }) => {
    await openCheckinService(page);
    await page.getByRole("button", { name: "Add first-time visitor" }).click();
    const form = page.locator("#visitor-form");
    await form.locator("#id_first_name").fill("Bad");
    await form.locator("#id_last_name").fill("Phone");
    await form.locator("#id_phone").fill("abc");
    await form.getByRole("button", { name: "Add & check in" }).click();
    await expect(page.locator("#visitor-form #id_phone_error")).toBeVisible();
  });

  test("not yet seen lists people who haven't checked in", async ({ page }) => {
    await openCheckinService(page);
    await page.getByRole("button", { name: /Not yet seen/ }).click();
    await expect(page.locator("#search-results")).toContainText("Pedro Santos");
    // Inactive people are not expected at services.
    await expect(page.locator("#search-results")).not.toContainText("Ines Inactive");
  });
});

test.describe("guest counter", () => {
  test("adds and removes guests, never below zero", async ({ page }) => {
    await page.goto("/attendance/");
    await page.selectOption("#id_service_type", { label: "Youth Fellowship" });
    await page.fill("#id_date", "2027-02-06");
    await page.getByRole("button", { name: "Save" }).click();
    const plus = page.getByRole("button", { name: "One more guest" });
    const minus = page.getByRole("button", { name: "One fewer guest" });
    const count = page.locator("#counters .card").nth(1).locator("span.font-serif");
    await minus.click();
    await expect(count).toHaveText("0");
    await plus.click();
    await expect(count).toHaveText("1");
    await plus.click();
    await expect(count).toHaveText("2");
    await minus.click();
    await expect(count).toHaveText("1");
  });
});
