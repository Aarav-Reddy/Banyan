/* Requires the parent repository's installed Playwright and axe dependencies. */
const { chromium, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const base = process.env.BANYAN_DEMO_URL || 'http://127.0.0.1:4173';
const output = path.resolve('.runtime/website-demo-qa');
(async () => {
  await fs.mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: process.env.BANYAN_CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
  try {
    for (const width of [1440, 390]) {
      const context = await browser.newContext({ viewport: { width, height: 1000 } });
      const blocked = [], errors = [], failures = [];
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if (url.origin !== new URL(base).origin || /^\/(api|_next)(\/|$)/.test(url.pathname)) {
          blocked.push(url.href); return route.abort();
        }
        return route.continue();
      });
      const page = await context.newPage();
      page.on('pageerror', error => errors.push(error.message));
      page.on('requestfailed', request => failures.push(request.url()));
      async function inspect(name) {
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${width}: ${name} page overflow`);
        const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
        assert.deepEqual(audit.violations.map(v => ({ id: v.id, targets: v.nodes.map(n => n.target) })), [], `${width}: ${name} accessibility`);
        await page.screenshot({ path: path.join(output, `${name}-${width}.png`), fullPage: true });
      }
      await page.goto(base + '/demo');
      await expect(page.locator('.organization-card')).toHaveCount(8);
      await inspect('discover');
      await page.getByLabel('Search organizations').fill('Aster');
      await expect(page.locator('.organization-card')).toHaveCount(1);
      await page.getByLabel('Search organizations').fill('no-such-organization');
      await expect(page.getByRole('heading', { name: 'No organizations match' })).toBeVisible();
      await page.getByRole('button', { name: 'Clear filters' }).first().click();
      await page.getByLabel('Service area').selectOption('East Downtown');
      await expect(page.locator('.organization-card')).toHaveCount(2);
      await page.getByRole('button', { name: 'Clear filters' }).first().click();
      for (const id of ['org-1', 'org-2', 'org-3']) await page.locator(`[data-shortlist="${id}"]`).click();
      await page.locator('[data-shortlist="org-4"]').click();
      await expect(page.locator('#selection-limit')).toBeVisible();
      await expect(page.locator('#compare-count')).toHaveText('3');
      await page.locator('[data-nav="compare"]').click();
      await expect(page.locator('.compare-table')).toBeVisible();
      await inspect('compare');
      await page.getByRole('button', { name: 'Remove Demo · Lantern Food Network from comparison' }).click();
      await expect(page.locator('#compare-count')).toHaveText('2');
      await page.locator('.compare-table').getByRole('link', { name: 'Demo · Aster Table', exact: true }).click();
      await expect(page.getByRole('heading', { name: 'Demo · Aster Table', exact: true, level: 1 })).toBeVisible();
      await expect(page.getByRole('cell', { name: '$95,256', exact: true })).toBeVisible();
      await inspect('profile');
      await page.goBack();
      await expect(page.locator('.compare-table')).toBeVisible();
      await page.locator('[data-nav="evidence"]').click();
      await page.getByLabel('Evidence type').selectOption('early hypothesis');
      await expect(page.locator('.evidence-card')).toHaveCount(1);
      await page.getByText('Source and limitations', { exact: true }).click();
      await expect(page.locator('details')).toHaveAttribute('open', '');
      await inspect('evidence');
      await page.goto(base + '/demo#evidence/evidence-8');
      await expect(page.locator('.evidence-card')).toHaveCount(1);
      await expect(page.getByText('Evening pickup was discontinued after low participation.', { exact: true })).toBeVisible();
      await page.locator('[data-nav="workspace"]').click();
      await expect(page.locator('.program-table')).toContainText('50 of 100 households');
      await inspect('workspace');
      await page.getByLabel('Explore an organization').selectOption('org-5');
      await expect(page.locator('.program-table')).toContainText('Not reported');
      await expect(page.locator('.program-table')).toContainText('Unknown');
      await page.goto(base + '/demo#organization/missing');
      await expect(page.getByRole('heading', { name: 'Organization not found' })).toBeVisible();
      await page.goto(base + '/demo#%E0%A4%A');
      await expect(page.getByRole('heading', { name: 'View not found' })).toBeVisible();
      await page.goto(base + '/demo#main');
      await expect(page.locator('.organization-card')).toHaveCount(8);
      await page.goto(base + '/demo');
      await page.keyboard.press('Tab');
      await expect(page.locator(':focus')).toHaveText('Skip to content');
      await page.keyboard.press('Enter');
      await expect(page.locator('#main')).toBeFocused();
      await page.locator('[data-shortlist="org-1"]').click();
      await page.reload();
      await expect(page.locator('#compare-count')).toHaveText('0');
      for (const [route, name] of [['/', 'home'], ['/pitch', 'pitch']]) {
        await page.goto(base + route); await inspect(name);
      }
      assert.deepEqual(blocked, [], 'No external or backend request is allowed');
      assert.deepEqual(errors, [], 'No browser runtime errors');
      assert.deepEqual(failures, [], 'No failed asset requests');
      await context.close();
      console.log(`PASS ${width}px: search, area, empty state, compare limit/remove, profile, back navigation, evidence, workspace, missingness, invalid links, keyboard, reload reset, home/pitch, axe, no external/backend requests`);
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
