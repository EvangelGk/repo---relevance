"""ClientContext: the structured ICP spec a client's brief compiles down to.

This is this repo's first piece of Artemis step 1 ("interpret brief") -
see ARTEMIS_CONTEXT.md. Nothing downstream (bronze/clay's company search
today; eventually silver-layer filtering) should read a client's raw brief
text directly - it reads this instead. New scope for this repo: the layout
CLAUDE.md documents today doesn't include client_context/ or bronze/clay/
yet, since bronze/ has been an empty placeholder until now.

Field names deliberately mirror Clay's own company-search field catalog
(GET /public/v0/search/query-mode/reference, fetched 2026-09-08) rather
than inventing a parallel vocabulary - bronze/clay/query_builder.py maps
each field here onto exactly the Clay DSL clause the reference doc
prescribes for it, so a client context file's shape stays legible against
Clay's own docs.

CLAY_INDUSTRIES and CLAY_COMPANY_SIZE_BUCKETS below are Clay's own enum
value sets for those two fields, extracted verbatim from that reference
doc (not hand-typed) so `industries`/`company_size_buckets` typos are
caught at load time instead of silently returning zero search results
later. hq_countries/hq_cities are deliberately NOT enum-validated here:
Clay's country_name enum alone runs to ~250 entries, and duplicating it in
this repo would just be a second copy to drift out of sync with Clay's -
a country-name typo there instead shows up downstream as a search with no
results, not a load-time error. Re-pull the reference doc and regenerate
these two tuples if Clay's enum values ever change.
"""
import json
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

