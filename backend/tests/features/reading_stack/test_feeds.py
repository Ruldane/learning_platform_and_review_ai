from app.features.reading_stack.service.feeds import FeedEntry, parse_feed


def test_rss_resolves_and_deduplicates_article_links() -> None:
    body = b"""<rss version="2.0"><channel>
      <item><title>Version 2</title><link>/release#news</link>
        <description>&lt;p&gt;Une version de test.&lt;/p&gt;</description></item>
      <item><title>Version 2 en double</title>
        <link>https://example.org/release</link></item>
      <item><title>Entree sans article</title></item>
    </channel></rss>"""

    assert parse_feed(body, "https://example.org/feed.xml") == [
        FeedEntry("https://example.org/release", "Version 2", "Une version de test."),
    ]


def test_atom_uses_the_article_link_and_ignores_other_relations() -> None:
    body = b"""<feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Un papier</title><link rel="self" href="/metadata"/>
        <link rel="alternate" href="/paper"/><summary>Le texte.</summary></entry>
    </feed>"""

    assert parse_feed(body, "https://example.org/atom.xml") == [
        FeedEntry("https://example.org/paper", "Un papier", "Le texte."),
    ]


def test_feed_reading_ignores_unusable_documents_and_links() -> None:
    body = b"""<rss><channel>
      <item><title>Lien invalide</title><link>mailto:example@example.org</link></item>
    </channel></rss>"""

    assert parse_feed(body, "https://example.org/feed.xml") == []
    assert parse_feed(b"<rss", "https://example.org/feed.xml") == []
    assert parse_feed(b" " * (1024 * 1024 + 1), "https://example.org/feed.xml") == []
