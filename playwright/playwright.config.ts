import { defineConfig, devices } from '@playwright/test';

/**
 * OMS-360 Playwright configuration.
 *
 * Target: the FastAPI app started locally via START_OMS360.bat
 * (docker-compose stack: MySQL, Kafka, Zookeeper, oms360-engine, oms360-consumer),
 * exposed at http://localhost:8000.
 *
 * Reporting/artifacts (per QA task spec):
 *   - HTML report            -> playwright-report/
 *   - Screenshot on failure  -> test-results/**\/*.png
 *   - Trace on first retry   -> test-results/**\/trace.zip (requires retries >= 1,
 *                               see `retries` below - a trace is only captured
 *                               when a test is actually retried)
 *   - Video on failure       -> test-results/**\/video.webm
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,

  // retries must be >= 1 for "trace: on-first-retry" to ever produce a trace.
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 2 : undefined,

  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },

  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }],
  ],

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
    ignoreHTTPSErrors: true,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
