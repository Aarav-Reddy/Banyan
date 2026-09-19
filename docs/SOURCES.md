# Implementation sources

Official documentation inspected during build (2026-09-19). Retrieved timestamps do not stand in for dataset reporting periods.

- [Django 5.2 release notes](https://docs.djangoproject.com/en/5.2/releases/) — supported LTS patches and compatibility.
- [Next.js installation](https://nextjs.org/docs/app/getting-started/installation) — App Router and supported runtime.
- [Codex custom subagents](https://developers.openai.com/es-419/docs/agent-configuration/subagents) — standalone TOML definitions; current English URL returned 404, localized official page inspected.
- Original proposal's source index remains intact in `docs/source-materials/ORIGINAL_PROPOSAL.md`. Statistics in it are historical proposal content, not validated product claims.

Additional primary references inspected for implementation:

- [IRS exempt-organization bulk data](https://www.irs.gov/charities-non-profits/form-990-series-downloads) and inspected [2022 schema archive](https://www.irs.gov/pub/irs-tege/990x-schema-2022v5-0.zip), [2023 schema archive](https://www.irs.gov/pub/irs-tege/990x-schema-2023v5-1.zip), [2024 schema archive](https://www.irs.gov/pub/irs-tege/990x-schema-2024v5.0.zip). Exact supported mappings are in schemas/mappings/irs.json; fixture provenance is in data/fixtures/ingestion/manifest.json.
- [IRS EO BMF extract](https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf) and [TEOS](https://www.irs.gov/charities-non-profits/tax-exempt-organization-search) — status provenance does not certify solvency or deductibility.
- [ACS 2023 five-year B17001 variables](https://api.census.gov/data/2023/acs/acs5/groups/B17001.html) — estimate/MOE/denominator mappings, supported geography distinctions.
- [Census QuickFacts Baltimore city](https://www.census.gov/quickfacts/fact/table/baltimorecitymaryland/PST045225) — manually verified 2020–2024 city-wide income/connectivity extract, stored separately from synthetic data. No ZIP measurement or estimated uncertainty is invented.
- [IATI 2.03 activity standard](https://iatistandard.org/en/iati-standard/203/activity-standard/) — reporting organizations, participating organizations, countries/sectors, budgets, transactions, links and target/actual results.
- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs/) and [Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create/) — server-only typed explanation boundary, store=false and no tools. Optional live operation was not exercised.

Installed Next.js documentation/types were inspected for agentRules and proxy configuration. The exact dependency/image environment and observed network audit results are recorded in BUILD_STATUS.md and lockfiles; external documentation availability is not evidence of a working integration.
