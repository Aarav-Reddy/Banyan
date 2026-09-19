# Data sources and ingestion

The default demo and tests use project-authored synthetic fixtures, never live APIs. Public-source adapters normalize files; backend services own authorization, quarantine retention, transactional persistence, idempotency, jobs and active filing revision selection. An imported record is not a verified impact finding.

## Interfaces and limits

`philanthra.ingestion.parse_upload(payload, filename, mapping=None)` returns `records`, `diagnostics`, `columns`, `preview`, `kind`, `status`, `checksum`, and `parser_version`. Mapping is `{source_column: normalized_field}`. CSV/XLSX requires explicit mapping of every column; unmapped columns must be removed before upload. Preview contains only normalized accepted fields. Sensitive column names, potential identifiers, formula cells, incompatible fields, invalid dates/counts and invalid monetary precision are rejected. These checks are screening, not proof of de-identification. Owners remain responsible for aggregate-only inputs and review.

Templates are [outcomes.csv](../schemas/imports/outcomes.csv) and [costs.csv](../schemas/imports/costs.csv). Costs retain exact decimal strings. Binary outcomes require explicit definition, direction, cohort/study identity, independence declaration, period and follow-up. Blank numerators/denominators remain null with warnings and cannot support pooling. Supported pilot currencies: USD, EUR, GBP, MXN, ETB, GTQ, CAD, AUD, JPY, CHF. XLSX identifiers should be stored as text: formatting a numeric cell with leading zeroes does not change its underlying identity.

`parse_source(payload, adapter, metadata=None)` returns the same envelope. Adapters: `irs_xml`, `irs_index`, `eo_bmf`, `revocations`, `form990n`, `acs5`, `iati`. Trusted caller metadata carries `source_kind`, `source_url` or `upload_id`, retrieval date and adapter configuration. Default local classification is NGO-contributed, never implicitly public. Preserve raw-file SHA-256 and record locators; a checksum plus parser version supports idempotency, but does not replace database uniqueness constraints. Malformed public-source documents are rejected atomically. Duplicate external record identities are omitted with diagnostics.

`parse_archive(payload, adapter, metadata)` processes safe ZIP members in memory. Limits: 5 MiB input/member, 20 MiB expanded archive, 200 entries, 100:1 expansion, 5,000 table rows, 64 columns, 10,000-character cells. Absolute/traversal paths, links, duplicate ZIP names and encrypted archives fail closed. XLSX macros/external links and formulas are rejected.

Text/PDF reports remain `quarantined`, never structured analytics records. An isolated child extracts page-located text with a 15-second wall limit, 10 CPU seconds, 40 pages, 200,000 text characters and 2 MiB PDF decompression streams. Linux additionally enforces 512 MiB address space; macOS relies on the parser's stream bounds and child timeout. Suspicious extracted text is withheld from preview. Image-only PDFs honestly report unavailable text. Backend must retain raw files privately and only permit manual evidence drafting under review. No OCR or automatic evidence validation is claimed.

`safe_csv()` escapes spreadsheet formulas, including whitespace-prefixed cells and headers. `rejected_csv()` exports row/field/error locations without rejected raw private values.

## Official mappings inspected

