from silver.apify.people.secondary.datapoints.topic_classify import function_topic_classify

# Realistic LinkedIn "About" markdown-style text - the kind of free text
# this function is meant to run against.
_SAMPLE_BIO_MARKDOWN = """
## About

I'm a growth marketing lead passionate about **machine learning** and
building go-to-market motions for early-stage SaaS startups. Previously
led demand generation at a fintech startup focused on payments.
"""


def test_classifies_markdown_bio():
    topics = function_topic_classify(_SAMPLE_BIO_MARKDOWN)
    assert set(topics) >= {"AI_ML", "SAAS", "MARKETING", "FINTECH"}


def test_no_match_returns_empty_list():
    assert function_topic_classify("I like long walks on the beach.") == []


def test_none_returns_empty_list():
    assert function_topic_classify(None) == []


def test_accepts_list_of_snippets():
    topics = function_topic_classify(["Excited about venture capital", "and cybersecurity."])
    assert set(topics) == {"VENTURE_CAPITAL", "CYBERSECURITY"}
