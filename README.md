# Philanthra

# **Impact Commons**

### *The intelligence layer that tells philanthropy where to fund—and helps nonprofits learn from everything the sector has already discovered.*

## Startup proposal

Philanthropy generates enormous amounts of financial, operational, and program data, yet most of that information remains fragmented across tax filings, grant reports, monitoring systems, spreadsheets, and individual NGOs. As a result, donors struggle to identify effective but overlooked organizations, while NGOs repeatedly solve the same problems without access to lessons already learned elsewhere.

**Impact Commons** would be a shared data and intelligence platform for the philanthropic sector. It would combine public nonprofit records with voluntarily contributed, privacy-protected program data from NGOs around the world. From the same underlying data infrastructure, the platform would produce two connected products:

1. **A philanthropic capital-allocation engine** that helps donors identify which organizations are best positioned to use additional funding.
2. **A nonprofit knowledge engine** that finds useful interventions, patterns, and lessons across organizations and proactively delivers them to NGOs that could benefit.

The unifying idea is simple:

> **Every philanthropic dollar should benefit from everything philanthropy has already learned.**

---

## The problem

### 1. Donors cannot easily identify overlooked organizations

Much of nonprofit discovery still depends on brand recognition, personal networks, polished grant applications, or simplistic charity ratings. Small local organizations may have strong operations and deep community knowledge but lack the fundraising staff or visibility of larger organizations.

The underlying financial data already exist. Most U.S. tax-exempt organizations file a Form 990-series return, although the level of information varies by filing type and some organizations are exempt. The IRS makes recent electronically filed 990-series returns downloadable in bulk XML, while its broader tax-exempt datasets are updated monthly. Full Form 990 filings contain information about program accomplishments, functional expenses, revenue, assets, liabilities, governance, and compensation. ([IRS][1])

Impact Commons would transform these raw filings into practical donor questions:

* Which small organizations working on food insecurity within this ZIP code appear capable of using another $50,000 effectively?
* Which organizations devote a strong proportion of spending to programs while remaining financially stable?
* Which organizations serve high-need communities but receive relatively little philanthropic funding?
* Which organizations show warning signs of financial distress?
* Where are multiple funders financing duplicate work while another neighborhood remains underserved?

Longitudinal nonprofit financial data can reveal genuine vulnerability. An Urban Institute analysis using IRS tax data identified signals such as declining net income, cash shortages, revenue disruptions, high leverage, and insolvency among some community-based organizations. ([Urban Institute][2])

Impact Commons would therefore build an explainable **Financial Resilience and Distress Model** using indicators such as:

* Repeated operating deficits
* Declining unrestricted assets or estimated cash reserves
* Revenue volatility and dependence on one funding source
* Liabilities relative to assets
* Sudden reductions in program spending
* Rapid expense growth unsupported by revenue
* Missing or delayed filings
* Abrupt changes in staffing or executive compensation
* Several years of shrinking program activity

The system would report a probabilistic **financial-distress risk**, not declare that an organization will collapse.

Program spending per dollar would also remain one input rather than the entire ranking. A low-overhead organization is not automatically effective, and an organization investing in technology, evaluation, safeguarding, or staff may appear less “efficient” while producing better outcomes. Impact Commons would combine financial efficiency with evidence quality, local need, organizational resilience, outcome data, and the organization’s ability to absorb additional funding.

---

### 2. NGOs repeatedly rediscover knowledge that already exists elsewhere

Every philanthropic NGO holds information that may be valuable to other NGOs:

* An intervention that worked
* An intervention that failed
* The cost of serving a particular population
* Operational barriers encountered in the field
* Beneficiary response patterns
* Implementation manuals and staff training methods
* Relationships between socioeconomic characteristics and program outcomes
* Contextual conditions under which an intervention succeeded

Today, much of this information stays inside individual organizations or is buried in reports that are difficult to compare.

For example:

