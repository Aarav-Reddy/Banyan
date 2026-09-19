import { test, expect, Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// Real isolated PostgreSQL, API and worker are supplied by playwright.config.ts.
// Only external network destinations are blocked; backend responses are never mocked.
test.beforeEach(async ({ context }) => {
  await context.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (["127.0.0.1", "localhost"].includes(url.hostname))
      await route.continue();
    else await route.abort("internetdisconnected");
  });
});
async function login(page: Page, username: string) {
  await page.goto("/login");
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Demo-only-Philanthra-2026!");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
}
async function stored(page: Page, path: string) {
  const workspace = await page.getByLabel("Active workspace").inputValue();
  const response = await page.request.get("/api/v1/" + path, {
    headers: { "X-Workspace-ID": workspace },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json()).data;
}
async function noOverflow(page: Page) {
  const layout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    documentWidth: document.documentElement.scrollWidth,
    fontSize: getComputedStyle(document.body).fontSize,
    outside: [...document.querySelectorAll("body *")]
      .filter(
        (el) =>
          !el.closest(".table-wrap") &&
          el.getBoundingClientRect().right > window.innerWidth + 1,
      )
      .slice(0, 8)
      .map((el) => ({
        tag: el.tagName,
        class: el.className,
        right: el.getBoundingClientRect().right,
      })),
  }));
  expect(
    layout.documentWidth,
    `${page.url()} ${JSON.stringify(layout)}`,
  ).toBeLessThanOrEqual(layout.viewport);
}
async function accessible(page: Page) {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(result.violations).toEqual([]);
}

test("advanced filters stay mounted, retain values, and submit the original exact query", async ({
  page,
}) => {
  await login(page, "foundation-admin");
  await page.goto("/discover");
  await expect(page.locator(".org-card").first()).toBeVisible();
  const advanced = page.locator("details.advanced-filters");
  await advanced.locator("summary").click();
  await page
    .getByLabel("Organization", { exact: true })
    .fill("Synthetic filter parity");
  await page
    .getByRole("combobox", { name: "Cause", exact: true })
    .selectOption("food_security");
  const area = await page
    .getByRole("combobox", { name: "Service area", exact: true })
    .locator("option")
    .nth(1)
    .getAttribute("value");
  expect(area).toBeTruthy();
  await page
    .getByRole("combobox", { name: "Service area", exact: true })
    .selectOption(area!);
  await page.getByLabel("Population", { exact: true }).fill("households");
  await page
    .getByRole("combobox", { name: "Annual revenue", exact: true })
    .selectOption("small");
  await page.getByLabel("Planning budget (USD)").fill("100.01");
  await page
    .getByLabel("Financial preference")
    .selectOption("capacity_building");
  await page.getByLabel("Desired outcome code").fill("food_security_improved");
  await page.getByLabel("Maximum follow-up (days)").fill("180");
  await expect(advanced.locator("summary")).toContainText(
    "6 additional filters set",
  );
  await advanced.locator("summary").click();
  await expect(advanced).not.toHaveAttribute("open");
  await expect(page.getByLabel("Population", { exact: true })).toHaveValue(
    "households",
  );
  await page
    .getByRole("button", { name: "Apply filters", exact: true })
    .click();
  await expect(page).toHaveURL(/budget_cents=10001/);
  expect(Object.fromEntries(new URL(page.url()).searchParams)).toEqual({
    q: "Synthetic filter parity",
    cause: "food_security",
    location: area,
    population: "households",
    size: "small",
    risk: "capacity_building",
    outcome_definition: "food_security_improved",
    horizon_days: "180",
    budget_cents: "10001",
  });
  await page.reload();
  await expect(advanced.locator("summary")).toContainText(
    "6 additional filters set",
  );
  await advanced.locator("summary").click();
  await expect(page.getByLabel("Planning budget (USD)")).toHaveValue("100.01");
  await page.getByLabel("Planning budget (USD)").fill("0.001");
  await advanced.locator("summary").click();
  await page
    .getByRole("button", { name: "Apply filters", exact: true })
    .click();
  await expect(page.locator(".filter-panel").getByRole("alert")).toBeVisible();
  await expect(advanced).toHaveAttribute("open", "");
  await expect(page.getByLabel("Planning budget (USD)")).toBeFocused();
  await expect(page.getByLabel("Organization", { exact: true })).toHaveValue(
    "Synthetic filter parity",
  );
  await expect(page.getByLabel("Planning budget (USD)")).toHaveValue("0.001");
  expect(new URL(page.url()).searchParams.get("budget_cents")).toBe("10001");
});