IRS uses the namespace `http://www.irs.gov/efile`. Mappings were inspected against actual redacted XSD ZIPs for [2022v5.0](https://www.irs.gov/pub/irs-tege/990x-schema-2022v5-0.zip), [2023v5.1](https://www.irs.gov/pub/irs-tege/990x-schema-2023v5-1.zip), and [2024v5.0](https://www.irs.gov/pub/irs-tege/990x-schema-2024v5.0.zip), discovered through the [official schema listing](https://www.irs.gov/charities-non-profits/tax-exempt-organization-search-teos-schemas). Other versions receive explicit unsupported diagnostics; this is a field-mapping parser, not a full tax-return XSD validator. Synthetic minimal parser fixtures are not complete schema-valid filings.

Full 990 retains current-year revenue/expenses, assets/liabilities/net assets, functional program expenses and its matching total, reported cash/savings and unrestricted net assets when present. Missing is not zero. EZ retains its limited separate financial fields. PF preserves foundation book values, fair-market assets and charitable disbursements separately; those disbursements are not ordinary 990 program expenses. All revision identities contain reporting dates and content checksum; imports do not automatically select active revisions. EIN is always a string. Filing ZIP is headquarters information, not a service area.

The [IRS distribution page](https://www.irs.gov/charities-non-profits/form-990-series-downloads) links official yearly indices and monthly archives. The inspected [2023 index](https://apps.irs.gov/pub/epostcard/990/xml/2023/index_2023.csv) has `RETURN_ID,FILING_TYPE,EIN,TAX_PERIOD,SUB_DATE,TAXPAYER_NAME,RETURN_TYPE,DLN,OBJECT_ID`. Its submission field may be only a year; index year is not tax year. No individual download URL is invented from an object identifier. Import bounded local excerpts/archives when official bulk downloads exceed limits.

[EO BMF dictionary](https://www.irs.gov/pub/irs-soi/eo-info.pdf) defines snapshot identity/status codes; [990-N dictionary](https://www.irs.gov/pub/irs-tege/990n-data-dictionary.pdf) defines the separate 26-field notice layout; [auto-revocation dictionary](https://www.irs.gov/pub/irs-tege/auto-revocation-data-dictionary.pdf) defines the separate 12-field event layout. Revocations are not bankruptcy labels. Both raw and corrected effective dates are preserved for the IRS-documented April–July 2020 date exception. No status parser certifies present deductibility. Principal officer fields from 990-N are deliberately not copied into normalized records.

ACS5 supports the inspected 2023 poverty table: [B17001 variables](https://api.census.gov/data/2023/acs/acs5/groups/B17001.html), [supported geography definitions](https://api.census.gov/data/2023/acs/acs5/geography.html), [annotation handling](https://www.census.gov/data/developers/data-sets/acs-1year/notes-on-acs-api-variable-types.html). `snapshot_year=2023` and `geography_type=state|county|tract|zcta` are explicit metadata. B17001_002E/M are below-poverty estimate/MOE; B17001_001E/M are the corresponding poverty-universe denominator/MOE. Preserve 2019–2023 coverage, boundary/crosswalk vintage, raw sentinel and annotations. No poverty percentage MOE is invented. Poverty is a contextual proxy, not a direct food-insecurity measure. Never substitute counties for ZIP measurements or equate USPS ZIP with Census ZCTA.

**Observed external blocker, 2026-09-19:** the official 2023 ACS Baltimore city (Maryland state 24, county 510) request returned HTTP 302 to `/data/missing_key.html` with `X-DataWebAPI-KeyError: 1`. No authentic observation was fabricated. The included ACS fixture is synthetic. A real snapshot requires authorized API access or an official bounded local extract with its manifest. The map must present real county metrics as unavailable until such a source is imported.

[IATI 2.03](https://iatistandard.org/en/iati-standard/203/activity-standard/) normalization keeps identity, organization roles, countries/sectors with vocabulary codes, document references, budgets, planned disbursements and transactions separately. Targets and actuals remain separate with periods, dimensions and locations. Transaction types are preserved; no commitments/disbursements are summed together, and repeated explicit transaction references fail validation. Reports remain source-reported and unreviewed. Remote document links are reference data and are never fetched by the parser.

## Opt-in network and local commands

From repository root, with the project virtual environment installed:

```sh
PYTHONPATH=apps/api .venv/bin/python -m philanthra.ingestion --adapter irs_xml --local data/fixtures/ingestion/irs_990_2024.xml --metadata data/fixtures/ingestion/manifest.json
PYTHONPATH=apps/api .venv/bin/python -m philanthra.ingestion --adapter irs_index --source irs_index_2023 --allow-network
```

The second command may report `source_too_large`; that is intentional, not a full-archive setup step. Network retrieval is separately enabled, exact-catalog HTTPS only, DNS checked for globally routable addresses and pinned for TLS connection, no redirects, cookies, credentials, proxy inheritance or automatic arbitrary URL following. Responses are size/time bounded. New catalog entries require source inspection and code review. Private/metadata destinations and DNS rebinding are denied. Source unavailability never blocks local fixtures. Candid and other commercial APIs are unavailable without separately authorized credentials/licenses; there is no scraping fallback.

Manual registry/grant data should enter through reviewed application editors with source records, not through an unsupported financial adapter. Annual reports use the document quarantine/manual drafting path. Extensions must add an explicit parser, mappings, fixtures, diagnostics and permission-aware backend service; they do not bypass consent or review.

## Fixture provenance and licensing

[Fixture manifest](../data/fixtures/ingestion/manifest.json) records SHA-256 for every synthetic fixture, source schema references and the absence of real source URLs. Parser-only EIN `000000001` must never be seeded into directory organizations. Synthetic ACS values attached to geographic test codes are not live public measurements and must remain labeled synthetic.

IRS content reuse is subject to the [IRS reuse policy](https://www.irs.gov/about-irs/use-of-content-from-irsgov); third-party material is not automatically public domain. [Census policy](https://www2.census.gov/foia/ds_policies/ds027.pdf) discusses government-created works. [IATI licensing](https://web-terms.iatistandard.org/en/latest/copyright/) separates documentation/software from publisher-owned data: inspect each publisher's actual license before redistribution. No third-party raw IATI activity is bundled here. Preserve original public snapshots unchanged, add source URL/retrieval/license/checksum manifests, and keep public fixtures separate from synthetic fixtures and private uploads.