* An NGO in Ethiopia may have developed a successful method of reducing childhood malnutrition through a particular combination of community health workers, fortified foods, parental education, and follow-up. An NGO confronting similar malnutrition in Mexico might benefit from that solution, provided the system identifies which elements are transferable and which require local adaptation.
* NGO A may have records comparing direct monetary assistance with infrastructure or employment opportunities for households in a particular income category. Its dataset alone may be too small to show a reliable pattern. When combined with compatible data from NGOs B, C, and D, a clearer result may emerge: under certain local conditions, infrastructure or income-generating opportunities appear to produce more durable outcomes than direct transfers.
* Several organizations may independently discover that a program works only when delivered through trusted local institutions, but none may recognize the wider pattern until their data are analyzed together.

International infrastructure already proves that standardized philanthropic data can be shared at scale. As displayed in September 2026, the International Aid Transparency Initiative reported more than one million development and humanitarian activities from 1,846 publishers and provides its data through CSV, JSON, XML, and an API. ([IATI Standard][3])

Impact Commons would go beyond publishing and searching that information. It would analyze it, connect it to outcome data, and actively tell an organization:

> “Three programs serving populations similar to yours tested approaches to this problem. This intervention produced the strongest results under comparable conditions. Here is the evidence, implementation method, estimated cost, uncertainty, and contact information for the organizations involved.”

---

## The product

### A shared philanthropy knowledge graph

Impact Commons would organize sector data into a common structure:

**Organization → Program → Problem → Intervention → Population → Geography → Cost → Outcome → Evidence → Funder**

The platform would ingest four categories of information.

### Public organizational data

* IRS Form 990-series filings
* Tax-exempt status and revocation records
* Government charity registries
* Published annual reports
* Audited financial statements
* Public grant records
* IATI development and humanitarian data
* Public demographic, health, economic, and geographic indicators

Candid already demonstrates the scale of the available philanthropic information landscape. It reports data on approximately 1.9 million organizations, three million annual grant transactions, and $180 billion in annual grant dollars. It also provides compliance, grants, nonprofit, taxonomy, and other APIs. ([Candid][4])

### Private NGO program data

Participating NGOs could securely contribute:

* Program costs
* Beneficiary characteristics in de-identified form
* Intervention details
* Outputs and outcomes
* Follow-up periods
* Survey results
* Qualitative field notes
* Project reports
* Implementation guides
* Failed or discontinued approaches
* Contextual limitations

The platform would accept spreadsheets, monitoring-and-evaluation exports, reports, surveys, and connections to commonly used nonprofit systems.

### Contextual data

To prevent false comparisons, each intervention would be linked to contextual variables such as:

* Local income and cost of living
* Rural or urban setting
* Population density
* Existing infrastructure
* Public-service availability
* Age and demographic characteristics
* Cultural and linguistic context
* Political stability
* Climate and geography
* Delivery partner type
* Program duration
* Funding level

### Evidence classifications

Each conclusion would clearly state whether it represents:

* A descriptive observation
* A correlation
* A quasi-experimental finding
* A randomized evaluation
* A repeated pattern across organizations
* An expert-reviewed operational lesson
* An early hypothesis requiring further testing

This is essential. Combining several weak observational datasets does not automatically establish causation.

---

## The two principal interfaces

### 1. Donor and foundation interface

A donor could enter:

* Cause area
* Location or ZIP code
* Donation amount
* Target population
* Preferred organization size
* Risk tolerance
* Desired outcome
* Time horizon

The platform would return a transparent portfolio of organizations rather than a single opaque score.

Each recommendation would include:

* Program-spending information
* Evidence of outcomes
* Financial-health trends
* Community need
* Existing funding concentration
* Organizational capacity
* Distress warnings
* Confidence level
* Reasons for the recommendation
* Missing information that could alter the result

A donor might receive:

> **Recommended local portfolio: $100,000**
> $40,000 to a financially stable youth-employment nonprofit with strong outcomes but limited unrestricted funding;
> $35,000 to a smaller food-access organization serving an underfunded ZIP code;
> $25,000 as a capacity-building grant to an effective organization whose growth is constrained by data and staffing systems.

Foundations could additionally monitor an entire portfolio for:

