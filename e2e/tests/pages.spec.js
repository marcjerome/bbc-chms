// Every page opens without a server error, JavaScript error or broken image.
import { test, expect, memberLink, openCheckinService } from "./helpers.js";

const PAGES = [
  "/", "/members/", "/members/new/", "/members/birthdays/", "/members/visitation/",
  "/members/households/", "/members/households/new/", "/attendance/", "/attendance/service-types/",
  "/attendance/service-types/new/", "/checkin/", "/checkin/stickers/", "/checkin/stickers/?show=all",
];

for (const url of PAGES) {
  test(`opens ${url}`, async ({ page }) => {
    const resp = await page.goto(url);
    expect(resp.status()).toBe(200);
    await expect(page.locator("h1").first()).toBeVisible();
    const broken = await page.$$eval("img", (imgs) => imgs.filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.src));
    expect(broken, "broken images").toEqual([]);
  });
}

test("every link in the menu works", async ({ page }) => {
  await page.goto("/");
  const links = await page.$$eval("aside nav a", (as) => as.map((a) => a.getAttribute("href")));
  expect(links.length).toBeGreaterThan(5);
  for (const href of links.filter((h) => !h.startsWith("/admin"))) {
    const resp = await page.goto(href);
    expect(resp.status(), href).toBe(200);
  }
});

test("member, household and service pages open from their lists", async ({ page }) => {
  await page.goto("/members/?q=Pedro");
  await memberLink(page, "Pedro Santos").first().click();
  await expect(page.locator("h1")).toHaveText("Bro. Pedro Santos");
  await page.getByRole("link", { name: "Santos Family" }).first().click();
  await expect(page.locator("h1")).toContainText("Santos Family");
  await openCheckinService(page);
});

test("birthday list prints from its own page", async ({ page }) => {
  await page.goto("/members/birthdays/");
  await expect(page.getByRole("button", { name: /Print/ }).or(page.getByRole("link", { name: /Print/ }))).toBeVisible();
});

test.describe("missing pages", () => {
  test.use({ allowErrors: true });
  test("an unknown member gives a 404, not a crash", async ({ page }) => {
    const resp = await page.goto("/members/999999/");
    expect(resp.status()).toBe(404);
  });
  test("a bad birthday week falls back to this week", async ({ page }) => {
    const resp = await page.goto("/members/birthdays/?week=not-a-date");
    expect(resp.status()).toBe(200);
  });
});
