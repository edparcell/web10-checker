from web10check.origins import registrable_domain, same_site


def test_www_is_same_site():
    assert same_site("www.example.com", "example.com")


def test_subdomain_is_same_site():
    assert same_site("images.apple.com", "apple.com")


def test_different_domains():
    assert not same_site("example.com", "cdn.example.net")


def test_uk_second_level():
    assert registrable_domain("news.bbc.co.uk") == "bbc.co.uk"
    assert same_site("news.bbc.co.uk", "www.bbc.co.uk")
    assert not same_site("example.co.uk", "other.co.uk")
