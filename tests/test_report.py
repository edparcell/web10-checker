import json

from web10check.checker import check_targets
from web10check.report import to_html, to_json, to_text

from conftest import CLEAN_PAGE, StubFetcher


def _site(html=CLEAN_PAGE):
    return check_targets(StubFetcher({"https://example.com/": html}),
                         ["https://example.com/"])


def test_text_report_shows_grade_and_rules():
    text = to_text(_site())
    assert "Overall grade: A (PASS)" in text
    assert "JS-01" in text and "[ pass]" in text


def test_json_report_round_trips():
    data = json.loads(to_json(_site()))
    assert data["grade"] == "A"
    assert data["pages"][0]["rules"][0]["rule_id"] == "JS-01"
    assert data["spec_edition"] == "2026"


def test_html_report_practices_what_it_preaches():
    html = to_html(_site(CLEAN_PAGE.replace("</body>", "<script></script></body>")))
    assert "<script" not in html.lower().replace("&lt;script", "")
    assert "http://" not in html and "https://example" in html  # only the checked URL
    assert "Grade <strong class='fail'>D</strong>" in html
