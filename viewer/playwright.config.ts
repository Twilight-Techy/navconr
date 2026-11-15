import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  use: {
    baseURL: "http://127.0.0.1:8765",
    headless: true,
    viewport: { width: 1440, height: 1000 },
  },
  webServer: {
    command:
      "../.venv/bin/python ../scripts/prepare_demo.py --db .navconr/browser-test.sqlite && ../.venv/bin/navconr serve --db ../.navconr/browser-test.sqlite --viewer dist --port 8765",
    url: "http://127.0.0.1:8765",
    reuseExistingServer: false,
    timeout: 20000,
  },
});
