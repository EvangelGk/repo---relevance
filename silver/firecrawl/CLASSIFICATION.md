# Firecrawl extractor classification

New file, 2026-09-08, added as part of the source-first restructure
(`silver/apify/`, `silver/prospeo/`, `silver/company/`, `silver/people/`).
Does not touch any existing file. Confirms: all 14 live extractors +
`conflict_check` are **company-scoped** - Firecrawl only ever processes
company-website markdown in this repo, never a person row, so there is no
ambiguity to resolve here.

| Extractor | Backs | Note |
|---|---|---|
| `domain_normalize` | `company.domain` (**required**) | join key; `context["source_url"]`-only |
| `company_entity_resolve` | `company.company_id` (**required**) | canonical entity key; reads `domain_normalize` + `legal_entity_extract` |
| `company_description_extract` | `company.description` | prefers `context["company_description"]` override, else first prose paragraph |
| `legal_entity_extract` | secondary | legal name + copyright year |
| `social_links_extract` | secondary | linkedin/twitter/crunchbase/g2/capterra/youtube URLs found on-page |
| `business_model` | secondary | {pricing, offering, delivery} enums |
| `site_locale_detect` | secondary | markdown-only since 2026-09-08 |
| `pricing_locale_extract` | secondary | currency/plan-tier signals |
| `careers_page_parse` | secondary | job postings array, strict-then-loose parse |
| `tech_stack_normalize` | secondary | `detected_stack` (context) + `mentioned_technologies` (markdown, ~75-vendor catalog) |
| `date_normalize` | secondary | any ISO/slash/named-month date found on-page |
| `compliance_framework_extract` | secondary | framework codes (ISO27001/SOC2/HIPAA/...); people-side analog: `apify/people/secondary/datapoints/person_certifications.py` |
| `experience_signal_extract` | secondary | founding-year/tenure *claims* from prose; no people-side clone - see `apify/people/secondary/README.md` Task 4 decision #2 |
| `service_region_extract` | secondary | place strings found on-page; no people-side analog - see `apify/people/secondary/README.md` Task 4 decision #3 |
| `conflict_check` | QA cross-check, not a datapoint | runs last, flags disagreement between overlapping extractors |

No location/HQ extractor exists here (`structured_data_extract` was
removed 2026-09-08 - cleaned markdown can't preserve schema.org JSON-LD).
`company.location` is Apify-only; see `apify/company/universal/README.md`.
