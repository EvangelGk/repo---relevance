"""function_tech_stack_normalize(detected tool names [website scrape]) ->
{detected_stack, mentioned_technologies}

detected_stack is populated ONLY from context["detected_tools"] (a real
website-fingerprinting input, e.g. from a tag-manager/script scan) -
never from markdown - and is deduped, alias-collapsed, and categorized
(CRM/analytics/support/...). mentioned_technologies is a separate,
markdown-only scan for vendor/product names mentioned in prose.

Catalog broadened significantly 2026-09-08 (technographics called out as
a priority datapoint): from 18 vendors across 5 categories to ~75 across
13, since markdown-mention scanning is the ONLY signal this pipeline can
actually produce today - there's no live site-fingerprinting scan feeding
context["detected_tools"] yet, so mentioned_technologies' hit rate is
entirely a function of how many real vendor names the catalog knows.
Aliases that are also common English words (close, front, heap, notion,
dbt) are qualified with a distinguishing suffix (".com", ".io", "labs",
etc.) to avoid false-positiving on ordinary prose - see _CATALOG.

mentioned_technologies reflects what a company talks about (competencies,
integrations, partners) - it is NOT evidence of what they actually run.
Do not treat it as equivalent to detected_stack in any downstream scoring.
"""
import re

from ..base import DataPointExtractor

