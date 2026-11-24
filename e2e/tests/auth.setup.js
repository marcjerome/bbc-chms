// Logs in once per role and saves the session, so tests start already signed in.
import { test as setup, expect } from "@playwright/test";
import { PASSWORD, ROLES, authFile } from "./helpers.js";

for (const role of ROLES) {
  setup(`sign in as ${role}`, async ({ page }) => {
    await page.goto("/login/");
    await page.fill("#id_username", role);
    await page.fill("#id_password", PASSWORD);
    await page.check("input[name=remember]");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).not.toHaveURL(/\/login\//);
    await page.context().storageState({ path: authFile(role) });
  });
}