* Emerging grantee distress
* Geographic funding gaps
* Duplication between programs
* Organizations ready to scale
* Opportunities for collaboration
* Causes or populations receiving disproportionately little funding

### 2. NGO intelligence interface

Each NGO would receive a private dashboard containing:

* Benchmarks against comparable organizations
* Relevant interventions tested elsewhere
* Emerging trends from pooled data
* Potential collaborators
* Funding opportunities aligned with its work
* Financial-resilience warnings
* Recommendations for collecting better outcome data
* Transferable implementation guides
* Questions worth testing in its next program cycle

Rather than forcing staff to search a database, the system would proactively route findings to organizations most likely to use them.

An alert could say:

> “Your organization is planning a childhood-malnutrition program in southern Mexico. A program in Ethiopia and two programs in Guatemala used comparable community-delivery models. The strongest common result involved fortnightly household follow-up combined with locally sourced nutrient supplementation. The evidence is moderately transferable, although food availability and healthcare access differ in your target area.”

---

## Why NGOs would contribute data

The platform cannot rely on altruism alone. NGOs need a direct reason to participate.

Contributing organizations would receive:

* Free core benchmarking and insight tools
* Access to lessons contributed by other organizations
* Data cleaning and standardization support
* Stronger impact reports for funders
* Automated grant-reporting assistance
* Identification of compatible funders
* Earlier warnings about financial vulnerability
* Recognition and attribution when their methods inform other programs
* Optional introductions to organizations adopting their approach
* Greater visibility to donors without paying for placement

NGOs would retain ownership of their data. Impact Commons would receive only the rights needed to conduct agreed analysis. It would not sell identifiable beneficiary information, and an organization could define which analyses, geographies, users, or cause areas its information may support.

Funders could sponsor data preparation for their grantees, solving a major practical problem: many small NGOs possess valuable information but lack dedicated data staff.

---

## Privacy and governance

The platform would begin with organizational, program-level, and aggregated data—not raw beneficiary records.

Safeguards would include:

* De-identification and aggregation before ingestion
* Collection of only information necessary for defined analyses
* Role-based access controls
* Encryption in transit and at rest
* Clear data-use agreements
* Audit logs showing how information was used
* NGO-controlled permissions
* Suppression of results based on very small populations
* Independent review of high-risk analyses
* Human review before consequential donor or program recommendations
* A governance council representing NGOs, funders, data experts, and affected communities

For especially sensitive datasets, later versions could use secure data enclaves or federated analysis, allowing models to examine patterns without transferring raw records from the NGO’s environment.

The platform must also prevent extractive data relationships. Organizations and communities generating the data should receive useful intelligence in return, not simply supply information that wealthy funders control.

---

## Business model

Impact Commons would be structured as a philanthropy-focused B2B platform with a data-cooperative component.

### Paying customers

* Private and family foundations
* Community foundations
* Corporate-philanthropy teams
* Donor-advised-fund providers
* Institutional donors
* Philanthropic advisers
* Government and multilateral grantmakers
* Large international NGO networks
* Donation and grant-management platforms

### Revenue streams

* Annual foundation subscriptions
* Portfolio-monitoring subscriptions
* Enterprise data integrations
* API access for giving and grant-management platforms
* Sponsored NGO data onboarding
* Custom cause-area or geographic analysis
* White-label donor-discovery tools
* Research partnerships and sector reports

The platform should not charge organizations to improve their ranking and should not accept a percentage of donations it recommends. Those models would create direct conflicts of interest.

A free or heavily subsidized contributor tier would allow small NGOs to participate. Foundations would pay for the more valuable capital-allocation, portfolio-monitoring, and sector-analysis products.

---

## Competitive position

Existing systems cover pieces of the problem:

* **IRS data** provide raw nonprofit financial and organizational records.
* **Candid** organizes nonprofit, compliance, grant, and funder information.
* **IATI** standardizes and distributes international development and humanitarian activity data.
* **GiveWell and similar evaluators** conduct intensive cost-effectiveness analysis for selected interventions and funding opportunities. GiveWell, for example, explicitly compares opportunities against a cost-effectiveness benchmark. ([GiveWell][5])

