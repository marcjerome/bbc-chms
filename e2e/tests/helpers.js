import { test as base, expect } from "@playwright/test";
import path from "node:path";

// Must match core/management/commands/seed_e2e.py
export const PASSWORD = "e2e-pass-123";
export const ROLES = ["admin", "secretary", "usher", "kiosk"];
export const KIOSK_SUNDAY = "2026-12-06";
export const CHECKIN_SERVICE_TITLE = "E2E Check-in Sunday"; // Sunday Worship on 2026-12-13

export const authFile = (role) => path.resolve(import.meta.dirname, "../.auth", `${role}.json`);

/** A unique, readable name so parallel tests never collide, e.g. "Zed1732a". */
export const uniq = (prefix) => `${prefix}${Date.now().toString(36).slice(-4)}${Math.floor(Math.random() * 1296).toString(36)}`;

/**
 * Every test fails if the page throws a JavaScript error, logs a console error, or any request
 * gets a server error (5xx). Opt out per test with `test.use({ allowErrors: true })`.
 */
export const test = base.extend({
  allowErrors: [false, { option: true }],
  role: ["admin", { option: true }],
  storageState: async ({ role }, use) => use(role ? authFile(role) : undefined),
  page: async ({ page, allowErrors }, use) => {
    const problems = [];
    page.on("pageerror", (e) => problems.push(`JS error: ${e.message}`));
    page.on("console", (m) => { if (m.type() === "error") problems.push(`console: ${m.text()}`); });
    page.on("response", (r) => { if (r.status() >= 500) problems.push(`HTTP ${r.status()} ${r.url()}`); });
    await use(page);
    if (!allowErrors) expect(problems, "page errors during the test").toEqual([]);
  },
});
export { expect };

/** The error list Django renders under a form field (<ul id="id_<field>_error">). */
export const fieldError = (page, field) => page.locator(`#id_${field}_error`);

/** Submit a form without the browser's own checks, to test the server's validation. */
export async function submitWithoutBrowserChecks(page, formSelector = "main form[method=post]") {
  await page.locator(formSelector).first().evaluate((f) => { f.noValidate = true; });
}

/** The member list shows "Last, First": the link to "Pedro Santos" reads "Bro. Santos, Pedro". */
export const memberLink = (page, fullName) => {
  const [first, ...rest] = fullName.split(" ");
  return page.getByRole("link", { name: new RegExp(`${rest.join(" ")}, ${first}`) });
};

/** Open a member's profile from the member list search. */
export async function openMember(page, name) {
  await page.goto(`/members/?q=${encodeURIComponent(name)}`);
  await memberLink(page, name).first().click();
  await expect(page.locator("h1")).toContainText(name);
}

/** Expect the "no access" page a signed-in user gets for a page their role can't open. */
export async function expectNoAccess(page, url) {
  const resp = await page.goto(url);
  expect(resp.status(), url).toBe(403);
  await expect(page.getByRole("heading", { name: "You don't have access to this page" })).toBeVisible();
}

/** Create a member through the form and land on their profile. */
export async function createMember(page, { first, last, ...rest }) {
  await page.goto("/members/new/");
  await page.fill("#id_first_name", first);
  await page.fill("#id_last_name", last);
  for (const [field, value] of Object.entries(rest)) {
    const el = page.locator(`#id_${field}`);
    const tag = await el.evaluate((e) => e.tagName);
    if (tag === "SELECT") await el.selectOption(value); else await el.fill(value);
  }
  await page.getByRole("button", { name: "Save" }).click();
}

/** The check-in page of the fixed E2E service (an upcoming service, found through its Change link). */
export async function openCheckinService(page) {
  await page.goto("/attendance/");
  const item = page.locator("li", { hasText: CHECKIN_SERVICE_TITLE });
  const edit = await item.getByRole("link", { name: "Change" }).getAttribute("href");
  await page.goto(edit.replace(/edit\/$/, ""));
  await expect(page.locator("h1")).toHaveText(CHECKIN_SERVICE_TITLE);
}
