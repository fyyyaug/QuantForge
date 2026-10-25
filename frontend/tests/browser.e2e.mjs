// Disposable, local-only browser regression. No provider calls or cloud resources.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdtemp, mkdir, readFile, rm } from 'node:fs/promises';
import { createServer } from 'node:net';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const root = fileURLToPath(new URL('../../', import.meta.url));
const output = path.resolve(root, '.quantforge-browser-tests');
const directory = await mkdtemp(path.join(tmpdir(), 'quantforge-browser-'));
await mkdir(output, { recursive: true });
const reservation = createServer();
await new Promise((resolve, reject) => {
  reservation.once('error', reject);
  reservation.listen(0, '127.0.0.1', resolve);
});
const port = reservation.address().port;
await new Promise((resolve) => reservation.close(resolve));
const baseURL = `http://127.0.0.1:${port}`;
let serverLog = '',
  browser;
const server = spawn(process.env.QUANTFORGE_PYTHON ?? 'python', ['-m', 'backend'], {
  cwd: root,
  env: {
    ...process.env,
    PORT: String(port),
    QUANTFORGE_HOST: '127.0.0.1',
    QUANTFORGE_DATA_DIR: directory,
    QUANTFORGE_PUBLIC_DEMO: 'true',
    QUANTFORGE_COOKIE_SECURE: 'false',
    QUANTFORGE_API_TOKEN: '',
    QUANTFORGE_ENABLE_PLANNER: 'false',
    ANTHROPIC_API_KEY: '',
  },
  stdio: ['ignore', 'pipe', 'pipe'],
});
server.stdout.on('data', (chunk) => {
  serverLog += chunk;
});
server.stderr.on('data', (chunk) => {
  serverLog += chunk;
});
const deadline = setTimeout(() => {
  server.kill('SIGKILL');
  process.exitCode = 1;
}, 180000);