Impact Commons would not simply reproduce these services. Its distinct role would be to connect:

1. **Where philanthropic money currently goes**
2. **Which organizations appear financially capable of using more**
3. **What interventions they have attempted**
4. **Which outcomes followed**
5. **Which lessons are transferable to another organization**
6. **Where additional philanthropic capital could produce the greatest marginal benefit**

Based on their public product descriptions, existing platforms provide important data, search, evaluation, or transparency functions, but the proposed differentiation is a continuously learning, cross-NGO recommendation system that serves both funders and nonprofit operators. ([IATI Standard][3])

---

## Initial MVP

The first version should be deliberately narrow.

### Pilot market

Begin with:

* One metropolitan area
* One philanthropic cause, such as food security, childhood nutrition, housing stability, or youth employment
* One local foundation or donor network
* Approximately 15–25 participating nonprofits

### MVP functions

1. Ingest several years of Form 990 data.
2. Map nonprofits by ZIP code, cause, size, program spending, and financial health.
3. Combine those records with neighborhood-level need indicators.
4. Allow participating NGOs to upload de-identified program and outcome data.
5. Produce standardized “intervention cards” explaining what was attempted, for whom, at what cost, and with what result.
6. Recommend overlooked organizations to participating donors.
7. Alert NGOs to relevant findings from peer organizations.
8. Test the financial-distress model against historical outcomes.
9. Have philanthropic and nonprofit experts review every recommendation during the pilot.

### Pilot success metrics

* Percentage of recommended grants going to previously overlooked organizations
* Additional funding reaching high-need ZIP codes
* Donor research time saved
* Accuracy and usefulness of financial-risk alerts
* Number of cross-NGO insights adopted
* Improvement in participating NGOs’ data quality
* Program costs avoided by reusing an existing solution
* Measurable outcome improvements after an NGO adopts a recommendation
* Percentage of participating NGOs that continue sharing data

After proving the model locally, the platform could expand nationally through IRS data and internationally through IATI, NGO consortiums, and country-specific charity registries.

---

## Why this is fundamentally a philanthropy startup

Impact Commons is not merely generic analytics software sold to nonprofits. Its central purpose is to improve how philanthropic knowledge and capital move through the sector.

It would help philanthropy answer both of its hardest questions:

> **Where should we give?**

and

> **What should the organizations we fund know before they act?**

By connecting donor allocation, nonprofit resilience, operational learning, and global knowledge transfer in one platform, Impact Commons would turn fragmented charitable data into shared infrastructure for more effective philanthropy.

## One-paragraph competition version

**Impact Commons is a shared intelligence platform for philanthropy that combines public nonprofit financial records with privacy-protected program data contributed by NGOs. Its donor engine uses Form 990 data, local-need indicators, outcome evidence, and explainable financial-risk models to identify overlooked organizations capable of using additional funding—including small nonprofits within a donor’s chosen ZIP code. Its NGO engine analyzes interventions and outcomes across organizations globally, allowing a malnutrition solution developed in Ethiopia to inform a program in Mexico or revealing patterns that become visible only when the datasets of several NGOs are combined. The same knowledge graph therefore tells donors where capital may have the greatest marginal value and tells nonprofits what the sector has already learned, while preserving NGO data ownership, beneficiary privacy, and human oversight.**

[1]: https://www.irs.gov/charities-non-profits/form-990-series-downloads "Form 990 series downloads | Internal Revenue Service"
[2]: https://www.urban.org/research/publication/financial-health-community-based-development-organizations-using-IRS?utm_source=chatgpt.com "The Financial Health of Community-Based Development Organizations: Using Internal Revenue Service Tax Data to Assess Sector Health | Urban Institute"
[3]: https://iatistandard.org/en/ "International Aid Transparency Initiative - iatistandard.org"
[4]: https://candid.org/use-our-data/ "Custom datasets and custom datasets | Candid"
[5]: https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness/cost-effectiveness-models?utm_source=chatgpt.com "GiveWell's Cost-Effectiveness Analyses"