_CATALOG = {
    # CRM
    "salesforce": {"category": "CRM", "aliases": ["salesforce"]},
    "hubspot": {"category": "CRM", "aliases": ["hubspot"]},
    "pipedrive": {"category": "CRM", "aliases": ["pipedrive"]},
    "zoho_crm": {"category": "CRM", "aliases": ["zoho crm", "zoho.com"]},
    "dynamics_365": {"category": "CRM", "aliases": ["dynamics 365", "microsoft dynamics"]},
    "close_crm": {"category": "CRM", "aliases": ["close.com", "close crm"]},
    # ANALYTICS
    "google_analytics": {"category": "ANALYTICS", "aliases": ["google analytics", "gtag", "googletagmanager"]},
    "segment": {"category": "ANALYTICS", "aliases": ["segment"]},
    "mixpanel": {"category": "ANALYTICS", "aliases": ["mixpanel"]},
    "amplitude": {"category": "ANALYTICS", "aliases": ["amplitude"]},
    "heap": {"category": "ANALYTICS", "aliases": ["heap analytics", "heap.io"]},
    "hotjar": {"category": "ANALYTICS", "aliases": ["hotjar"]},
    "fullstory": {"category": "ANALYTICS", "aliases": ["fullstory"]},
    "posthog": {"category": "ANALYTICS", "aliases": ["posthog"]},
    # SUPPORT
    "intercom": {"category": "SUPPORT", "aliases": ["intercom"]},
    "zendesk": {"category": "SUPPORT", "aliases": ["zendesk"]},
    "drift": {"category": "SUPPORT", "aliases": ["drift.com", "drift chat"]},
    "freshdesk": {"category": "SUPPORT", "aliases": ["freshdesk"]},
    "helpscout": {"category": "SUPPORT", "aliases": ["help scout", "helpscout"]},
    "frontapp": {"category": "SUPPORT", "aliases": ["frontapp", "front app"]},
    # PAYMENTS
    "stripe": {"category": "PAYMENTS", "aliases": ["stripe"]},
    "paypal": {"category": "PAYMENTS", "aliases": ["paypal"]},
    "braintree": {"category": "PAYMENTS", "aliases": ["braintree"]},
    "adyen": {"category": "PAYMENTS", "aliases": ["adyen"]},
    "chargebee": {"category": "PAYMENTS", "aliases": ["chargebee"]},
    "recurly": {"category": "PAYMENTS", "aliases": ["recurly"]},
    # ECOMMERCE
    "shopify": {"category": "ECOMMERCE", "aliases": ["shopify"]},
    "bigcommerce": {"category": "ECOMMERCE", "aliases": ["bigcommerce"]},
    "woocommerce": {"category": "ECOMMERCE", "aliases": ["woocommerce"]},
    "magento": {"category": "ECOMMERCE", "aliases": ["magento"]},
    # MARKETING
    "marketo": {"category": "MARKETING", "aliases": ["marketo"]},
    "mailchimp": {"category": "MARKETING", "aliases": ["mailchimp"]},
    "klaviyo": {"category": "MARKETING", "aliases": ["klaviyo"]},
    "pardot": {"category": "MARKETING", "aliases": ["pardot"]},
    "activecampaign": {"category": "MARKETING", "aliases": ["activecampaign"]},
    "braze": {"category": "MARKETING", "aliases": ["braze"]},
    "iterable": {"category": "MARKETING", "aliases": ["iterable"]},
    "customerio": {"category": "MARKETING", "aliases": ["customer.io"]},
    # CMS
    "wordpress": {"category": "CMS", "aliases": ["wordpress", "wp-content"]},
    "webflow": {"category": "CMS", "aliases": ["webflow"]},
    "contentful": {"category": "CMS", "aliases": ["contentful"]},
    "sanity": {"category": "CMS", "aliases": ["sanity.io"]},
    "drupal": {"category": "CMS", "aliases": ["drupal"]},
    "squarespace": {"category": "CMS", "aliases": ["squarespace"]},
    "wix": {"category": "CMS", "aliases": ["wix.com"]},
    # INFRA / CLOUD
    "cloudflare": {"category": "INFRA", "aliases": ["cloudflare"]},
    "aws": {"category": "INFRA", "aliases": ["amazon web services", "aws"]},
    "azure": {"category": "INFRA", "aliases": ["microsoft azure", "azure cloud"]},
    "gcp": {"category": "INFRA", "aliases": ["google cloud platform", "google cloud"]},
    "vercel": {"category": "INFRA", "aliases": ["vercel"]},
    "netlify": {"category": "INFRA", "aliases": ["netlify"]},
    "heroku": {"category": "INFRA", "aliases": ["heroku"]},
    "digitalocean": {"category": "INFRA", "aliases": ["digitalocean", "digital ocean"]},
    # COMMUNICATION
    "slack": {"category": "COMMUNICATION", "aliases": ["slack"]},
    "zoom": {"category": "COMMUNICATION", "aliases": ["zoom.us", "zoom video", "zoom meeting"]},
    "microsoft_teams": {"category": "COMMUNICATION", "aliases": ["microsoft teams"]},
    "calendly": {"category": "COMMUNICATION", "aliases": ["calendly"]},
    # DEV_TOOLS
    "github": {"category": "DEV_TOOLS", "aliases": ["github"]},
    "gitlab": {"category": "DEV_TOOLS", "aliases": ["gitlab"]},
    "jira": {"category": "DEV_TOOLS", "aliases": ["jira"]},
    "confluence": {"category": "DEV_TOOLS", "aliases": ["confluence"]},
    "linear_app": {"category": "DEV_TOOLS", "aliases": ["linear.app", "linear issue tracker"]},
    "asana": {"category": "DEV_TOOLS", "aliases": ["asana.com", "asana app"]},
    "trello": {"category": "DEV_TOOLS", "aliases": ["trello"]},
    "notion": {"category": "DEV_TOOLS", "aliases": ["notion.so"]},
    # DATA_BI
    "snowflake": {"category": "DATA_BI", "aliases": ["snowflake"]},
    "looker": {"category": "DATA_BI", "aliases": ["looker"]},
    "tableau": {"category": "DATA_BI", "aliases": ["tableau"]},
    "power_bi": {"category": "DATA_BI", "aliases": ["power bi", "powerbi"]},
    "databricks": {"category": "DATA_BI", "aliases": ["databricks"]},
    "fivetran": {"category": "DATA_BI", "aliases": ["fivetran"]},
    "dbt": {"category": "DATA_BI", "aliases": ["dbt labs", "getdbt.com"]},
    # SECURITY_IAM
    "okta": {"category": "SECURITY_IAM", "aliases": ["okta"]},
    "auth0": {"category": "SECURITY_IAM", "aliases": ["auth0"]},
    "onelogin": {"category": "SECURITY_IAM", "aliases": ["onelogin"]},
    "duo_security": {"category": "SECURITY_IAM", "aliases": ["duo security"]},
    "1password": {"category": "SECURITY_IAM", "aliases": ["1password"]},
    # HR_PEOPLE
    "workday": {"category": "HR_PEOPLE", "aliases": ["workday"]},
    "bamboohr": {"category": "HR_PEOPLE", "aliases": ["bamboohr"]},
    "gusto": {"category": "HR_PEOPLE", "aliases": ["gusto.com", "gusto payroll"]},
    "rippling": {"category": "HR_PEOPLE", "aliases": ["rippling"]},
    "greenhouse": {"category": "HR_PEOPLE", "aliases": ["greenhouse.io", "greenhouse recruiting"]},
    "lever": {"category": "HR_PEOPLE", "aliases": ["lever.co", "lever recruiting"]},
}
_PATTERNS = {
    tool_id: re.compile(
        r"\b(?:" + "|".join(re.escape(a) for a in entry["aliases"]) + r")\b", re.IGNORECASE
    )
    for tool_id, entry in _CATALOG.items()
}


def _resolve(raw_name: str):
    for tool_id, pattern in _PATTERNS.items():
        if pattern.search(raw_name):
            return tool_id, _CATALOG[tool_id]["category"]
    return None


class TechStackNormalize(DataPointExtractor):
    name = "tech_stack_normalize"

    def extract(self, markdown: str, context: dict):
        mentioned = [
            {"tool_id": tool_id, "category": _CATALOG[tool_id]["category"]}
            for tool_id, pattern in _PATTERNS.items()
            if pattern.search(markdown)
        ]

        detected_stack = []
        seen_ids = set()
        for raw_name in context.get("detected_tools") or []:
            resolved = _resolve(str(raw_name))
            if resolved:
                tool_id, category = resolved
            else:
                tool_id = re.sub(r"[^a-z0-9]+", "_", str(raw_name).strip().lower()).strip("_")
                category = None
            if tool_id and tool_id not in seen_ids:
                seen_ids.add(tool_id)
                detected_stack.append({"tool_id": tool_id, "category": category})

        if detected_stack:
            self._last_source = "context"
        elif mentioned:
            self._last_source = "markdown"
        else:
            self._last_source = None
        return {"detected_stack": detected_stack, "mentioned_technologies": mentioned}
