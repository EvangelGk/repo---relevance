"""Import order = execution order: later extractors can read earlier
ones' output out of `context` (e.g. company_entity_resolve reads
domain_normalize + legal_entity_extract; conflict_check reads everything,
so it stays last). To add a new datapoint: create the file here, subclass
DataPointExtractor, and add one import line below - firecrawl.py never
needs to change, since it builds its extractor list from base.REGISTRY.
"""
from . import domain_normalize  # noqa: F401
from . import structured_data_extract  # noqa: F401
from . import social_links_extract  # noqa: F401
from . import legal_entity_extract  # noqa: F401
from . import company_description_extract  # noqa: F401
from . import site_locale_detect  # noqa: F401
from . import pricing_locale_extract  # noqa: F401
from . import careers_page_parse  # noqa: F401
from . import tech_stack_normalize  # noqa: F401
from . import business_model  # noqa: F401
from . import company_entity_resolve  # noqa: F401
from . import regulatory_event_classify  # noqa: F401
from . import date_normalize  # noqa: F401
from . import timeseries_snapshot  # noqa: F401
from . import freshness  # noqa: F401
from . import compliance_framework_extract  # noqa: F401
from . import experience_signal_extract  # noqa: F401
from . import service_region_extract  # noqa: F401
from . import conflict_check  # noqa: F401