async function waitForServer() {
  for (let i = 0; i < 100; i += 1) {
    if (server.exitCode !== null) throw new Error(`Server exited: ${serverLog}`);
    try {
      if ((await fetch(`${baseURL}/health`)).ok) return;
    } catch {
      /* startup */
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Server did not become healthy: ${serverLog}`);
}

async function enterDemo(page) {
  await page.goto(baseURL);
  await page.getByRole('button', { name: 'Try the live demo ↗', exact: true }).click();
  await page.getByRole('heading', { name: 'Start with a hypothesis.', exact: true }).waitFor();
  await page.locator('.planner-card summary').click();
  assert.equal(
    await page.getByRole('button', { name: 'Draft a plan for review →', exact: true }).isDisabled(),
    true,
  );
  await page.locator('.planner-card summary').click();
}

async function approvePlan(page, diagnostic = false) {
  await page
    .getByRole('checkbox', {
      name: 'I reviewed these assumptions and understand that this is a synthetic research simulation.',
    })
    .check();
  await page
    .getByRole('button', {
      name: diagnostic ? 'Run invalid diagnostic →' : 'Approve & run experiment →',
      exact: true,
    })
    .click();
  await page.getByRole('heading', { name: 'Read the result. Check the evidence.', exact: true }).waitFor();
}

async function approveCorrection(page) {
  const dialog = page.getByRole('dialog');
  await dialog
    .getByRole('checkbox', { name: 'I reviewed this diff and approve a separate experiment.' })
    .check();
  await dialog.getByRole('button', { name: 'Approve & rerun →', exact: true }).click();
  await page.getByRole('heading', { name: 'A change you can trace.', exact: true }).waitFor();
}

async function newResearch(page) {
  await page.getByRole('link', { name: /New research/ }).click();
  await page.getByRole('heading', { name: 'Start with a hypothesis.', exact: true }).waitFor();
}

const observed = [];
try {
  await waitForServer();
  browser = await chromium.launch({ headless: true });
  for (const [name, viewport] of [
    ['desktop', { width: 1440, height: 1050 }],
    ['mobile', { width: 390, height: 844 }],
  ]) {
    const context = await browser.newContext({ baseURL, viewport, acceptDownloads: true });
    const page = await context.newPage();
    page.setDefaultTimeout(10000);
    const pageErrors = [];
    page.on('pageerror', (error) => pageErrors.push(error.message));
    try {
      await enterDemo(page);
      const form = page.locator('#plan-form');
      await form.getByLabel('Commission (bps / side)', { exact: true }).fill('10');
      await form.getByRole('button', { name: 'Review plan →', exact: true }).click();
      await approvePlan(page);
      await page.getByRole('button', { name: 'Inspect the audit →', exact: true }).click();
      await page.locator('#cost-form').waitFor();
      assert.equal(await page.getByLabel('Commission (bps / side)', { exact: true }).inputValue(), '15');
      await page.getByLabel('Commission (bps / side)', { exact: true }).fill('10');
      assert.equal(
        await page.getByRole('button', { name: 'Review cost change →', exact: true }).isDisabled(),
        true,
      );
      await page.getByLabel('Commission (bps / side)', { exact: true }).fill('15');
      await page.getByRole('button', { name: 'Review cost change →', exact: true }).click();
      await approveCorrection(page);
      await page.getByRole('button', { name: 'Audit new experiment', exact: true }).click();
      assert.equal(await page.getByLabel('Commission (bps / side)', { exact: true }).inputValue(), '20');
      await page.getByRole('button', { name: 'Review cost change →', exact: true }).click();
      await approveCorrection(page);

      const downloadPromise = page.waitForEvent('download');
      await page.getByRole('button', { name: 'Download comparison report', exact: true }).click();
      const download = await downloadPromise;
      const reportFile = path.join(output, `comparison-${name}.md`);
      await download.saveAs(reportFile);
      const report = await readFile(reportFile, 'utf8');
      for (const part of [
        'Exact strategy specification',
        'lookback_sessions',
        'fee_bps_each_side',
        'Original experiment',
        'New experiment',
        'Scientific artifact hash',
        'SYNTHETIC',
      ])
        assert.ok(report.includes(part), part);

      await newResearch(page);
      await page.getByRole('button', { name: 'Review diagnostic example ↗', exact: true }).click();
      await approvePlan(page, true);
      await page.getByRole('button', { name: 'Inspect the audit →', exact: true }).click();
      await page
        .getByRole('heading', { name: 'The order came before the information.', exact: true })
        .waitFor();
      await page.getByRole('button', { name: 'Review timing correction →', exact: true }).click();
      await approveCorrection(page);
      await page.getByRole('heading', { name: '14 entry signals changed.', exact: true }).waitFor();
      await page.screenshot({ path: path.join(output, `comparison-${name}.png`), fullPage: true });
      await page.screenshot({ path: path.join(output, `comparison-viewport-${name}.png`) });

      await page.reload();
      await page.getByRole('heading', { name: 'Start with a hypothesis.', exact: true }).waitFor();
      await page.getByRole('link', { name: /Experiments/ }).click();
      await page.getByRole('heading', { name: 'Every experiment has a trail.', exact: true }).waitFor();
      await page.getByRole('button', { name: 'Open →', exact: true }).first().click();
      await page.getByRole('button', { name: '04 Compare', exact: true }).click();
      await page.getByRole('heading', { name: '14 entry signals changed.', exact: true }).waitFor();

      const rows = await (await context.request.get('/api/runs')).json();
      assert.equal(rows.length, 5);
      const second = await browser.newContext({ baseURL, viewport });
      const secondPage = await second.newPage();
      await enterDemo(secondPage);
      assert.deepEqual(await (await second.request.get('/api/runs')).json(), []);
      assert.equal((await second.request.get(`/api/runs/${rows[0].run_id}/artifact`)).status(), 404);
      await secondPage.getByRole('button', { name: 'End demo', exact: true }).click();
      await secondPage.getByRole('button', { name: 'Try the live demo ↗', exact: true }).waitFor();
      await second.close();

      await newResearch(page);
      await page.locator('#dataset').selectOption('missing_open');
      await page.locator('#plan-form').getByRole('button', { name: 'Review plan →', exact: true }).click();
      await approvePlan(page);
      await page.getByRole('heading', { name: 'Simulation blocked by validation', exact: true }).waitFor();
      assert.equal(await page.locator('.chart').count(), 0);
      await newResearch(page);
      await page.locator('#dataset').selectOption('clean_momentum');
      await page.getByLabel('Return threshold (%)', { exact: true }).fill('10000');
      await page.locator('#plan-form').getByRole('button', { name: 'Review plan →', exact: true }).click();
      await approvePlan(page);
      await page
        .getByText('No trades. This is a computed outcome, not missing data.', { exact: true })
        .waitFor();
      await newResearch(page);
      await page.getByRole('button', { name: 'Inspect audit evaluation →', exact: true }).click();
      await page.getByRole('heading', { name: '26 / 26 expected outcomes matched', exact: true }).waitFor();
      await page.screenshot({ path: path.join(output, `evaluation-${name}.png`), fullPage: true });
      await page.getByRole('link', { name: /Experiments/ }).click();
      await context.setOffline(true);
      await page.getByRole('button', { name: 'Refresh history', exact: true }).click();
      await page.getByRole('alert').waitFor();
      assert.ok((await page.getByRole('button', { name: 'Open →', exact: true }).count()) > 0);
      await context.setOffline(false);
      await page.getByRole('button', { name: 'Refresh history', exact: true }).click();
      await page.getByRole('heading', { name: 'Every experiment has a trail.', exact: true }).waitFor();
      assert.deepEqual(pageErrors, []);
      const layout = await page.evaluate(() => ({
        width: window.innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        overflow: [...document.querySelectorAll('body *')]
          .filter((element) => {
            if (element.getBoundingClientRect().right <= window.innerWidth + 1) return false;
            for (let parent = element.parentElement; parent; parent = parent.parentElement)
              if (['auto', 'hidden', 'scroll', 'clip'].includes(getComputedStyle(parent).overflowX))
                return false;
            return true;
          })
          .map((element) => ({
            tag: element.tagName,
            className: element.className,
            right: element.getBoundingClientRect().right,
            text: element.textContent.slice(0, 60),
          }))
          .slice(0, 12),
      }));
      assert.ok(layout.scrollWidth <= layout.width, JSON.stringify(layout));
      observed.push(name);
    } catch (error) {
      await page
        .screenshot({ path: path.join(output, `failure-${name}.png`), fullPage: true })
        .catch(() => {});
      throw error;
    } finally {
      await context.close();
    }
  }
  console.log(
    JSON.stringify({
      browser: 'chromium',
      passed_viewports: observed,
      scenarios: [
        'plan',
        'consecutive_cost_corrections',
        'comparison_download',
        'timing_audit',
        'refresh_and_history',
        'visitor_isolation',
        'invalid_data',
        'zero_trades',
        'audit_evaluation',
        'offline_recovery',
      ],
      provider_calls: 0,
    }),
  );
} finally {
  clearTimeout(deadline);
  await browser?.close();
  server.kill('SIGTERM');
  await new Promise((resolve) => {
    if (server.exitCode !== null) return resolve();
    const timer = setTimeout(() => {
      server.kill('SIGKILL');
      resolve();
    }, 5000);
    server.once('close', () => {
      clearTimeout(timer);
      resolve();
    });
  });
  await rm(directory, { recursive: true, force: true });
}
