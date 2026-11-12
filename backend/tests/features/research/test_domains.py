import pytest

from app.features.research.service.domains import host_matches, normalize_domain, rank_results
from app.providers.search.base import SearchResult

# Les deux premiers tableaux reprennent `normalizeDomain.test.ts` du front : même règle des deux
# côtés (le reste de `rejects` couvre les pièges propres à Python : `\d`, `$`).


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://www.Python.org/doc", "python.org"),
        ("docs.python.org", "docs.python.org"),
        ("  HTTP://User@Example.COM:8080/a?b=c#d  ", "example.com"),
        ("www.github.com.", "github.com"),
        ("xn--bcher-kva.example", "xn--bcher-kva.example"),
    ],
)
def test_normalize_domain_accepts(value: str, expected: str) -> None:
    assert normalize_domain(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "localhost",
        "192.168.0.1",
        "a b.com",
        "-x.com",
        "exemple.c",
        "http://",
        "a..com",
        "python.org\n/x\n",
        "pyth٣n.org",
        "example.com:١٢",
        "www.com",
        "a" * 64 + ".com",
        "[::1]",
        "exa_mple.com",
        "example.123",
    ],
)
def test_normalize_domain_rejects(value: str) -> None:
    with pytest.raises(ValueError, match="domaine"):
        normalize_domain(value)


def test_host_matches_domain_and_subdomains_only() -> None:
    assert host_matches("python.org", "python.org")
    assert host_matches("docs.python.org", "python.org")
    assert host_matches("Docs.Python.org.", "python.org")
    assert not host_matches("notpython.org", "python.org")
    assert not host_matches("python.org.evil.com", "python.org")
    assert not host_matches("python.org", "docs.python.org")
    assert not host_matches("python.org", "")


def _hit(url: str) -> SearchResult:
    return SearchResult(title=url, url=url, snippet="", engine="x", published=None)


def test_rank_results_excludes_and_puts_preferred_first() -> None:
    results = [
        _hit("https://blog.example.com/a"),
        _hit("https://docs.python.org/3/"),
        _hit("https://spam.net/x"),
        _hit("https://www.python.org/"),
        _hit("https://other.org/"),
    ]
    ranked = rank_results(results, preferred=["python.org"], excluded=["https://www.spam.net"])
    assert [(h.result.url, h.preferred) for h in ranked] == [
        ("https://docs.python.org/3/", True),
        ("https://www.python.org/", True),
        ("https://blog.example.com/a", False),
        ("https://other.org/", False),
    ]


def test_rank_results_exclusion_wins_and_invalid_entries_are_ignored() -> None:
    results = [_hit("https://a.python.org/"), _hit("not a url"), _hit("https://b.org/")]
    ranked = rank_results(results, preferred=["python.org", "???"], excluded=["a.python.org", ""])
    assert [h.result.url for h in ranked] == ["not a url", "https://b.org/"]
    assert rank_results([], preferred=[], excluded=[]) == []
