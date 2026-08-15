from pathlib import Path

from web10check.checker import check_targets
from web10check.fetcher import LocalFetcher

from conftest import CLEAN_PAGE, StubFetcher, rule

ABOUT = CLEAN_PAGE.replace("<h1>Hello</h1>", "<h1>About</h1>")


def make_site(tmp_path: Path):
    (tmp_path / "index.html").write_text(
        CLEAN_PAGE.replace(
            "</body>",
            '<a href="about.html">about</a>'
            '<a href="https://elsewhere.net/">external</a></body>',
        ),
        encoding="utf-8",
    )
    (tmp_path / "about.html").write_text(ABOUT, encoding="utf-8")
    return tmp_path


def test_local_spider_stays_on_site(tmp_path):
    make_site(tmp_path)
    fetcher = LocalFetcher(tmp_path)
    site = check_targets(fetcher, [fetcher.resolve_target(tmp_path)], spider=True)
    assert len(site.pages) == 2
    assert site.grade == "A"


def test_relative_target_resolves_against_cwd(tmp_path, monkeypatch):
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    make_site(site_dir)
    monkeypatch.chdir(tmp_path)
    fetcher = LocalFetcher("site")
    assert fetcher.resolve_target("site").endswith("site/index.html")


def test_local_absolute_url_is_third_party(tmp_path):
    (tmp_path / "index.html").write_text(
        CLEAN_PAGE.replace(
            "</body>", '<img src="https://cdn.net/x.png" alt="x"></body>'),
        encoding="utf-8",
    )
    fetcher = LocalFetcher(tmp_path)
    site = check_targets(fetcher, [fetcher.resolve_target(tmp_path)])
    assert not rule(site.pages[0], "TP-01").passed


def test_local_relative_resources_are_weighed(tmp_path):
    (tmp_path / "index.html").write_text(
        CLEAN_PAGE.replace(
            "</head>", '<link rel="stylesheet" href="style.css"></head>'),
        encoding="utf-8",
    )
    (tmp_path / "style.css").write_text("body { color: #222; }", encoding="utf-8")
    fetcher = LocalFetcher(tmp_path)
    site = check_targets(fetcher, [fetcher.resolve_target(tmp_path)])
    page = site.pages[0]
    assert page.grade == "A"
    assert page.weight_bytes > len(CLEAN_PAGE) - 60  # page + css counted


def test_http_spider_and_worst_page_grade():
    home = CLEAN_PAGE.replace("</body>", '<a href="/bad.html">bad</a></body>')
    bad = CLEAN_PAGE.replace("</body>", "<script>x()</script></body>")
    fetcher = StubFetcher({
        "https://example.com/": home,
        "https://example.com/bad.html": bad,
    })
    site = check_targets(fetcher, ["https://example.com/"], spider=True)
    assert len(site.pages) == 2
    assert site.pages[0].grade == "A"
    assert site.grade == "D"


def test_empty_response_is_not_a_page():
    fetcher = StubFetcher({"https://example.com/": ""})
    site = check_targets(fetcher, ["https://example.com/"])
    assert not site.pages[0].ok
    assert "empty response" in site.pages[0].error


def test_unreachable_page_reported():
    fetcher = StubFetcher({})
    site = check_targets(fetcher, ["https://example.com/"])
    assert not site.pages[0].ok
    assert site.grade is None