CLAY_INDUSTRIES = (
    "Abrasives and Nonmetallic Minerals Manufacturing", "Accessible Architecture and Design",
    "Accommodation Services", "Accounting", "Administration of Justice",
    "Administrative and Support Services", "Advertising Services",
    "Agricultural Chemical Manufacturing",
    "Agriculture, Construction, Mining Machinery Manufacturing",
    "Air, Water, and Waste Program Management", "Airlines and Aviation",
    "Alternative Dispute Resolution", "Alternative Medicine", "Ambulance Services",
    "Amusement Parks and Arcades", "Animal Feed Manufacturing", "Animation",
    "Animation and Post-production", "Apparel Manufacturing", "Apparel and Fashion",
    "Appliances, Electrical, and Electronics Manufacturing",
    "Architectural and Structural Metal Manufacturing", "Architecture and Planning",
    "Armed Forces", "Artists and Writers", "Arts and Crafts",
    "Audio and Video Equipment Manufacturing", "Automation Machinery Manufacturing",
    "Automotive", "Aviation & Aerospace", "Aviation and Aerospace Component Manufacturing",
    "Baked Goods Manufacturing", "Banking", "Bars, Taverns, and Nightclubs",
    "Bed-and-Breakfasts, Hostels, Homestays", "Beverage Manufacturing",
    "Biomass Electric Power Generation", "Biotechnology", "Biotechnology Research",
    "Blockchain Services", "Blogs", "Boilers, Tanks, and Shipping Container Manufacturing",
    "Book Publishing", "Book and Periodical Publishing", "Breweries",
    "Broadcast Media Production and Distribution", "Building Construction",
    "Building Equipment Contractors", "Building Finishing Contractors", "Building Materials",
    "Building Structure and Exterior Contractors", "Business Consulting and Services",
    "Business Content", "Business Intelligence Platforms", "Business Supplies and Equipment",
    "Capital Markets", "Caterers", "Chemical Manufacturing",
    "Chemical Raw Materials Manufacturing", "Child Day Care Services", "Chiropractors",
    "Civic and Social Organizations", "Civil Engineering",
    "Claims Adjusting, Actuarial Services", "Clay and Refractory Products Manufacturing",
    "Climate Data and Analytics", "Climate Technology Product Manufacturing", "Coal Mining",
    "Collection Agencies", "Commercial Real Estate",
    "Commercial and Industrial Equipment Rental",
    "Commercial and Industrial Machinery Maintenance",
    "Commercial and Service Industry Machinery Manufacturing",
    "Communications Equipment Manufacturing", "Community Development and Urban Planning",
    "Community Services", "Computer Games", "Computer Hardware",
    "Computer Hardware Manufacturing", "Computer Networking", "Computer Networking Products",
    "Computer and Network Security", "Computers and Electronics Manufacturing",
    "Conservation Programs", "Construction", "Construction Hardware Manufacturing",
    "Consumer Electronics", "Consumer Goods", "Consumer Goods Rental", "Consumer Services",
    "Cosmetics", "Cosmetology and Barber Schools", "Courts of Law", "Credit Intermediation",
    "Dairy", "Dairy Product Manufacturing", "Dance Companies",
    "Data Infrastructure and Analytics", "Data Security Software Products", "Defense & Space",
    "Defense and Space Manufacturing", "Dentists", "Design", "Design Services",
    "Desktop Computing Software Products", "Digital Accessibility Services", "Distilleries",
    "E-Learning", "E-Learning Providers", "Economic Programs", "Education",
    "Education Administration Programs", "Education Management",
    "Electric Lighting Equipment Manufacturing", "Electric Power Generation",
    "Electric Power Transmission, Control, and Distribution",
    "Electrical Equipment Manufacturing", "Electronic and Precision Equipment Maintenance",
    "Embedded Software Products", "Emergency and Relief Services", "Engineering Services",
    "Engines and Power Transmission Equipment Manufacturing", "Entertainment",
    "Entertainment Providers", "Environmental Quality Programs", "Environmental Services",
    "Equipment Rental Services", "Events Services", "Executive Offices",
    "Executive Search Services", "Fabricated Metal Products", "Facilities Services",
    "Farming, Ranching, Forestry", "Farming", "Fashion Accessories Manufacturing",
    "Financial Services", "Fine Art", "Fine Arts Schools", "Fire Protection", "Fisheries",
    "Flight Training", "Food & Beverages", "Food and Beverage Manufacturing",
    "Food and Beverage Retail", "Food and Beverage Services", "Food Production",
    "Footwear Manufacturing", "Forestry and Logging", "Freight and Package Transportation",
    "Fruit and Vegetable Preserves Manufacturing", "Fundraising", "Funds and Trusts",
    "Furniture", "Furniture and Home Furnishings Manufacturing",
    "Gambling Facilities and Casinos", "Geothermal Electric Power Generation",
    "Glass Product Manufacturing", "Glass, Ceramics and Concrete Manufacturing",
    "Golf Courses and Country Clubs", "Government Administration", "Government Relations",
    "Government Relations Services", "Graphic Design", "Ground Passenger Transportation",
    "HVAC and Refrigeration Equipment Manufacturing", "Health and Human Services",
    "Health, Wellness and Fitness", "Higher Education",
    "Highway, Street, and Bridge Construction", "Historical Sites", "Holding Companies",
    "Home Health Care Services", "Horticulture", "Hospitality", "Hospitals",
    "Hospitals and Health Care", "Hotels and Motels", "Household Appliance Manufacturing",
    "Household Services", "Household and Institutional Furniture Manufacturing",
    "Housing Programs", "Housing and Community Development", "Human Resources",
    "Human Resources Services", "Hydroelectric Power Generation",
    "IT Services and IT Consulting", "IT System Custom Software Development",
    "IT System Data Services", "IT System Design Services",
    "IT System Installation and Disposal", "IT System Operations and Maintenance",
    "IT System Testing and Evaluation", "IT System Training and Support", "Import and Export",
    "Individual and Family Services", "Industrial Automation",
    "Industrial Machinery Manufacturing", "Industry Associations", "Information Services",
    "Information Technology and Services", "Insurance", "Insurance Agencies and Brokerages",
    "Insurance Carriers", "Insurance and Employee Benefit Funds", "Interior Design",
    "International Affairs", "International Trade and Development",
    "Internet Marketplace Platforms", "Internet News", "Internet Publishing",
    "Investment Advice", "Investment Banking", "Investment Management", "Janitorial Services",
    "Landscaping Services", "Language Schools", "Laundry and Drycleaning Services",
    "Law Enforcement", "Law Practice", "Leasing Non-residential Real Estate",
    "Leasing Residential Real Estate", "Leather Product Manufacturing", "Legal Services",
    "Legislative Offices", "Leisure, Travel & Tourism", "Libraries", "Loan Brokers",
    "Luxury Goods and Jewelry", "Machinery Manufacturing", "Manufacturing", "Maritime",
    "Maritime Transportation", "Market Research", "Marketing Services",
    "Mattress and Blinds Manufacturing", "Measuring and Control Instrument Manufacturing",
    "Meat Products Manufacturing", "Mechanical or Industrial Engineering",
    "Media & Telecommunications", "Media Production", "Medical Devices",
    "Medical Equipment Manufacturing", "Medical Practices",
    "Medical and Diagnostic Laboratories", "Mental Health Care", "Metal Ore Mining",
    "Metal Treatments", "Metal Valve, Ball, and Roller Manufacturing",
    "Metalworking Machinery Manufacturing", "Military and International Affairs", "Mining",
    "Mobile Computing Software Products", "Mobile Food Services", "Mobile Gaming Apps",
    "Motor Vehicle Manufacturing", "Motor Vehicle Parts Manufacturing",
    "Movies and Sound Recording", "Movies, Videos and Sound", "Museums",
    "Museums, Historical Sites, and Zoos", "Music", "Musicians", "Nanotechnology Research",
    "Natural Gas Distribution", "Newspaper Publishing", "Non-profit Organization Management",
    "Non-profit Organizations", "Nonmetallic Mineral Mining",
    "Nonresidential Building Construction", "Nuclear Electric Power Generation",
    "Nursing Homes and Residential Care Facilities", "Office Administration",
    "Office Furniture and Fixtures Manufacturing", "Oil and Gas", "Oil, Gas, and Mining",
    "Online Audio and Video Media", "Online Media", "Online and Mail Order Retail",
    "Operations Consulting", "Optometrists", "Outpatient Care Centers",
    "Outsourcing and Offshoring Consulting", "Outsourcing/Offshoring",
    "Packaging and Containers", "Packaging and Containers Manufacturing",
    "Paint, Coating, and Adhesive Manufacturing", "Paper and Forest Product Manufacturing",
    "Paper and Forest Products", "Performing Arts", "Performing Arts and Spectator Sports",
    "Periodical Publishing", "Personal Care Product Manufacturing", "Personal Care Services",
    "Personal and Laundry Services", "Pet Services", "Pharmaceutical Manufacturing",
    "Philanthropic Fundraising Services", "Philanthropy", "Photography",
    "Physical, Occupational and Speech Therapists", "Physicians", "Plastics Manufacturing",
    "Plastics and Rubber Product Manufacturing", "Political Organizations",
    "Primary Metal Manufacturing", "Primary and Secondary Education", "Printing Services",
    "Professional Organizations", "Professional Services",
    "Professional Training and Coaching", "Program Development", "Public Assistance Programs",
    "Public Health", "Public Policy", "Public Policy Offices",
    "Public Relations and Communications Services", "Public Safety",
    "Radio and Television Broadcasting", "Rail Transportation",
    "Railroad Equipment Manufacturing", "Ranching", "Real Estate",
    "Real Estate Agents and Brokers", "Real Estate and Equipment Rental Services",
    "Recreational Facilities", "Religious Institutions",
    "Renewable Energy Equipment Manufacturing", "Renewable Energy Power Generation",
    "Renewable Energy Semiconductor Manufacturing", "Renewables & Environment",
    "Repair and Maintenance", "Research", "Research Services",
    "Residential Building Construction", "Restaurants", "Retail", "Retail Apparel and Fashion",
    "Retail Appliances, Electrical, and Electronic Equipment", "Retail Art Dealers",
    "Retail Art Supplies", "Retail Books and Printed News",
    "Retail Building Materials and Garden Equipment", "Retail Florists",
    "Retail Furniture and Home Furnishings", "Retail Gasoline", "Retail Groceries",
    "Retail Health and Personal Care Products", "Retail Luxury Goods and Jewelry",
    "Retail Motor Vehicles", "Retail Musical Instruments", "Retail Office Equipment",
    "Retail Office Supplies and Gifts", "Retail Pharmacies",
    "Retail Recyclable Materials & Used Merchandise", "Reupholstery and Furniture Repair",
    "Robotics Engineering", "Rubber Products Manufacturing", "Satellite Telecommunications",
    "School and Employee Bus Services", "Seafood Product Manufacturing",
    "Securities and Commodity Exchanges", "Security Guards and Patrol Services",
    "Security Systems Services", "Security and Investigations", "Semiconductor Manufacturing",
    "Semiconductors", "Services for Renewable Energy", "Services for the Elderly and Disabled",
    "Sheet Music Publishing", "Shipbuilding",
    "Shuttles and Special Needs Transportation Services", "Sightseeing Transportation",
    "Soap and Cleaning Product Manufacturing", "Social Networking Platforms",
    "Software Development", "Solar Electric Power Generation", "Sound Recording",
    "Space Research and Technology", "Specialty Trade Contractors", "Spectator Sports",
    "Sporting Goods", "Sporting Goods Manufacturing", "Sports Teams and Clubs",
    "Sports and Recreation Instruction", "Spring and Wire Product Manufacturing",
    "Staffing and Recruiting", "Steam and Air-Conditioning Supply",
    "Strategic Management Services", "Subdivision of Land",
    "Sugar and Confectionery Product Manufacturing", "Surveying and Mapping Services",
    "Taxi and Limousine Services", "Technical and Vocational Training",
    "Technology, Information and Internet", "Technology, Information and Media",
    "Telecommunications", "Telecommunications Carriers", "Telephone Call Centers",
    "Temporary Help Services", "Textile Manufacturing", "Theater Companies", "Think Tanks",
    "Tobacco", "Tobacco Manufacturing", "Translation and Localization",
    "Transportation Equipment Manufacturing", "Transportation Programs",
    "Transportation, Logistics, Supply Chain and Storage", "Transportation/Trucking/Railroad",
    "Travel Arrangements", "Truck Transportation", "Trusts and Estates",
    "Turned Products and Fastener Manufacturing", "Urban Transit Services", "Utilities",
    "Utilities Administration", "Utility System Construction",
    "Vehicle Repair and Maintenance", "Venture Capital and Private Equity Principals",
    "Veterinary", "Veterinary Services", "Vocational Rehabilitation Services", "Warehousing",
    "Warehousing and Storage", "Waste Collection", "Waste Treatment and Disposal",
    "Water Supply and Irrigation Systems",
    "Water, Waste, Steam, and Air Conditioning Services", "Wellness and Fitness Services",
    "Wholesale", "Wholesale Alcoholic Beverages", "Wholesale Apparel and Sewing Supplies",
    "Wholesale Appliances, Electrical, and Electronics", "Wholesale Building Materials",
    "Wholesale Chemical and Allied Products", "Wholesale Computer Equipment",
    "Wholesale Drugs and Sundries", "Wholesale Food and Beverage", "Wholesale Footwear",
    "Wholesale Furniture and Home Furnishings",
    "Wholesale Hardware, Plumbing, Heating Equipment", "Wholesale Import and Export",
    "Wholesale Luxury Goods and Jewelry", "Wholesale Machinery",
    "Wholesale Metals and Minerals", "Wholesale Motor Vehicles and Parts",
    "Wholesale Paper Products", "Wholesale Petroleum and Petroleum Products",
    "Wholesale Raw Farm Products", "Wholesale Recyclable Materials",
    "Wind Electric Power Generation", "Wine and Spirits", "Wineries", "Wireless Services",
    "Wood Product Manufacturing", "Writing and Editing", "Zoos and Botanical Gardens",
)

