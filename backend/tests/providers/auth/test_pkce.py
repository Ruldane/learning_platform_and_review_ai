import re

from app.providers.auth.pkce import challenge, new_verifier


def test_challenge_matches_rfc7636_example() -> None:
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert challenge(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_verifier_length_and_alphabet_follow_rfc7636() -> None:
    verifier = new_verifier()
    assert 43 <= len(verifier) <= 128
    assert re.fullmatch(r"[A-Za-z0-9_-]+", verifier)


def test_verifiers_are_never_repeated() -> None:
    assert len({new_verifier() for _ in range(50)}) == 50


def test_challenge_has_no_padding() -> None:
    assert "=" not in challenge(new_verifier())
