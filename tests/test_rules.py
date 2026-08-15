from conftest import CLEAN_PAGE, rule


def test_clean_page_gets_a(check_html):
    result = check_html(CLEAN_PAGE)
    assert result.grade == "A"
    assert result.majors == 0 and result.minors == 0
    assert all(r.passed for r in result.rule_results)


def test_script_tag_is_major(check_html):
    result = check_html(CLEAN_PAGE.replace("</body>", "<script>alert(1)</script></body>"))
    assert not rule(result, "JS-01").passed
    assert result.grade == "D"


def test_event_handler_and_js_url_are_js(check_html):
    html = CLEAN_PAGE.replace(
        "<p>A perfectly ordinary page.</p>",
        '<p onclick="x()">hi</p><a href="javascript:void(0)">click</a>',
    )
    result = check_html(html)
    js = rule(result, "JS-01")
    assert len(js.occurrences) == 2
    assert js.counted == 1  # majors count once per rule


def test_script_preload_is_js(check_html):
    html = CLEAN_PAGE.replace(
        "</head>", '<link rel="modulepreload" href="/app.js"></head>')
    assert not rule(check_html(html), "JS-01").passed


def test_third_party_image_is_major(check_html):
    html = CLEAN_PAGE.replace(
        "</body>", '<img src="https://cdn.tracker.net/pixel.gif" alt=""></body>')
    result = check_html(html)
    assert not rule(result, "TP-01").passed
    assert result.grade == "D"


def test_same_site_subdomain_is_not_third_party(check_html):
    html = CLEAN_PAGE.replace(
        "</body>", '<img src="https://images.example.com/a.png" alt=""></body>')
    assert rule(check_html(html), "TP-01").passed


def test_two_majors_is_f(check_html):
    html = CLEAN_PAGE.replace(
        "</body>",
        '<script src="x.js"></script><img src="https://ads.example.net/a.gif" alt=""></body>',
    )
    assert check_html(html).grade == "F"


def test_missing_alt_capped_at_three(check_html):
    imgs = "".join(f'<img src="i{n}.png">' for n in range(5))
    result = check_html(CLEAN_PAGE.replace("</body>", imgs + "</body>"))
    hy5 = rule(result, "HY-05")
    assert len(hy5.occurrences) == 5
    assert hy5.counted == 3
    assert result.grade == "B"


def test_empty_alt_is_fine(check_html):
    html = CLEAN_PAGE.replace("</body>", '<img src="a.png" alt=""></body>')
    assert rule(check_html(html), "HY-05").passed


def test_hygiene_minors(check_html):
    result = check_html("<html><body><p>bare</p></body></html>",
                        html_content_type="text/html")
    for rule_id in ("HY-01", "HY-02", "HY-03", "HY-04"):
        assert not rule(result, rule_id).passed
    assert result.minors == 4
    assert result.grade == "B"


def test_charset_from_header_counts(check_html):
    html = CLEAN_PAGE.replace('<meta charset="utf-8">', "")
    # StubFetcher serves text/html; charset=utf-8, which is a declaration
    assert rule(check_html(html), "HY-04").passed


def test_autoplay_is_major(check_html):
    html = CLEAN_PAGE.replace("</body>", '<video autoplay src="v.mp4"></video></body>')
    assert not rule(check_html(html), "AV-01").passed


def test_first_party_iframe_is_minor(check_html):
    html = CLEAN_PAGE.replace("</body>", '<iframe src="/inner.html"></iframe></body>')
    result = check_html(html)
    assert not rule(result, "FR-01").passed
    assert result.grade == "B"


def test_third_party_iframe_is_major(check_html):
    html = CLEAN_PAGE.replace("</body>", '<iframe src="https://ads.net/f"></iframe></body>')
    result = check_html(html)
    assert not rule(result, "TP-01").passed
    assert rule(result, "FR-01").passed


def test_font_face_in_style_tag(check_html):
    html = CLEAN_PAGE.replace(
        "</head>", "<style>@font-face { font-family: X; src: url(x.woff2); }</style></head>")
    assert not rule(check_html(html), "FT-01").passed


def test_linked_css_is_fetched_and_scanned(check_html):
    html = CLEAN_PAGE.replace(
        "</head>", '<link rel="stylesheet" href="/style.css"></head>')
    css = "@font-face { src: url(f.woff); } body { background: url(https://cdn.other.net/bg.png); }"
    result = check_html(html, extra_pages={"https://example.com/style.css": css})
    assert not rule(result, "FT-01").passed
    assert not rule(result, "TP-01").passed


def test_cookies_are_major(check_html):
    result = check_html(CLEAN_PAGE, page_cookies={"https://example.com/"})
    assert not rule(result, "CK-01").passed
    assert result.grade == "D"


def test_weight_minor_and_major(check_html):
    html = CLEAN_PAGE.replace("</body>", '<img src="big.jpg" alt="big"></body>')
    heavy = check_html(html, sizes={"https://example.com/big.jpg": 600 * 1024})
    assert not rule(heavy, "WT-02").passed
    assert rule(heavy, "WT-01").passed
    obese = check_html(html, sizes={"https://example.com/big.jpg": 3 * 1024 * 1024})
    assert not rule(obese, "WT-01").passed
    assert rule(obese, "WT-02").passed  # WT-02 yields to WT-01


def test_over_twenty_requests_is_minor(check_html):
    imgs = "".join(f'<img src="i{n}.png" alt="x">' for n in range(21))
    result = check_html(CLEAN_PAGE.replace("</body>", imgs + "</body>"))
    assert not rule(result, "RQ-01").passed


def test_noscript_content_is_ignored(check_html):
    html = CLEAN_PAGE.replace(
        "</body>",
        '<noscript><img src="https://tracker.net/px.gif"></noscript></body>')
    result = check_html(html)
    assert rule(result, "TP-01").passed
    assert rule(result, "HY-05").passed
    assert result.grade == "A"