test("renamed navigation retains role destinations and mobile focus returns on close", async ({
  page,
}, info) => {
  const shared = {
    "Evidence library": "/evidence",
    "Saved evidence": "/saved",
    "Combined analysis": "/analyses",
    Connections: "/graph",
    Watchlist: "/watchlist",
    Alerts: "/alerts",
  };
  const funding = {
    Organizations: "/discover",
    "Funding plans": "/portfolios",
    "Plan funding": "/allocate",
  };
  const nonprofit = {
    Overview: "/dashboard",
    Programs: "/programs",
    "Data uploads": "/uploads",
    "Impact report": "/impact-report",
    "Funding opportunities": "/opportunities",
  };
  for (const [username, specific] of [
    ["foundation-admin", funding],
    ["foundation-viewer", funding],
    ["ngo-owner", nonprofit],
    ["ngo-viewer", nonprofit],
    ["reviewer", { ...funding, Reviews: "/reviews" }],
    ["platform-admin", funding],
  ] as const) {
    await login(page, username);
    if (info.project.name === "mobile") {
      const open = page.getByRole("button", {
        name: "Open navigation",
        exact: true,
      });
      await open.click();
      await expect(page.locator(".mobile-menu")).toHaveAttribute(
        "aria-expanded",
        "true",
      );
      await expect(page.locator(".mobile-close")).toBeFocused();
    }
    const nav = page.getByRole("navigation", { name: "Main navigation" });
    for (const [name, href] of Object.entries({ ...shared, ...specific })) {
      const link = nav.getByRole("link", { name, exact: true });
      await expect(link).toHaveAttribute("href", href);
      await expect(link).toBeVisible();
    }
    for (const [name, href] of Object.entries({
      "Sharing & privacy": "/sharing",
      Settings: "/settings",
      Methodology: "/methodology",
    }))
      await expect(
        page
          .getByRole("navigation", { name: "Workspace utilities" })
          .getByRole("link", { name, exact: true }),
      ).toHaveAttribute("href", href);
    if (info.project.name === "mobile") {
      await page.keyboard.press("Escape");
      await expect(
        page.getByRole("button", { name: "Open navigation", exact: true }),
      ).toBeFocused();
      await expect(page.locator(".mobile-menu")).toHaveAttribute(
        "aria-expanded",
        "false",
      );
      await page
        .getByRole("button", { name: "Open navigation", exact: true })
        .click();
      await page.locator(".mobile-close").click();
      await expect(
        page.getByRole("button", { name: "Open navigation", exact: true }),
      ).toBeFocused();
    }
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(
      page.getByRole("button", { name: "Sign in", exact: true }),
    ).toBeVisible();
  }
});

test("reports lead with allocations and preserve source and technical content in print", async ({
  page,
}) => {
  await login(page, "foundation-admin");
  const records = await stored(page, "portfolios/");
  const plan = records.find(
    (p: { title: string }) => p.title === "Neighborhood food access",
  );
  expect(plan).toBeTruthy();
  await page.goto(`/reports/${plan.id}`);
  await expect(
    page.getByRole("heading", { name: "Funding allocation", exact: true }),
  ).toBeVisible();
  const table = page.getByRole("region", { name: "Funding allocation table" });
  const constraints = page.getByText(
    "View all planning inputs and candidate constraints",
    { exact: true },
  );
  expect(
    await table.evaluate(
      (element) =>
        !!(
          element.compareDocumentPosition(
            [...document.querySelectorAll("summary")].find(
              (s) =>
                s.textContent ===
                "View all planning inputs and candidate constraints",
            )!,
          ) & Node.DOCUMENT_POSITION_FOLLOWING
        ),
    ),
  ).toBe(true);
  const technical = page.getByText(
    "Complete report data and technical details",
    { exact: true },
  );
  await technical.click();
  await expect(
    page
      .locator(".report-technical")
      .last()
      .locator('dt[title="policy_version"]'),
  ).toBeVisible();
  const sources = page.locator("details").filter({
    has: page.locator("summary", { hasText: /^Sources & provenance/ }),
  });
  await sources.locator("summary").click();
  await expect(sources.locator("a").first()).toHaveAttribute(
    "href",
    /^\/sources\//,
  );
  await expect(sources.locator(".checksum").first()).toBeVisible();
  await sources.locator("summary").click();
  const initial = await page
    .locator("main details")
    .evaluateAll((elements) =>
      elements.map((el) => (el as HTMLDetailsElement).open),
    );
  await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
  await page.emulateMedia({ media: "print" });
  expect(
    await page
      .locator("main details")
      .evaluateAll((elements) =>
        elements.every((el) => (el as HTMLDetailsElement).open),
      ),
  ).toBe(true);
  await expect(table).toBeVisible();
  await expect(sources.locator(".checksum").first()).toBeVisible();
  await expect(
    page
      .locator(".report-technical")
      .last()
      .locator('dt[title="policy_version"]'),
  ).toBeVisible();
  await page.emulateMedia({ media: "screen" });
  await page.evaluate(() => window.dispatchEvent(new Event("afterprint")));
  expect(
    await page
      .locator("main details")
      .evaluateAll((elements) =>
        elements.map((el) => (el as HTMLDetailsElement).open),
      ),
  ).toEqual(initial);
  await accessible(page);
});

