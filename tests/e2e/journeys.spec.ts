import { test, expect, Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFile } from 'node:fs/promises';

async function login(page: Page, username: string) {
  await page.goto('/login');
  await page.getByLabel('Username', {exact:true}).fill(username);
  await page.getByLabel('Password', {exact:true}).fill('Demo-only-Philanthra-2026!');
  await page.getByRole('button', {name:'Sign in', exact:true}).click();
  await expect(page.getByRole('button', {name:'Sign out'})).toBeVisible();
}
async function stored(page: Page, path: string) {
  const workspace = await page.getByLabel('Active workspace').inputValue();
  const response = await page.request.get('/api/v1/'+path, {headers: {'X-Workspace-ID':workspace}});
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json()).data;
}
async function submitReview(page: Page) {
  await page.getByText(/^Submit revision \d+ for review$/).click();
  await page.getByLabel('Assigned reviewer').selectOption({label:'reviewer'});
  await page.getByRole('button', {name:'Submit for review', exact:true}).click();
  await expect(page.getByText('Pending review', {exact:true}).first()).toBeVisible();
}
async function approve(page: Page, title: string) {
  await page.goto('/reviews');
  const panel = page.locator('.panel').filter({hasText:title});
  await expect(panel.getByRole('heading', {name:title,exact:true})).toBeVisible();
  await panel.locator('select[name=decision]').selectOption('approved');
  await panel.getByLabel('Reason, scope & caveats').fill('Synthetic workflow review: sources and limitations checked; no real expert endorsement.');
  await panel.getByRole('button', {name:'Record review decision'}).click();
  await expect(panel).toHaveCount(0);
}