CLAY_COMPANY_SIZE_BUCKETS = (
    "1", "2-10", "11-50", "51-200", "201-500", "501-1,000", "1,001-5,000", "5,001-10,000",
    "10,001+",
)

_CLIENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clients")

_REQUIRED_FIELDS = ("client_id", "name")

# Every ClientContext field that's a list of strings in the JSON file and a
# tuple of strings on the dataclass - kept as one list so load/validate
# don't have to repeat the field set.
_TUPLE_FIELDS = (
    "industries",
    "company_size_buckets",
    "hq_countries",
    "hq_cities",
    "technologies",
    "description_keywords",
    "products_and_services",
    "exclude_domains",
)


class ClientContextError(ValueError):
    """Raised when a client context file fails to load or validate."""


@dataclass(frozen=True)
class ClientContext:
    """One client's interpreted ICP - the output of Artemis step 1 in this
    repo. `client_id` is this object's join key (filenames under
    clients/, dead-letter/audit correlation, eventually a run_id
    composite) the same way domain_normalize is the join key for a row."""

    client_id: str
    name: str
    industries: Tuple[str, ...] = ()
    company_size_buckets: Tuple[str, ...] = ()
    hq_countries: Tuple[str, ...] = ()
    hq_cities: Tuple[str, ...] = ()
    technologies: Tuple[str, ...] = ()
    description_keywords: Tuple[str, ...] = ()
    products_and_services: Tuple[str, ...] = ()
    exclude_domains: Tuple[str, ...] = ()
    limit: int = 100
    notes: Optional[str] = None
    created_at: Optional[str] = None