test("public, editor and assigned review surfaces pass installed WCAG checks", async ({
  page,
  browser,
}, info) => {
  await page.goto("/");
  await expect(page.locator("h1")).toBeVisible();
  await accessible(page);
  await page.goto("/login");
  await expect(page.getByLabel("Username", { exact: true })).toBeVisible();
  await accessible(page);
  await login(page, "ngo-owner");
  await page.goto("/programs/new");
  await expect(
    page.getByRole("button", { name: "Create program", exact: true }),
  ).toBeVisible();
  await accessible(page);
  await page.getByRole("button", { name: "Sign out" }).click();
  await login(page, "foundation-admin");
  const plans = await stored(page, "portfolios/");
  const title =
    info.project.name === "desktop"
      ? "Neighborhood food access"
      : "Small grant, known caps";
  const plan = plans.find((p: { title: string }) => p.title === title);
  await page.goto(`/portfolios/${plan.id}`);
  await page.getByText(/^Submit revision \d+ for review$/).click();
  await page
    .getByLabel("Assigned reviewer")
    .selectOption({ label: "reviewer" });
  await page
    .getByRole("button", { name: "Submit for review", exact: true })
    .click();
  await expect(
    page.getByText("Pending review", { exact: true }).first(),
  ).toBeVisible();
  const context = await browser.newContext({ viewport: page.viewportSize()! });
  const reviewer = await context.newPage();
  await login(reviewer, "reviewer");
  await reviewer.goto("/reviews");
  await expect(
    reviewer.getByRole("heading", { name: title, exact: true }),
  ).toBeVisible();
  await expect(
    reviewer.getByLabel("Reason, scope & caveats").first(),
  ).toBeVisible();
  await accessible(reviewer);
  await context.close();
});

test("representative screens reflow at required widths and enlarged text", async ({
  page,
}, info) => {
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  const widths =
    info.project.name === "desktop" ? [320, 390, 768, 1024, 1440] : [390];
  await login(page, "ngo-owner");
  const paths = [
    "/",
    "/dashboard",
    "/programs/new",
    "/uploads",
    "/analyses",
    "/impact-report",
    "/settings",
    "/graph",
  ];
  for (const path of paths) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    await expect(
      page.getByText("Loading workspace records…", { exact: true }),
    ).toHaveCount(0);
    for (const width of widths) {
      await page.setViewportSize({ width, height: 1000 });
      await noOverflow(page);
    }
    await page.setViewportSize({ width: 1024, height: 1000 });
    const textSizes = await page.evaluate(() => {
      const control = document.querySelector("input, select, button, .button")!;
      const before = [document.body, control].map((element) =>
        parseFloat(getComputedStyle(element).fontSize),
      );
      document.documentElement.style.fontSize = "200%";
      const after = [document.body, control].map((element) =>
        parseFloat(getComputedStyle(element).fontSize),
      );
      return { before, after };
    });
    textSizes.after.forEach((size, index) =>
      expect(size / textSizes.before[index]).toBeGreaterThan(1.9),
    );
    await noOverflow(page);
    await page.setViewportSize({ width: 320, height: 1000 });
    await noOverflow(page);
  }
  await page.getByRole("button", { name: "Sign out" }).click();
  await login(page, "foundation-admin");
  for (const path of ["/discover", "/allocate", "/portfolios"]) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    await expect(
      page.getByText("Loading workspace records…", { exact: true }),
    ).toHaveCount(0);
    for (const width of widths) {
      await page.setViewportSize({ width, height: 1000 });
      await noOverflow(page);
    }
    await page.setViewportSize({ width: 1024, height: 1000 });
    const textSizes = await page.evaluate(() => {
      const control = document.querySelector("input, select, button, .button")!;
      const before = [document.body, control].map((element) =>
        parseFloat(getComputedStyle(element).fontSize),
      );
      document.documentElement.style.fontSize = "200%";
      const after = [document.body, control].map((element) =>
        parseFloat(getComputedStyle(element).fontSize),
      );
      return { before, after };
    });
    textSizes.after.forEach((size, index) =>
      expect(size / textSizes.before[index]).toBeGreaterThan(1.9),
    );
    await noOverflow(page);
    await page.setViewportSize({ width: 320, height: 1000 });
    await noOverflow(page);
  }
  expect(errors).toEqual([]);
});