test('donor discovers, compares, saves exact-cent draft, obtains separate review and exports', async ({page,browser}, info) => {
  const errors:string[]=[]; page.on('pageerror', error=>errors.push(error.message));
  await login(page,'foundation-admin');
  await page.goto('/discover');
  await expect(page.locator('.org-card').first()).toBeVisible();
  await page.locator('.org-card input[type=checkbox]').nth(0).check();
  await page.locator('.org-card input[type=checkbox]').nth(1).check();
  await page.getByRole('link', {name:'Compare organizations',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Compare with context.'})).toBeVisible();
  await expect(page.getByRole('row').filter({hasText:'Revenue (USD)'})).toHaveCount(1);
  await page.getByRole('link',{name:'Build a funding plan'}).click();
  const title = `QA reviewed portfolio ${info.project.name}`;
  await page.getByLabel('Portfolio name').fill(title);
  await page.getByLabel('Total budget (USD)').fill('100.01');
  for (const input of await page.getByLabel('Maximum allocation (USD)').all()) await input.fill('100.01');
  for (const input of await page.getByLabel('Capacity assumption', {exact:true}).all()) await input.fill('Synthetic donor planning assumption, not verified capacity.');
  await page.getByRole('button',{name:'Calculate & save draft'}).click();
  await expect(page.getByRole('heading',{name:title})).toBeVisible();
  const id=page.url().split('/').pop()!;
  const draft=await stored(page,`portfolios/${id}/`);
  expect(draft.portfolio.budget_cents).toBe(10001);
  expect(draft.portfolio.allocations.reduce((sum:number,a:{amount_cents:number})=>sum+a.amount_cents,0)+draft.portfolio.unallocated_cents).toBe(10001);
  await submitReview(page);
  const reviewContext=await browser.newContext(); const reviewer=await reviewContext.newPage();
  await login(reviewer,'reviewer'); await approve(reviewer,title); await reviewContext.close();
  await page.reload(); expect((await stored(page,`portfolios/${id}/`)).status).toBe('approved');
  const downloadEvent=page.waitForEvent('download'); await page.getByRole('button',{name:'Export CSV'}).click();
  const download=await downloadEvent; const csv=await readFile((await download.path())!,'utf8');
  expect(csv).toContain('approved'); expect(csv).toContain('synthetic_demo'); expect(csv).toContain('source_ids');
  await page.getByRole('link',{name:'Printable report'}).click();
  await expect(page.getByRole('heading',{name:'Funding allocation'})).toBeVisible();
  await page.screenshot({path:`docs/screenshots/portfolio-${info.project.name}.png`,fullPage:true});
  expect(errors).toEqual([]);
});

test('NGO uploads mapped aggregate, worker persists it, reviews card, grants and withdraws source', async ({page,browser}, info) => {
  await login(page,'ngo-owner'); await page.goto('/uploads');
  const fixture=(await readFile('data/fixtures/ingestion/outcomes.csv','utf8')).replace('Fictional food program',`QA import ${info.project.name}`).replace('custom_food_security_improved',`qa_outcome_${info.project.name}`).replace('synthetic-area-1','US-MD-Baltimore');
  const filename=`qa-${info.project.name}.csv`;
  await page.getByLabel('CSV, XLSX, text report, or text PDF').setInputFiles({name:filename,mimeType:'text/csv',buffer:Buffer.from(fixture)});
  await page.getByRole('button',{name:'Upload to quarantine'}).click();
  await expect(page.getByRole('heading',{name:filename})).toBeVisible();
  await expect(page.getByRole('button',{name:'Validate mapping'})).toBeVisible({timeout:30000});
  await page.getByRole('button',{name:'Validate mapping'}).click();
  await expect(page.getByRole('button',{name:'Commit validated records'})).toBeVisible({timeout:30000});
  await page.getByRole('button',{name:'Commit validated records'}).click();
  const batchId=page.url().split('/').pop()!;
  await expect.poll(async()=>(await stored(page,`imports/${batchId}/`)).status).toBe('completed');
  const batch=await stored(page,`imports/${batchId}/`);
  await page.goto('/programs'); await expect(page.getByRole('link',{name:`QA import ${info.project.name}`,exact:true})).toBeVisible();
  await page.goto('/evidence/new'); const title=`QA card ${info.project.name}`;
  await page.getByLabel('Card title').fill(title); await page.locator('select[name=program_id]').selectOption({label:`QA import ${info.project.name}`});
  await page.getByLabel('Summary',{exact:true}).fill('Synthetic aggregate cohort describes food security; this observation does not establish causation.');
  await page.getByLabel('Implementation steps').fill('Record a fixed cohort and follow up after six months.');
  await page.getByRole('button',{name:'Save private draft'}).click(); await expect(page.getByRole('heading',{name:title})).toBeVisible();
  const cardId=page.url().split('/').pop()!; await submitReview(page);
  const ctx=await browser.newContext(); const reviewer=await ctx.newPage(); await login(reviewer,'reviewer'); await approve(reviewer,title); await ctx.close();
  await page.goto('/sharing'); await page.locator('select[name=source_id]').selectOption({label:filename}); await page.locator('select[name=audience]').selectOption('public');
  await page.getByRole('button',{name:'Grant scoped permission'}).click(); await expect(page.getByText('Saved.',{exact:true})).toBeVisible();
  const donorContext=await browser.newContext(); const donor=await donorContext.newPage(); await login(donor,'foundation-admin');
  await donor.goto(`/evidence/${cardId}`); await expect(donor.getByRole('heading',{name:title})).toBeVisible();
  const sourceRow=page.locator('.source').filter({has:page.getByRole('link',{name:filename,exact:true})});
  await sourceRow.getByText('Withdraw this source',{exact:true}).click(); await sourceRow.getByLabel(`Confirm withdrawal of ${filename}`).fill('WITHDRAW');
  await sourceRow.getByRole('button',{name:'Withdraw source & queue deletion'}).click();
  await expect.poll(async()=>{const ws=await donor.getByLabel('Active workspace').inputValue();return (await donor.request.get(`/api/v1/cards/${cardId}/`,{headers:{'X-Workspace-ID':ws}})).status();}).toBe(404);
  await donor.reload(); await expect(donor.getByRole('alert')).toBeVisible(); await donorContext.close();
  const jobs=await stored(page,'jobs/'); expect(jobs.some((j:{kind:string})=>j.kind==='delete_source')).toBeTruthy();
  expect(batch.source_id || batch.source).toBeTruthy();
});

test('fixed pooled analysis computes from persisted compatible cohort and discloses limits',async({page},info)=>{
  await login(page,'ngo-owner'); await page.goto('/analyses');
  await page.getByLabel('Analysis title').fill(`QA pooled ${info.project.name}`);
  const select=page.getByLabel('Complete outcome & period set');
  await expect(select.locator('option')).not.toHaveCount(1);
  const option=await select.locator('option').filter({hasText:/Synthetic binary indicator:.*2025-01-01/}).first().getAttribute('value');
  expect(option).toBeTruthy(); await select.selectOption(option!);
  await page.getByRole('button',{name:'Calculate pooled draft'}).click();
  await expect(page.getByRole('heading',{name:'Latest calculation'})).toBeVisible();
  const saved=(await stored(page,'analyses/')).find((a:{title:string})=>a.title===`QA pooled ${info.project.name}`);
  expect(saved).toBeTruthy(); expect(saved.payload.status).toBe('draft'); expect(saved.payload.organization_count).toBeGreaterThanOrEqual(3);
  await page.screenshot({path:`docs/screenshots/analysis-${info.project.name}.png`,fullPage:true});
});

test('discovery keyboard, mobile layout, empty state and accessibility',async({page},info)=>{
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  await login(page,'foundation-admin'); await page.goto('/discover');
  await expect(page.locator('.org-card').first()).toBeVisible();
  await page.keyboard.press('Tab'); await expect(page.getByRole('link',{name:'Skip to content'})).toBeFocused();
  await page.keyboard.press('Enter');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  expect(results.violations).toEqual([]);
  await page.screenshot({path:`docs/screenshots/discovery-${info.project.name}.png`,fullPage:true});
  await page.getByLabel('Organization',{exact:true}).fill('No matching fictional organization QA');
  await page.getByRole('button',{name:'Apply filters'}).click();
  await expect(page.getByRole('heading',{name:'No organizations match these filters'})).toBeVisible();
  expect(new URL(page.url()).searchParams.get('q')).toBe('No matching fictional organization QA');expect(errors).toEqual([]);
});
