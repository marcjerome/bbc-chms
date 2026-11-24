// Flock end-to-end tests. See README.md. Runs against the throwaway stack in docker-compose.e2e.yml.
import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:8004";
const CAMERA_VIDEO = path.resolve(import.meta.dirname, ".fixtures/qr-camera.y4m");

export default defineConfig({
  testDir: "./tests",
  globalSetup: "./global-setup.js",
  timeout: 30_000,
  expect: { timeout: 8_000 },
  fullyParallel: true,
  workers: process.env.CI ? 2 : 4,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: BASE_URL,
    timezoneId: "Asia/Manila",
    locale: "en-PH",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "setup", testMatch: /auth\.setup\.js/ },
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"] },
      dependencies: ["setup"],
      testIgnore: [/camera\.spec\.js/, /mobile\.spec\.js/, /modes\.spec\.js/],
    },
    {
      // The church uses Android phones and tablets.
      name: "android",
      use: { ...devices["Pixel 7"] },
      dependencies: ["setup"],
      testMatch: /mobile\.spec\.js/,
    },
    {
      // A fake webcam that shows a real QR sticker (made by `manage.py seed_e2e`).
      name: "camera",
      use: {
        ...devices["Desktop Chrome"],
        permissions: ["camera"],
        launchOptions: {
          args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                 `--use-file-for-fake-video-capture=${CAMERA_VIDEO}`],
        },
      },
      dependencies: ["setup"],
      testMatch: /camera\.spec\.js/,
    },
    {
      // Switching check-in modes changes the whole app, so these run after everything else, one at a time.
      name: "modes",
      use: { ...devices["Desktop Chrome"] },
      dependencies: ["desktop", "android", "camera"],
      testMatch: /modes\.spec\.js/,
    },
  ],
});