def _validate(data: dict) -> List[str]:
    violations: List[str] = []

    for name in _REQUIRED_FIELDS:
        if not data.get(name):
            violations.append(f"{name}: required but missing")

    for name in _TUPLE_FIELDS:
        value = data.get(name, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            violations.append(f"{name}: expected a list of strings")

    unknown_industries = set(data.get("industries") or []) - set(CLAY_INDUSTRIES)
    if unknown_industries:
        violations.append(
            f"industries: not in Clay's industry enum: {sorted(unknown_industries)}"
        )

    unknown_sizes = set(data.get("company_size_buckets") or []) - set(CLAY_COMPANY_SIZE_BUCKETS)
    if unknown_sizes:
        violations.append(
            f"company_size_buckets: not in Clay's size-bucket enum: {sorted(unknown_sizes)}"
        )

    limit = data.get("limit", 100)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        violations.append("limit: must be a positive integer")

    return violations


def load_client_context(path: str) -> ClientContext:
    """Read one client context JSON file and return a validated
    ClientContext. Raises ClientContextError (with every violation found,
    not just the first) rather than letting a malformed file reach
    bronze/clay's query builder and produce a confusing Clay 400."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    violations = _validate(data)
    if violations:
        raise ClientContextError(f"{path}: " + "; ".join(violations))

    return ClientContext(
        client_id=data["client_id"],
        name=data["name"],
        industries=tuple(data.get("industries") or ()),
        company_size_buckets=tuple(data.get("company_size_buckets") or ()),
        hq_countries=tuple(data.get("hq_countries") or ()),
        hq_cities=tuple(data.get("hq_cities") or ()),
        technologies=tuple(data.get("technologies") or ()),
        description_keywords=tuple(data.get("description_keywords") or ()),
        products_and_services=tuple(data.get("products_and_services") or ()),
        exclude_domains=tuple(data.get("exclude_domains") or ()),
        limit=data.get("limit", 100),
        notes=data.get("notes"),
        created_at=data.get("created_at"),
    )


def list_client_contexts(directory: str = _CLIENTS_DIR) -> List[ClientContext]:
    """Load every *.json file directly under `directory`, sorted by
    filename for a deterministic order. Raises on the first invalid file
    rather than skipping it - a bad client context should block the run it
    would have driven, not silently drop out of a batch."""
    if not os.path.isdir(directory):
        return []
    paths = sorted(
        os.path.join(directory, fname)
        for fname in os.listdir(directory)
        if fname.endswith(".json")
    )
    return [load_client_context(p) for p in paths]
