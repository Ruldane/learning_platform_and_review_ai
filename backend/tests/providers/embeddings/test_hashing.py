import math

from app.providers.embeddings.fake import HashingEmbedder


def _cos(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


async def test_hashing_embedder_is_deterministic_and_normalized() -> None:
    embedder = HashingEmbedder(64)
    first = await embedder.aembed_query("Attention multi têtes")
    second = await embedder.aembed_query("attention MULTI têtes")
    assert first == second and len(first) == 64
    assert math.isclose(math.sqrt(sum(x * x for x in first)), 1.0, rel_tol=1e-9)


async def test_hashing_embedder_shared_words_score_higher() -> None:
    embedder = HashingEmbedder(64)
    q = await embedder.aembed_query("attention multi têtes")
    near = await embedder.aembed_query("les têtes d'attention")
    far = await embedder.aembed_query("recette de crêpes")
    assert _cos(q, near) > _cos(q, far)


async def test_hashing_embedder_empty_text_is_zeros() -> None:
    assert await HashingEmbedder(8).aembed_query("  ...  ") == [0.0] * 8


async def test_hashing_embedder_documents_match_query_and_dimension() -> None:
    embedder = HashingEmbedder()
    docs = await embedder.aembed_documents(["un", "deux trois"])
    assert len(docs) == 2 and all(len(v) == 64 for v in docs)
    assert docs[1] == await embedder.aembed_query("deux trois")
