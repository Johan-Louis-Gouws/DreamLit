import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  use: {
    baseURL: "http://127.0.0.1:8766",
    headless: true,
    screenshot: "only-on-failure",
  },
  workers: 1,
  webServer: {
    command: "../.venv/bin/python ../tests/browser_server.py",
    url: "http://127.0.0.1:8766/api/health",
    reuseExistingServer: false,
    timeout: 15000,
  },
});
