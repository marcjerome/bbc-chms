import fs from "node:fs";
import { test, expect, uniq, fieldError, submitWithoutBrowserChecks, createMember, openMember, memberLink } from "./helpers.js";

test.describe("adding and editing members", () => {
  test("add a member with full details", async ({ page }) => {
    const first = uniq("Lito");
    await createMember(page, {
      first, last: "Mercado", title: "Bro.", gender: "M", birth_date: "1990-04-12", phone: "0917 555 1234",
      email: "lito@example.com", household: { label: "Santos Family" }, household_role: "child", status: "attendee",
    });
    await expect(page.getByText(`${first} Mercado was added.`)).toBeVisible();
    await expect(page.locator("h1")).toHaveText(`Bro. ${first} Mercado`);
    await expect(page.getByText("Santos Family")).toBeVisible();
    await expect(page.getByText("April 12, 1990")).toBeVisible();
  });

  test("edit a member", async ({ page }) => {
    const first = uniq("Edna");
    await createMember(page, { first, last: "Editado" });
    await page.getByRole("link", { name: "Edit" }).click();
    await page.fill("#id_occupation", "Teacher");
    await page.selectOption("#id_status", "member");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText(`${first} Editado was updated.`)).toBeVisible();
    await expect(page.getByText("Teacher")).toBeVisible();
  });

  test("delete asks first, then removes the member", async ({ page }) => {
    const first = uniq("Dora");
    await createMember(page, { first, last: "Delete" });
    await page.locator("a[href$='/delete/']").click();
    await page.getByRole("button", { name: "Delete permanently" }).click();
    await expect(page.getByText(`${first} Delete was deleted.`)).toBeVisible();
    await page.goto(`/members/?q=${first}`);
    await expect(memberLink(page, `${first} Delete`)).toHaveCount(0);
  });
});

test.describe("member form validation", () => {
  test("first and last name are required (browser and server)", async ({ page }) => {
    await page.goto("/members/new/");
    expect(await page.locator("#id_first_name").evaluate((e) => e.required)).toBe(true);
    await submitWithoutBrowserChecks(page);
    await page.fill("#id_first_name", "   "); // only spaces
    await page.getByRole("button", { name: "Save" }).click();
    await expect(fieldError(page, "first_name")).toContainText("required");
    await expect(fieldError(page, "last_name")).toContainText("required");
    await expect(page).toHaveURL(/\/members\/new\/$/);
  });

  test("email must be a valid address", async ({ page }) => {
    await page.goto("/members/new/");
    await submitWithoutBrowserChecks(page);
    await page.fill("#id_first_name", "Ema");
    await page.fill("#id_last_name", "Il");
    await page.fill("#id_email", "not-an-email");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(fieldError(page, "email")).toContainText(/valid email/i);
  });

  test("household role needs a household", async ({ page }) => {
    await page.goto("/members/new/");
    await page.fill("#id_first_name", "Rolo");
    await page.fill("#id_last_name", "Nohouse");
    await page.selectOption("#id_household_role", "child");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(fieldError(page, "household_role")).toContainText("Choose a household first.");
  });

  test("mobile number must look like a phone number", async ({ page }) => {
    await page.goto("/members/new/");
    await page.fill("#id_first_name", "Phony");
    await page.fill("#id_last_name", "Number");
    await page.fill("#id_phone", "call me maybe");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(fieldError(page, "phone")).toBeVisible();
  });

  test("birthday cannot be in the future", async ({ page }) => {
    await page.goto("/members/new/");
    await page.fill("#id_first_name", "Future");
    await page.fill("#id_last_name", "Baby");
    await page.fill("#id_birth_date", "2099-01-01");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(fieldError(page, "birth_date")).toBeVisible();
  });

  test("church dates cannot be before the birthday", async ({ page }) => {
    await page.goto("/members/new/");
    await page.fill("#id_first_name", "Early");
    await page.fill("#id_last_name", "Bird");
    await page.fill("#id_birth_date", "2000-01-01");
    await page.fill("#id_baptism_date", "1995-06-01");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(fieldError(page, "baptism_date")).toBeVisible();
  });

  test("a baptism date marks the member as baptized", async ({ page }) => {
    const first = uniq("Bapt");
    await createMember(page, { first, last: "Isado", baptism_date: "2020-03-01" });
    await expect(page.getByText(`${first} Isado was added.`)).toBeVisible();
    await expect(page.getByText("Yes")).toBeVisible();
  });

  test("a photo must be an image file", async ({ page }) => {
    await page.goto("/members/new/");
    await page.fill("#id_first_name", "Photo");
    await page.fill("#id_last_name", "Bad");
    await page.setInputFiles("#id_photo", { name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("hello") });
    await page.getByRole("button", { name: "Save" }).click();
    await expect(fieldError(page, "photo")).toContainText(/image/i);
  });

  test("a validation error keeps everything already typed", async ({ page }) => {
    await page.goto("/members/new/");
    await page.fill("#id_first_name", "Keep");
    await page.fill("#id_last_name", "Typing");
    await page.fill("#id_occupation", "Farmer");
    await page.selectOption("#id_household_role", "child"); // invalid without household
    await page.getByRole("button", { name: "Save" }).click();
    await expect(fieldError(page, "household_role")).toBeVisible();
    await expect(page.locator("#id_first_name")).toHaveValue("Keep");
    await expect(page.locator("#id_occupation")).toHaveValue("Farmer");
  });
});

test.describe("finding members", () => {
  test("live search by name", async ({ page }) => {
    await page.goto("/members/");
    await page.fill("input[name=q]", "Pedro");
    await expect(page).toHaveURL(/q=Pedro/);
    await expect(memberLink(page, "Pedro Santos")).toBeVisible();
    await expect(memberLink(page, "Rosa Santos")).toHaveCount(0);
  });

  test("search by mobile number and email", async ({ page }) => {
    await page.goto("/members/?q=09173334444");
    await expect(memberLink(page, "Rosa Santos")).toBeVisible();
    await page.goto("/members/?q=pedro@example.com");
    await expect(memberLink(page, "Pedro Santos")).toBeVisible();
  });

  test("filter by status", async ({ page }) => {
    await page.goto("/members/");
    await page.locator("label", { hasText: /^Visitor$/ }).click();
    await expect(page).toHaveURL(/status=visitor/);
    await expect(memberLink(page, "Victor Visita")).toBeVisible();
    await expect(memberLink(page, "Pedro Santos")).toHaveCount(0);
  });

  test("no results shows a friendly message", async ({ page }) => {
    await page.goto("/members/?q=Zzyzx");
    await expect(page.getByText(/no one|no members|nobody/i)).toBeVisible();
  });

  test("export the filtered list to CSV", async ({ page }) => {
    await page.goto("/members/?q=Santos");
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("link", { name: "Export CSV" }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/^members-\d{4}-\d{2}-\d{2}\.csv$/);
    const text = fs.readFileSync(await download.path(), "utf8");
    expect(text).toContain("Santos,Pedro");
    expect(text).not.toContain("Visita");
  });

  test("profile shows the household", async ({ page }) => {
    await openMember(page, "Pedro Santos");
    await expect(page.getByRole("link", { name: "Santos Family" })).toBeVisible();
    await expect(page.getByRole("link", { name: /Rosa · Spouse/ })).toBeVisible();
  });
});
