"""Served-page plausibility guards: block pages, content-free stubs, and
meta-refresh bounces must not be graded as websites."""

from conftest import CLEAN_PAGE, rule


def test_block_page_is_unassessable(check_html):
    html = ('<!DOCTYPE html><html><head><title>ERROR: The request could '
            'not be satisfied</title></head><body><h1>403 ERROR</h1>'
            '<p>Request blocked.</p></body></html>')
    result = check_html(html)
    assert not result.ok
    assert "block page" in result.error


def test_content_free_stub_is_unassessable(check_html):
    result = check_html("<html><body></body></html>")
    assert not result.ok
    assert "too small" in result.error


def test_real_minimal_page_is_still_graded(check_html):
    assert check_html(CLEAN_PAGE).ok


def test_non_html_response_is_unassessable(check_html):
    result = check_html('{"error": "over capacity", "status": 403}',
                        html_content_type="application/json")
    assert not result.ok
    assert "not HTML" in result.error


def test_meta_refresh_stub_follows_to_real_page(check_html):
    stub = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            '<title>Home</title>'
            '<meta http-equiv="refresh" content="0; url=/real.html">'
            '</head><body></body></html>')
    real = CLEAN_PAGE.replace("</body>", "<script>x()</script></body>")
    result = check_html(stub, extra_pages={"https://example.com/real.html": real})
    assert result.ok
    assert not rule(result, "JS-01").passed  # graded the target, not the stub


def test_meta_refresh_on_content_page_is_not_followed(check_html):
    html = CLEAN_PAGE.replace(
        "</head>",
        '<meta http-equiv="refresh" content="60"></head>').replace(
        "<p>A perfectly ordinary page.</p>",
        "<p>" + "Live scores update every minute on this page. " * 6 + "</p>")
    result = check_html(html)
    assert result.ok
    assert result.grade == "A"
